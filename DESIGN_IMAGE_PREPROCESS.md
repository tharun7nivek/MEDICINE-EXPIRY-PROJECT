# Design spec: image transforms before AI date detection

This document is a porting guide for a **new implementation** of this medicine-expiry project. It covers **what** image operations run before the vision model, **why** they exist, **exact parameters**, and **code to copy**.

There are **two pipelines** in this repo. They do **not** share the same preprocess stack.

| Pipeline | File | Purpose | Transforms before VL/LLM |
|---|---|---|---|
| **Web (current Django app)** | `expiry_app/views.py` | Upload → YOLO crop → OpenRouter VL | Resize for YOLO, mask crop, **no dewarp** |
| **Offline batch / failsafe** | `dates.py` | Folder of images → Groq Llama Maverick | Dewarp + sharpen, morphological OCR-style preprocess, waterfall retries |

If you are rebuilding the **product web path**, start with `views.py`. If you need the **accuracy failsafe** (dewarping, morph), you must **bring `dates.py` into the web path**; it is not wired into Django today.

---

## 1. Problem the transforms are solving

Medicine labels are photographed at an angle, on curved bottles, with small print, glare, and clutter (brand art, barcodes, batch codes). A vision-language model (VLM) is asked to read **MFG/EXP dates**.

Transforms exist to:

1. **Localize** the date region so the model is not looking at the whole bottle (YOLO instance segmentation + crop).
2. **Reduce perspective distortion** on that crop so printed digits look closer to frontal (heuristic “dewarp”).
3. **Increase local contrast of glyphs** when the raw crop still fails (sharpen; then morphological binarization).
4. **Retry without the transform** if the transform made things worse (waterfall).

They are **not** camera-calibration undistort (`cv2.undistort` / chessboard). There is **no** document-corner detector, **no** homography from real 3D, **no** cylindrical unwrap.

---

## 2. End-to-end architecture

```
                    ┌─────────────────────────┐
  user image        │  save as PNG            │
  ─────────────────►│  static/raw_images/     │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Resize 640×640         │  YOLO input only
                    │  Ultralytics YOLO .pt   │  masks on date regions
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  Scale mask to original │
                    │  Contours → polygon AND │
                    │  Bounding-box crop      │
                    └───────────┬─────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │ WEB (views.py)       │  BATCH (dates.py)    │
         │ send crop as-is      │  Layer 1: dewarp+    │
         │ to OpenRouter VL     │  sharpen, then VLM   │
         │ fallback: full image │  Layer 2: raw crop   │
         │                      │  Layer 3: morph full │
         │                      │  Layer 4: raw full   │
         └──────────────────────┴──────────────────────┘
```

**Dependencies (from imports):**

- `opencv-python` (`cv2`)
- `numpy`
- `Pillow` (`PIL`) — used in `dates.py` morph save and RGB validate
- `ultralytics` YOLO — web path only
- `requests` — OpenRouter
- `groq` — batch path only
- Django 5.x — web path

YOLO weights: `model/best.pt` (instance segmentation, not box-only).

---

## 3. Web pipeline transforms (`expiry_app/views.py`)

### 3.1 Why each step

| Step | Why |
|---|---|
| Save upload as PNG | Stable path for OpenCV + VLM; unique `uuid` filename |
| `cv2.imread` | BGR ndarray for YOLO + crop |
| `cv2.resize(..., (640, 640))` | Typical YOLO train size; **distorts aspect ratio** (stretch, not letterbox) |
| Predict on **resized** image, crop from **original** | Masks come from 640×640; they are resized back to `(W, H)` so crops keep original resolution (better for small text) |
| Instance **masks** not boxes | Date print is a thin region; mask + `bitwise_and` zeros background so the VLM sees less clutter |
| Area filter `< 50` px² | Drop noise contours |
| Min box `w < 5 or h < 5` | Drop degenerate crops |
| Sort crops by area, take top **2** (`MAX_CROPS_TO_ANALYZE`) | Limit API cost; largest mask is assumed most likely the date panel |
| If no masks / no dates | Fall back to **full original** image to the same VLM |

### 3.2 Constants

```python
MODEL_PATH = os.path.join(settings.BASE_DIR, 'model', 'best.pt')
MAX_CROPS_TO_ANALYZE = 2
YOLO_INPUT_SIZE = (640, 640)
MIN_CONTOUR_AREA = 50
MIN_CROP_SIDE = 5
```

YOLO is loaded **lazily** and guarded with `threading.Lock` so Django `runserver` checks do not load the model, and concurrent requests do not race.

### 3.3 Code to port: YOLO crop (canonical)

This is the **entire** localization stack used before the VLM in production.

```python
import cv2
import numpy as np
import os
import threading
from ultralytics import YOLO

MODEL_PATH = ".../model/best.pt"
MAX_CROPS_TO_ANALYZE = 2
_model = None
_yolo_lock = threading.Lock()


def get_yolo_model():
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model


def extract_date_crops(img_bgr, yolo_output_dir, file_id):
    """
    img_bgr: original image from cv2.imread
    Returns list of (web_or_rel_path, filesystem_path) for the largest crops.
    """
    H, W, _ = img_bgr.shape
    img_resized = cv2.resize(img_bgr, (640, 640))

    with _yolo_lock:
        results = get_yolo_model().predict(img_resized, verbose=False)

    crop_candidates = []

    for result in results:
        if result.masks is None or result.masks.data is None:
            continue
        for idx, mask in enumerate(result.masks.data):
            mask = mask.cpu().numpy().astype(np.uint8) * 255
            mask = cv2.resize(mask, (W, H))
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 50:
                    continue
                polygon_mask = np.zeros_like(img_bgr, dtype=np.uint8)
                cv2.drawContours(
                    polygon_mask, [contour], -1, (255, 255, 255),
                    thickness=cv2.FILLED,
                )
                roi = cv2.bitwise_and(img_bgr, polygon_mask)
                x, y, w, h = cv2.boundingRect(contour)
                if w < 5 or h < 5:
                    continue
                cropped_roi = roi[y : y + h, x : x + w]
                crop_candidates.append((area, idx, cropped_roi))

    crop_candidates.sort(key=lambda item: item[0], reverse=True)
    output_paths = []
    os.makedirs(yolo_output_dir, exist_ok=True)
    for area, idx, cropped_roi in crop_candidates[:MAX_CROPS_TO_ANALYZE]:
        output_filename = f"output_{file_id}_{idx}.png"
        output_path = os.path.join(yolo_output_dir, output_filename)
        cv2.imwrite(output_path, cropped_roi)
        output_paths.append(output_path)
    return output_paths
```

**Geometry notes for a new implementation:**

- Mask is `uint8` 0/255 after `* 255`.
- `cv2.resize` on the mask uses **default bilinear** interpolation, then contours. That slightly **blurs mask edges**; if you reimplement, consider `interpolation=cv2.INTER_NEAREST` for a crisper polygon.
- Crop is **axis-aligned bounding box** of the contour, not a rotated min-area rect. Background outside the polygon is black (`bitwise_and`).
- **Aspect-ratio stretch** at 640×640 can shift mask alignment vs a letterboxed model. If you retrain YOLO with letterbox, match inference to training.

### 3.4 What is *not* done on the web path

- No `getPerspectiveTransform` / `warpPerspective`
- No sharpen kernel
- No grayscale / adaptive threshold / morphology
- No PIL RGB conversion (OpenRouter encoder uses the file bytes as-is)

The VLM (`nvidia/nemotron-nano-12b-v2-vl:free` via OpenRouter) receives **PNG/JPEG base64** of the crop (or full image).

---

## 4. Batch pipeline: dewarp + morph (`dates.py`)

This is the pipeline you asked about. It assumes you already have a **cropped** image path and a **full** image path (comments say “YOLO cropped”). The `__main__` folder runner currently passes the **same** path for both (`detect_dates_from_image` → `enhanced_four_layer_failsafe_analysis(image_path, image_path, ...)`), so in batch mode layers 1–2 and 3–4 are the same file unless you wire YOLO yourself.

### 4.1 Layer waterfall (why)

VLM OCR is brittle. A transform that helps a curved bottle can **hurt** a flat, already-frontal label. The design is **stop at first “fruitful” result**:

| Layer | Input | Transform | Intent |
|---|---|---|---|
| 1 | Crop | Dewarp + unsharp-style kernel | Frontalize + crisp edges |
| 2 | Crop | None | If dewarp sheared the text, try original |
| 3 | Full image | Adaptive threshold + morph close + invert | High-contrast “document” look when crop fails |
| 4 | Full image | None | Last resort, full context |

**Fruitful** means: JSON has any `expiry_dates` or `manufacturing_dates`, **or** `analysis_notes` contain a 4-digit year or month abbreviation. Consistency check `validate_date_consistency` currently **does not change control flow** (both branches `return processed_result`).

### 4.2 Dewarp — what it actually does

**Name vs reality:** `dewarp_image` does **not** detect bottle curvature or document corners.

It applies a **fixed trapezoid warp**:

- **Source** quadrilateral = the four image corners.
- **Destination** = top edge unchanged; **bottom-left and bottom-right move inward** by `offset`.
- `offset = min(50, width // 8)` pixels.

Effect: the bottom of the image is **pinched**, which **stretches** the lower region horizontally relative to the top. That is a cheap approximation of “looking up at a bottle” or “label receding at the bottom.” It is **the same warp for every image**, independent of content.

Then a **3×3 sharpen** kernel:

```
-1 -1 -1
-1  9 -1
-1 -1 -1
```

This is a classic high-boost / unsharp-style Laplacian (center 9 = 8+1). It boosts edges (digits) and also **boosts noise and JPEG ringing**.

On failure, return the original ndarray.

**Why this was used (inferred from code + domain):**

- Curved/angled packs make EXP text look like a trapezoid; a mild inverse trapezoid can make glyphs more axis-aligned for the VLM.
- Sharpen compensates for blur after `warpPerspective` interpolation.
- Caps `offset` at 50 so large images are not wildly sheared; `width // 8` scales down for tiny YOLO crops (e.g. width 80 → offset 10).

**Limitations to fix in a new version:**

- Warp assumes “distortion is always bottom-inward.” Wrong for many photos (tilt left/right, top of bottle closer, cylindrical barrel).
- No `cv2.INTER_CUBIC` specified — default is linear.
- Border fill default (black) can introduce black triangles the VLM may treat as content.
- Sharpen after warp is baked in; you cannot A/B them separately in this function.

### 4.3 Code to port: dewarp

```python
import cv2
import numpy as np


def dewarp_image(image):
    """Heuristic trapezoid warp + sharpen. image: BGR or gray ndarray."""
    if len(image.shape) == 3:
        height, width = image.shape[:2]
    else:
        height, width = image.shape

    src_points = np.float32([
        [0, 0],
        [width - 1, 0],
        [0, height - 1],
        [width - 1, height - 1],
    ])
    offset = min(50, width // 8)
    dst_points = np.float32([
        [0, 0],
        [width - 1, 0],
        [offset, height - 1],
        [width - offset, height - 1],
    ])
    try:
        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        dewarped = cv2.warpPerspective(image, matrix, (width, height))
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        dewarped_sharpened = cv2.filter2D(dewarped, -1, kernel)
        return dewarped_sharpened
    except Exception as e:
        print(f"Dewarping failed: {str(e)}, returning original image")
        return image
```

**Math:** `getPerspectiveTransform` solves a 3×3 homography \(H\) mapping `src` → `dst`. `warpPerspective` samples the input so output pixel \(p\) comes from \(H^{-1}p\). Output size stays `(width, height)`.

**Suggested split for a new codebase:**

```python
def trapezoid_dewarp(image, offset=None, interpolation=cv2.INTER_CUBIC):
    h, w = image.shape[:2]
    if offset is None:
        offset = min(50, w // 8)
    src = np.float32([[0, 0], [w - 1, 0], [0, h - 1], [w - 1, h - 1]])
    dst = np.float32([[0, 0], [w - 1, 0], [offset, h - 1], [w - offset, h - 1]])
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(
        image, M, (w, h),
        flags=interpolation,
        borderMode=cv2.BORDER_REPLICATE,
    )


def sharpen(image):
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], dtype=np.float32)
    return cv2.filter2D(image, -1, kernel)
```

### 4.4 Morphological preprocess — what and why

Used only on **layer 3**, on the **full** image.

| Step | OpenCV | Why |
|---|---|---|
| BGR → gray | `cvtColor COLOR_BGR2GRAY` | Threshold needs 1 channel |
| Adaptive mean threshold, **binary inverted** | `ADAPTIVE_THRESH_MEAN_C`, `THRESH_BINARY_INV`, block **11**, C **10** | Local lighting / glare on bottles; invert so **text is white on black** for close |
| Morphological **close** | `MORPH_CLOSE`, kernel **2×2** ones, uint8 | Close = dilate then erode; **reconnect broken strokes** in small expiry digits |
| Invert again | `bitwise_not` | Back to **black text on white** (document-like) for the VLM |
| Save via PIL | `Image.fromarray` | Morph array is grayscale; PIL writes PNG |

**Why not always morph first:** binarization destroys color, logos, and weak print; VLMs often do better on natural RGB. Morph is a **failsafe** when the model cannot read the photo.

**Parameter sensitivity:**

- Block size **11** must be odd.
- C **10** is fairly aggressive (more of the image becomes “background”).
- 2×2 close is small — meant for thin glyphs, not large blobs.

### 4.5 Code to port: morphological preprocess

```python
import cv2
import numpy as np
from PIL import Image


def morphological_preprocess(image_path, save_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        11, 10,
    )
    kernel = np.ones((2, 2), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    pil_image = Image.fromarray(cv2.bitwise_not(morph))
    pil_image.save(save_path)
    return save_path
```

### 4.6 Code to port: four-layer orchestrator

```python
import os
import cv2


def enhanced_four_layer_failsafe_analysis(
    cropped_image_path, full_image_path, dewarped_dir, detector
):
    """Waterfall: dewarped crop -> raw crop -> morph full -> raw full."""
    os.makedirs(dewarped_dir, exist_ok=True)

    # Layer 1
    try:
        cropped_img = cv2.imread(cropped_image_path)
        if cropped_img is not None:
            dewarped_img = dewarp_image(cropped_img)
            dewarped_filename = os.path.basename(cropped_image_path).replace(
                ".png", "_dewarped.png"
            )
            dewarped_path = os.path.join(dewarped_dir, dewarped_filename)
            cv2.imwrite(dewarped_path, dewarped_img)
            dewarped_result = detector.detect_with_maverick(dewarped_path)
            if detector.is_result_fruitful(dewarped_result):
                return process_maverick_result(
                    dewarped_result, "Layer 1 - Dewarped Cropped"
                )
    except Exception as e:
        print(f"Layer 1 failed: {str(e)}")

    # Layer 2
    try:
        rawcropped_result = detector.detect_with_maverick(cropped_image_path)
        if detector.is_result_fruitful(rawcropped_result):
            return process_maverick_result(
                rawcropped_result, "Layer 2 - Raw Cropped"
            )
    except Exception as e:
        print(f"Layer 2 failed: {str(e)}")

    # Layer 3
    try:
        morph_path = full_image_path.replace(".png", "_morph.png")
        morphological_preprocess(full_image_path, morph_path)
        morph_result = detector.detect_with_maverick(morph_path)
        if detector.is_result_fruitful(morph_result):
            return process_maverick_result(morph_result, "Layer 3 - Morph Full")
    except Exception as e:
        print(f"Layer 3 failed: {str(e)}")

    # Layer 4
    try:
        rawfull_result = detector.detect_with_maverick(full_image_path)
        if detector.is_result_fruitful(rawfull_result):
            return process_maverick_result(rawfull_result, "Layer 4 - Raw Full")
    except Exception as e:
        print(f"Layer 4 failed: {str(e)}")

    return {
        "manufacturing_date": "All layers failed",
        "expiry_date": "All layers failed",
        "status": "All four detection layers failed. Please try with a clearer image.",
        "year1": "Detection failed",
        "year2": "Detection failed",
        "month1": "Detection failed",
        "month2": "Detection failed",
        "detection_method": "Complete failure - all 4 layers failed",
    }
```

**Porting bug to fix:** Layer 1 filename uses `.replace('.png', '_dewarped.png')`. `.jpg` files will **not** get `_dewarped` in the name. Use `os.path.splitext`.

### 4.7 Image validation before Groq (`open_and_validate_image`)

```python
from PIL import Image


def open_and_validate_image(image_path):
    try:
        with Image.open(image_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            temp_path = image_path.replace(".png", "_temp.png")
            img.save(temp_path, "PNG")
            return temp_path if temp_path != image_path else image_path
    except Exception as e:
        print(f"Error opening image: {str(e)}")
        return None
```

**Why:** Groq vision expects a consistent RGB PNG. Morph output is mode `L` (grayscale); this converts it to RGB before base64.

**Quirk:** If the file is already RGB PNG, it still writes `_temp.png` and returns that path. Same `.png`-only replace issue as dewarp filenames.

Encode: raw bytes → `base64.b64encode` → data URL `data:image/jpeg;base64,...` even when the file is PNG (MIME mismatch; usually still works).

---

## 5. VLM call (not a geometric transform, but the consumer)

### 5.1 Web: OpenRouter

- Model: `nvidia/nemotron-nano-12b-v2-vl:free`
- `max_tokens`: 500, `temperature`: 0.3, `top_p`: 0.9, `top_k`: 40
- Prompt asks for JSON with `manufacturing_date_standard` / `expiry_date_standard` as `MMM YYYY`
- Crop selection: prefer high confidence; stop early on `confidence == high`; else full image

### 5.2 Batch: Groq Llama Maverick

- Model: `meta-llama/llama-4-maverick-17b-128e-instruct`
- `max_tokens`: 2048, `temperature`: 0.0, `response_format: json_object`
- Prompt is longer (many date formats, Julian dates, batch codes)

**Do not copy API keys from source.** Both files currently hardcode keys; a new implementation should use environment variables.

---

## 6. Recommended port: combine the two pipelines

The original product **localized** with YOLO (`views.py`) and **dewarped** in a separate script (`dates.py`). For a new version:

```
upload
  → save original
  → YOLO 640² predict
  → mask → contour → polygon crop (original res)
  → Layer 1: dewarp+sharpen crop → VLM
  → Layer 2: raw crop → VLM
  → Layer 3: morph full → VLM
  → Layer 4: raw full → VLM
```

Optional upgrades (not in this repo, but match the *intent* of dewarp):

1. **True document unwarp:** detect 4 corners of the label (`approxPolyDP` on the YOLO contour) and `warpPerspective` to a rectangle of size `(max(w), max(h))`.
2. **Cylindrical unwrap:** if the object is a bottle, map columns with a cosine/cylinder model.
3. **Letterbox YOLO** instead of stretch-resize.
4. **CLAHE** on L-channel before VLM (gentle contrast without destroying color).
5. Keep morph **only** as failsafe.

---

## 7. File map (this repo)

| Path | Role |
|---|---|
| `expiry_app/views.py` | Django upload, YOLO crop, OpenRouter detect, expiry status |
| `dates.py` | Dewarp, morph, Groq Maverick, 4-layer failsafe, CSV batch |
| `expiry_app/urls.py` | Routes `home`, `segment_image`, `results` |
| `templates/home.html` / `results.html` | UI; shows YOLO crops |
| `model/best.pt` | YOLO segmentation weights (not in git listing here; required at runtime) |
| `static/raw_images/` | Uploads |
| `static/yolo_output/` | Crops |
| `main.py` | Unused hello stub |
| `expiry_app/models.py` | Empty Django models |

---

## 8. Tech spec checklist for a reimplementation

**Must match if you want behavioral parity with `dates.py` dewarp:**

- [ ] Source corners: `(0,0)`, `(w-1,0)`, `(0,h-1)`, `(w-1,h-1)`
- [ ] Dest bottom: `(offset, h-1)`, `(w-offset, h-1)` with `offset = min(50, w//8)`
- [ ] `getPerspectiveTransform` + `warpPerspective` same output size
- [ ] Sharpen kernel `[[-1,-1,-1],[-1,9,-1],[-1,-1,-1]]` via `filter2D(..., -1, kernel)`

**Must match if you want parity with morph:**

- [ ] Gray → adaptive mean INV, block 11, C 10
- [ ] Close 2×2
- [ ] Invert to black-on-white PNG

**Must match if you want parity with web YOLO crop:**

- [ ] Resize to 640×640 for predict
- [ ] Resize mask back to original `W,H`
- [ ] Filled contour mask AND original
- [ ] Area ≥ 50, box ≥ 5×5
- [ ] Top 2 crops by area
- [ ] Fallback full image

**Fruitful / JSON post-process** is independent of geometry; copy from `is_result_fruitful` / `process_maverick_result` or the OpenRouter `validate_and_fix_dates` depending on which VLM you keep.

"""
Generate a Google-Docs-friendly MedExpiry plain-language architecture guide (.docx).
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "guide_assets"
OUT = ROOT / "MedExpiry_System_Guide.docx"

TEAL = RGBColor(0x0F, 0x76, 0x6E)
TEAL_DARK = RGBColor(0x04, 0x2F, 0x2E)
MUTED = RGBColor(0x5B, 0x7C, 0x7A)
ACCENT = RGBColor(0x0D, 0x94, 0x88)


def set_run_font(run, name="Calibri", size=11, bold=False, color=None):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color


def add_page_border(section):
    """Light page margins suitable for Google Docs upload."""
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)


def shade_paragraph(paragraph, hex_color: str):
    p = paragraph._p
    pPr = p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    pPr.append(shd)


def add_heading_styled(doc, text, level=1):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16 if level == 1 else 12)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    if level == 1:
        set_run_font(run, size=18, bold=True, color=TEAL_DARK)
    elif level == 2:
        set_run_font(run, size=14, bold=True, color=TEAL)
    else:
        set_run_font(run, size=12, bold=True, color=TEAL)
    return p


def add_body(doc, text, *, space_after=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    run = p.add_run(text)
    set_run_font(run, size=11, color=TEAL_DARK)
    return p


def add_bullet(doc, text, *, bold_lead=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    if bold_lead:
        r1 = p.add_run(bold_lead)
        set_run_font(r1, size=11, bold=True, color=TEAL_DARK)
        r2 = p.add_run(text)
        set_run_font(r2, size=11, color=TEAL_DARK)
    else:
        r = p.add_run(text)
        set_run_font(r, size=11, color=TEAL_DARK)
    return p


def add_callout(doc, title: str, body: str, fill="E6FFFA"):
    p = doc.add_paragraph()
    shade_paragraph(p, fill)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Cm(0.2)
    r = p.add_run(title)
    set_run_font(r, size=11, bold=True, color=TEAL)
    p2 = doc.add_paragraph()
    shade_paragraph(p2, fill)
    p2.paragraph_format.space_after = Pt(10)
    p2.paragraph_format.left_indent = Cm(0.2)
    r2 = p2.add_run(body)
    set_run_font(r2, size=10.5, color=TEAL_DARK)


def add_image(doc, name: str, caption: str, width_in=6.2):
    path = ASSETS / name
    if not path.exists():
        add_body(doc, f"[Image missing: {name}]")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width_in))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(12)
    r = cap.add_run(caption)
    set_run_font(r, size=9, color=MUTED)


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        r = p.add_run(h)
        set_run_font(r, size=10, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), "0F766E")
        shading.set(qn("w:val"), "clear")
        hdr[i]._teCell = hdr[i]
        hdr[i]._tc.get_or_add_tcPr().append(shading)
    for ri, row in enumerate(rows):
        cells = table.rows[ri + 1].cells
        for ci, val in enumerate(row):
            cells[ci].text = ""
            p = cells[ci].paragraphs[0]
            r = p.add_run(val)
            set_run_font(r, size=10, color=TEAL_DARK)
            if ri % 2 == 1:
                shading = OxmlElement("w:shd")
                shading.set(qn("w:fill"), "F0FDFA")
                shading.set(qn("w:val"), "clear")
                cells[ci]._tc.get_or_add_tcPr().append(shading)
    doc.add_paragraph()


def build():
    doc = Document()
    section = doc.sections[0]
    add_page_border(section)

    # ---- Cover ----
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(36)
    r = title.add_run("MedExpiry")
    set_run_font(r, name="Georgia", size=32, bold=True, color=TEAL_DARK)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = sub.add_run("How the Medicine Expiry System Works")
    set_run_font(r, name="Georgia", size=18, color=TEAL)

    tag = doc.add_paragraph()
    tag.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tag.paragraph_format.space_after = Pt(6)
    r = tag.add_run(
        "A plain-language guide to the full journey — from a pack photo to a clear "
        "“expired or not” answer, including every checking step, special cases, "
        "languages, and spoken results."
    )
    set_run_font(r, size=11, color=MUTED)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.paragraph_format.space_after = Pt(18)
    r = meta.add_run("Version 1.1  ·  August 2026  ·  Written for non-technical readers")
    set_run_font(r, size=10, color=MUTED)

    add_callout(
        doc,
        "What this document is for",
        "This guide explains the MedExpiry product in everyday language. You do not "
        "need a software background. We avoid programming names and focus on what "
        "happens, why it happens, and what you will see on screen in each situation.",
    )

    # ---- 1. Big picture ----
    add_heading_styled(doc, "1. The big picture", 1)
    add_body(
        doc,
        "MedExpiry helps a household answer a simple but important question: "
        "“Is this medicine still safe to use, based on the dates printed on the pack?”",
    )
    add_body(
        doc,
        "A person takes or uploads a photo of the medicine pack (especially the area "
        "with manufacturing and expiry dates). The system carefully reads those dates, "
        "double-checks itself, applies calendar rules, and shows a clear result. "
        "If the user prefers, it can also speak the result aloud in one of several "
        "Indian languages.",
    )
    add_image(
        doc,
        "overview-user-journey.png",
        "Figure 1. The overall journey: photo → MedExpiry → careful analysis → clear spoken/written result.",
    )

    add_heading_styled(doc, "What the product does well", 2)
    add_bullet(doc, "Reads manufacturing and expiry dates from a pack photo.")
    add_bullet(doc, "Uses two independent “eyes” so one mistaken reading is less likely to win.")
    add_bullet(doc, "Brings in a third careful review only when the two readings disagree or look unsure.")
    add_bullet(doc, "Applies fixed calendar rules at the end (not a guess) to decide expired vs not expired.")
    add_bullet(doc, "Separately tells you if a human should still take a second look.")
    add_bullet(doc, "Works in ten languages and can read the answer aloud.")

    add_heading_styled(doc, "What it does not claim", 2)
    add_bullet(doc, "It does not replace a pharmacist, doctor, or official recall notice.")
    add_bullet(doc, "It cannot magically invent dates that are not visible in the photo.")
    add_bullet(doc, "Blurry, cropped, or glare-heavy photos reduce accuracy.")

    # ---- 2. What you see ----
    add_heading_styled(doc, "2. What a person sees in the app", 1)
    add_body(
        doc,
        "The MedExpiry website has a welcoming home page and a Detection page where "
        "you upload a pack photo. After analysis finishes (this can take a short while "
        "because several careful checks run), you see:",
    )
    add_bullet(doc, "Manufacturing date (as printed on the pack).", bold_lead="Manufacturing date — ")
    add_bullet(doc, "Expiry date (as printed on the pack).", bold_lead="Expiry date — ")
    add_bullet(doc, "A clear headline such as Not expired, Expired, or Unable to determine.", bold_lead="Main status — ")
    add_bullet(doc, "Whether human review is still recommended.", bold_lead="Review flag — ")
    add_bullet(doc, "Whether the two readings agreed (for transparency).", bold_lead="Agreement note — ")
    add_bullet(doc, "Listen and Stop buttons for spoken summary.", bold_lead="Speech — ")

    add_image(
        doc,
        "result-outcomes.png",
        "Figure 2. The three main outcomes people can see, plus the separate human-review flag.",
    )

    add_callout(
        doc,
        "Two separate answers (this matters)",
        "“Not expired / Expired” is decided from the expiry date and today’s calendar. "
        "“Needs human review / No human review needed” is a separate trust signal. "
        "A pack can be Not expired and still need human review if the pipeline was "
        "uncertain — or Not expired with no review needed when everything checked out cleanly.",
        fill="FEFCE8",
    )

    # ---- 3. Pipeline ----
    add_heading_styled(doc, "3. The step-by-step checking process", 1)
    add_body(
        doc,
        "Behind the scenes, MedExpiry runs a fixed sequence of steps — like a checklist "
        "that never skips a stage. Think of it as a production line for reading dates "
        "safely. Some steps use advanced vision models; some steps use plain, fixed "
        "rules that never “hallucinate.”",
    )
    add_image(
        doc,
        "pipeline-nodes.png",
        "Figure 3. The six main steps from finding the date area to the final calendar decision.",
    )

    # Step 1
    add_heading_styled(doc, "Step 1 — Find the date area on the pack", 2)
    add_body(
        doc,
        "Before trying to read tiny printed characters, the system first tries to "
        "locate the region on the pack that usually holds manufacturing and expiry "
        "markings. This is done with a specialist detector (YOLO) trained for those date "
        "regions (not a general “chat” model inventing a box). After the crop is made, "
        "the system also saves a mildly straightened and sharpened helper picture of "
        "that same crop. The helper is extra context — it does not replace the real photo, "
        "and it is never applied before the date-area detector runs.",
    )
    add_heading_styled(doc, "Scenarios in this step", 3)
    add_bullet(
        doc,
        "The detector finds the date region. The system crops that area, adds a little "
        "padding around the edges (so letters are not cut off), and enlarges small crops "
        "so the next steps can read them more clearly. A straightened helper copy of "
        "that crop is saved at the same time.",
        bold_lead="Success — ",
    )
    add_bullet(
        doc,
        "The detector cannot find a clear date region (unusual lighting, odd angle, "
        "or pack style). The system does not give up. It falls back to using the whole "
        "photo as the crop, and continues. Quality may be lower, but the pipeline still runs.",
        bold_lead="Miss / fallback — ",
    )
    add_callout(
        doc,
        "Why this step matters for quality",
        "Reading an entire busy pack photo is harder than reading a close-up of the "
        "date strip. Finding the right area first improves accuracy and reduces mistakes "
        "from nearby text (batch numbers, addresses, logos).",
    )

    # Step 2
    add_heading_styled(doc, "Step 2 — First careful reading", 2)
    add_body(
        doc,
        "A vision model (Qwen 3.6 27B, via Groq) looks at two pictures of the same "
        "cropped date area in one step: the natural close-up (primary) and the "
        "straightened, sharpened helper. It must transcribe from the natural photo. "
        "It may use the helper only to resolve an unclear digit. If the two views "
        "disagree, it is told to prefer the natural photo unless a character is clearly "
        "more readable on the helper. It is instructed not to invent a “plausible” date "
        "when text is unreadable. It also reports how confident it feels about each "
        "field (high, medium, or low).",
    )
    add_heading_styled(doc, "Scenarios in this step", 3)
    add_bullet(doc, "Both dates are clear → high confidence values are returned.", bold_lead="Clear print — ")
    add_bullet(doc, "One character is smudged → medium or low confidence, with honesty preferred over guessing.", bold_lead="Partly unclear — ")
    add_bullet(doc, "A field is missing or fully illegible → that field is left empty rather than invented.", bold_lead="Missing field — ")

    # Step 3
    add_heading_styled(doc, "Step 3 — Second independent reading", 2)
    add_body(
        doc,
        "A second reading is done with the same kind of model (Qwen 3.6 27B on Groq) "
        "on the natural RGB crop only — not the straightened helper, and not the first "
        "reader’s answer. That keeps the second check independent, so it cannot simply "
        "copy the first mistake or a warp artifact.",
    )
    add_heading_styled(doc, "Scenarios in this step", 3)
    add_bullet(doc, "Same dates as the first reading → strong agreement later.", bold_lead="Agreement path — ")
    add_bullet(doc, "Different digits or month names → disagreement path later.", bold_lead="Disagreement path — ")
    add_bullet(
        doc,
        "Sometimes the second reader returns only a label fragment such as “EXP.” or "
        "“MFG” without numbers. The system treats that specially in the next step so "
        "a real numeric date from the first reader is not thrown away.",
        bold_lead="Label-only noise — ",
    )

    # Step 4
    add_heading_styled(doc, "Step 4 — Compare the two readings", 2)
    add_body(
        doc,
        "This step does not use an AI model. It uses fixed comparison rules: clean up "
        "spacing and letter case, then compare manufacturing and expiry strings, and "
        "look at confidence flags.",
    )
    add_image(
        doc,
        "consensus-scenarios.png",
        "Figure 4. How the comparison step decides whether to go straight to calendar checks or ask for an extra review.",
    )
    add_heading_styled(doc, "Scenarios covered by comparison", 3)
    add_bullet(
        doc,
        "Both readings match and confidence is not low → use those dates and go straight "
        "to calendar validation (fast, common happy path).",
        bold_lead="Clear agreement — ",
    )
    add_bullet(
        doc,
        "Both readings match, but at least one field was marked low confidence → still "
        "send to extra review. Two models can agree on the same wrong guess when print is poor.",
        bold_lead="Agreement but unsure — ",
    )
    add_bullet(
        doc,
        "Manufacturing or expiry differs between the two readings → extra review.",
        bold_lead="Disagreement — ",
    )
    add_bullet(
        doc,
        "Second reading looks like label words without digits, while first reading has "
        "real numbers → keep the first reading as a match and skip unnecessary extra review.",
        bold_lead="Label-prefix guard — ",
    )

    # Step 5
    add_heading_styled(doc, "Step 5 — Extra careful review (only when needed)", 2)
    add_body(
        doc,
        "When readings disagree or look unsure, a third vision review "
        "(Nemotron Omni on OpenRouter) looks at the natural crop again with both "
        "candidate answers, plus a high-contrast black-and-white helper made only "
        "for this step (morphological processing). It must prefer the natural photo "
        "and use the high-contrast helper only when a disputed character is clearer "
        "there. It is asked to justify the choice from what is visually present — "
        "not from what “sounds like a normal medicine date.”",
    )
    add_heading_styled(doc, "Scenarios in this step", 3)
    add_bullet(
        doc,
        "The third review can clearly see which digits are correct → it returns a resolved "
        "final manufacturing and/or expiry value.",
        bold_lead="Resolved — ",
    )
    add_bullet(
        doc,
        "The disputed character is still illegible even on close look → it marks the case "
        "unresolved. Later steps will flag human review rather than forcing a fake answer.",
        bold_lead="Unresolved — ",
    )
    add_bullet(
        doc,
        "If the earlier comparison already matched confidently, this step is skipped. "
        "That saves time and cost on clear packs.",
        bold_lead="Skipped on clear match — ",
    )

    # Step 6
    add_heading_styled(doc, "Step 6 — Calendar and format rules (final gate)", 2)
    add_body(
        doc,
        "This is the last word on pipeline trust for acceptance. It is not an AI guess. "
        "It parses the printed date into a real calendar meaning and applies strict checks.",
    )
    add_body(
        doc,
        "Many pack formats are supported, including styles like APR.2024, MAR.2027, "
        "08/2024, 2024-08, 15-08-2024, 15 AUG 2024, and several compact numeric forms. "
        "If a date shows only month and year (common on packs), the medicine is treated "
        "as valid through the last day of that month.",
    )
    add_heading_styled(doc, "Checks performed", 3)
    add_bullet(doc, "Can the expiry date be understood as a real date format?")
    add_bullet(doc, "Is the pack still within its valid period relative to today?")
    add_bullet(doc, "If manufacturing date exists, does expiry come after (or at) manufacturing?")
    add_bullet(doc, "Did an earlier extra review leave the case unresolved?")
    add_heading_styled(doc, "Outcomes of this gate", 3)
    add_bullet(
        doc,
        "All required checks pass → the pipeline marks the case as accepted (trusted enough).",
        bold_lead="Accepted — ",
    )
    add_bullet(
        doc,
        "Any required check fails (unreadable expiry, already past validity, impossible "
        "date order, unresolved dispute) → human review is flagged.",
        bold_lead="Human review — ",
    )

    # ---- 4. Final assessment for the user ----
    add_heading_styled(doc, "4. Turning pipeline results into what people understand", 1)
    add_body(
        doc,
        "After the checklist finishes, MedExpiry creates a simple assessment for the screen "
        "and for speech. This assessment is calculated with the same date rules on the "
        "server — the website does not recalculate expiry on its own. That keeps answers consistent.",
    )
    add_table(
        doc,
        ["What you see", "What it means", "Typical cause"],
        [
            [
                "Not expired",
                "Expiry date is still within its valid period (including end-of-month for month-only dates).",
                "Clear future expiry such as MAR.2027 when today is earlier.",
            ],
            [
                "Expired",
                "Today is after the last valid day of the expiry period.",
                "Past month/year such as APR.2024 when today is later.",
            ],
            [
                "Unable to determine",
                "Expiry could not be read as a known date format.",
                "Missing, garbled, or non-date text.",
            ],
            [
                "No human review needed",
                "Pipeline accepted the case and expiry was readable.",
                "Clean agreement + calendar checks passed.",
            ],
            [
                "Needs human review",
                "Pipeline was not fully confident, or expiry was unreadable.",
                "Disagreement, low confidence, unresolved review, or bad parse.",
            ],
        ],
    )

    add_heading_styled(doc, "Combined scenarios people actually encounter", 2)
    add_bullet(
        doc,
        "Clear photo, both readings agree, future expiry → Not expired + No human review needed. "
        "(This matches a healthy pack like manufacturing APR.2024 and expiry MAR.2027.)",
        bold_lead="Best case — ",
    )
    add_bullet(
        doc,
        "Clear photo of an old pack whose expiry month has passed → Expired. Human review "
        "depends on whether calendar/format checks were fully satisfied.",
        bold_lead="Expired pack — ",
    )
    add_bullet(
        doc,
        "Two readings disagree, third review resolves the digits, expiry still in the future → "
        "Not expired, but may still show Needs human review depending on acceptance rules.",
        bold_lead="Hard photo, recovered — ",
    )
    add_bullet(
        doc,
        "Third review cannot resolve the disputed digit → Unable to determine or incomplete "
        "dates, with Needs human review.",
        bold_lead="Truly illegible — ",
    )
    add_bullet(
        doc,
        "Detector missed the strip, full photo used as fallback → pipeline still runs; "
        "risk of weaker readings and more review flags.",
        bold_lead="Fallback crop — ",
    )
    add_bullet(
        doc,
        "Second reading returns “EXP.” only → system keeps the numeric first reading when appropriate.",
        bold_lead="Label noise — ",
    )

    # ---- 5. Languages & TTS ----
    add_heading_styled(doc, "5. Languages and spoken results", 1)
    add_body(
        doc,
        "MedExpiry is built for Indian households where not everyone reads English comfortably. "
        "The interface and the spoken summary follow the language chosen in the app.",
    )
    add_image(
        doc,
        "languages-tts.png",
        "Figure 5. Choose a language, then use Listen / Stop to hear the result.",
    )
    add_heading_styled(doc, "Supported languages", 2)
    add_body(
        doc,
        "English, Hindi, Tamil, Telugu, Marathi, Bengali, Gujarati, Kannada, Malayalam, and Punjabi. "
        "The choice is remembered on the device for the next visit.",
    )
    add_heading_styled(doc, "How speech works", 2)
    add_bullet(doc, "The server decides the facts (dates, expired or not, review needed).")
    add_bullet(
        doc,
        "When you tap Listen, the server builds one spoken paragraph in the selected "
        "language (verdict first, then dates, then whether human review is needed) "
        "and returns audio from Microsoft Edge neural text-to-speech (no extra API key).",
    )
    add_bullet(doc, "The app plays that audio; Stop immediately cancels playback.")
    add_callout(
        doc,
        "Design choice in plain words",
        "Screen labels live with the app (so the interface feels fast and local). "
        "Spoken wording and the voice are produced on the server so every language "
        "we list can actually be heard, not only English and Hindi. The hard facts — "
        "whether the medicine is expired — are still decided with the same calendar rules.",
    )

    # ---- 6. Quality ----
    add_heading_styled(doc, "6. Overall pipeline quality — why this design is careful", 1)
    add_body(
        doc,
        "MedExpiry is intentionally cautious. Healthcare-adjacent tools should prefer "
        "“I am unsure — please check” over a confident wrong date.",
    )
    add_heading_styled(doc, "Quality principles built into the flow", 2)
    add_bullet(doc, "Locate first, then read (better focus on the right print).", bold_lead="Focus — ")
    add_bullet(doc, "Two independent readings reduce single-model mistakes.", bold_lead="Redundancy — ")
    add_bullet(doc, "Extra review only when needed (efficient and safer on hard cases).", bold_lead="Selective escalation — ")
    add_bullet(doc, "Final acceptance uses fixed calendar rules, not model opinion.", bold_lead="Deterministic last word — ")
    add_bullet(doc, "Abstain rather than invent illegible digits.", bold_lead="Honesty — ")
    add_bullet(doc, "Human-review flag is shown separately from expired/not expired.", bold_lead="Clear communication — ")
    add_bullet(doc, "Long analysis window supported (vision checks can take time).", bold_lead="Patience — ")

    add_heading_styled(doc, "What improves results in real homes", 2)
    add_bullet(doc, "Bright, even lighting without strong glare.")
    add_bullet(doc, "Fill the frame with the date print (MFG / EXP area).")
    add_bullet(doc, "Keep the camera steady; avoid motion blur.")
    add_bullet(doc, "Prefer JPEG/PNG/WebP/BMP photos from the pack itself (not a screenshot of a screenshot).")

    add_heading_styled(doc, "Known limits (honest)", 2)
    add_bullet(doc, "Very damaged, faded, or handwritten overprints may remain unreadable.")
    add_bullet(doc, "Unusual date formats outside the supported set may need human review.")
    add_bullet(doc, "Spoken audio is generated on the server so it is not limited to voices installed on the phone.")
    add_bullet(doc, "The tool reads printed dates; it does not verify whether the medicine was stored correctly.")

    # ---- 7. End-to-end walkthrough ----
    add_heading_styled(doc, "7. A complete example walkthrough", 1)
    add_body(
        doc,
        "Imagine a blister pack photo showing manufacturing APR.2024 and expiry MAR.2027, "
        "taken in August 2026.",
    )
    add_bullet(doc, "Date area is found and cropped; a straightened helper copy is saved.")
    add_bullet(doc, "First reading (Qwen 3.6 27B) sees the natural crop plus the helper and returns APR.2024 and MAR.2027 with good confidence.")
    add_bullet(doc, "Second independent reading returns the same values.")
    add_bullet(doc, "Comparison: clear agreement → skip extra review.")
    add_bullet(doc, "Calendar rules: MAR.2027 is still valid through the end of March 2027 → not expired.")
    add_bullet(doc, "Acceptance checks pass → no human review needed.")
    add_bullet(doc, "Screen shows Not expired; Listen can speak that summary in the chosen language.")

    add_body(
        doc,
        "Now imagine the same pack but the second reading mis-reads the year. Comparison "
        "detects disagreement → extra review looks again → if it resolves to MAR.2027, "
        "calendar rules still say not expired. If it cannot resolve the year, the app "
        "will not pretend certainty and will ask for human review.",
    )

    # ---- 8. Closing ----
    add_heading_styled(doc, "8. Summary for decision-makers", 1)
    add_body(
        doc,
        "MedExpiry combines specialist date-area detection (YOLO), dual independent "
        "readings (Qwen 3.6 27B), optional third-party adjudication (Nemotron Omni), "
        "mild crop helpers for hard print, and strict calendar validation. Users receive "
        "a plain expired/not-expired answer plus a separate review flag, in multiple Indian "
        "languages, with optional speech. The design prioritizes safety and honesty over "
        "speed-at-all-costs guessing.",
    )
    add_callout(
        doc,
        "One sentence takeaway",
        "Upload a pack photo → the system finds the dates, double-checks them, applies "
        "calendar rules, and tells you clearly whether the medicine looks expired — and "
        "whether a person should still verify.",
        fill="CCFBF1",
    )

    footer = doc.add_paragraph()
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.paragraph_format.space_before = Pt(24)
    r = footer.add_run(
        "MedExpiry System Guide  ·  Compatible with Microsoft Word and Google Docs  ·  "
        "Upload this .docx file to Google Drive and open with Google Docs"
    )
    set_run_font(r, size=9, color=MUTED)

    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()

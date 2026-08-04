import { Navigate, Route, Routes } from "react-router-dom";
import LandingPage from "../../features/landing/components/LandingPage";
import DetectionPage from "../../features/detection/components/DetectionPage";

/**
 * App route table:
 * - `/` landing
 * - `/detect` medicine pack detection
 * - unknown paths redirect home
 */
export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/detect" element={<DetectionPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import AppRoutes from "./app/routes/AppRoutes";

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
      <Toaster
        position="top-right"
        toastOptions={{
          className: "font-body text-sm",
          style: {
            background: "#fff",
            color: "var(--color-ink)",
            border: "1px solid rgba(15, 61, 58, 0.1)",
          },
          error: {
            style: {
              color: "var(--color-danger)",
            },
          },
        }}
      />
    </BrowserRouter>
  );
}

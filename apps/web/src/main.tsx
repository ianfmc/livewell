import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ThemeProvider } from "./components/theme-provider";
import "./index.css";
import App from "./App";

async function prepare() {
  if (import.meta.env.DEV) {
    const { worker } = await import("./mocks/browser");
    return worker.start({ onUnhandledRequest: "bypass" });
  }
}

prepare()
  .then(() => {
    createRoot(document.getElementById("root")!).render(
      <StrictMode>
        <BrowserRouter>
          <ThemeProvider>
            <App />
          </ThemeProvider>
        </BrowserRouter>
      </StrictMode>,
    );
  })
  .catch(console.error);

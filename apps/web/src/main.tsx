import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { A2uiProvider } from './a2ui/A2uiProvider';
import { ThemeProvider } from "./components/theme-provider";
import "./index.css";
import App from "./App";

async function prepare() {
  if (import.meta.env.VITE_USE_MOCKS === 'true') {
    const { worker } = await import("./mocks/browser");
    return worker.start({ onUnhandledRequest: "bypass" });
  }
}

prepare()
  .then(() => {
    createRoot(document.getElementById("root")!).render(
      <StrictMode>
        <BrowserRouter>
          <A2uiProvider>
            <ThemeProvider>
              <App />
            </ThemeProvider>
          </A2uiProvider>
        </BrowserRouter>
      </StrictMode>,
    );
  })
  .catch(console.error);

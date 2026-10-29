import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";

const rootElement = document.getElementById("root");

if (!rootElement) {
  const errorMsg = "Critical error: Missing root element (#root) in index.html. DarkShield AI cannot mount.";
  console.error(errorMsg);
  const fallback = document.createElement("div");
  fallback.style.padding = "20px";
  fallback.style.color = "#dc2626";
  fallback.style.fontFamily = "sans-serif";
  fallback.innerText = errorMsg;
  document.body.appendChild(fallback);
  throw new Error(errorMsg);
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);

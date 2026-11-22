import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { ProvedorDeSessao } from "./sessao";
import "./estilos.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ProvedorDeSessao>
      <App />
    </ProvedorDeSessao>
  </StrictMode>,
);

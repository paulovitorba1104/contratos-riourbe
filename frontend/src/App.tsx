import { Navigate, Route, Routes } from "react-router-dom";

import { BarraSuperior } from "./components/BarraSuperior";
import { Rodape } from "./components/Rodape";
import { AuthProvider, useAuth } from "./lib/AuthContext";
import { ToastProvider } from "./lib/ToastContext";
import { Atas } from "./pages/contratos/Atas";
import { ContratoDetalhe } from "./pages/contratos/ContratoDetalhe";
import { ContratosKanban } from "./pages/contratos/ContratosKanban";
import { Fiscais } from "./pages/contratos/Fiscais";
import { Fornecedores } from "./pages/contratos/Fornecedores";
import { NovoContrato } from "./pages/contratos/NovoContrato";
import { ConfiguracaoFaturamento } from "./pages/faturas/ConfiguracaoFaturamento";
import { FaturaDetalhe } from "./pages/faturas/FaturaDetalhe";
import { FaturasKanban } from "./pages/faturas/FaturasKanban";
import { Medicoes } from "./pages/faturas/Medicoes";
import { NovaFatura } from "./pages/faturas/NovaFatura";
import { PainelAnual } from "./pages/faturas/PainelAnual";
import { Hub } from "./pages/Hub";
import { Login } from "./pages/Login";

function RotaProtegida({ children }: { children: React.ReactNode }) {
  const { usuario, carregando } = useAuth();

  if (carregando) {
    return <div className="flex min-h-screen items-center justify-center">Carregando...</div>;
  }
  if (!usuario) {
    return <Navigate to="/login" replace />;
  }
  return (
    <>
      <BarraSuperior />
      {children}
    </>
  );
}

function Rotas() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RotaProtegida>
            <Hub />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos"
        element={
          <RotaProtegida>
            <ContratosKanban />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/novo"
        element={
          <RotaProtegida>
            <NovoContrato />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/atas"
        element={
          <RotaProtegida>
            <Atas />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/fiscais"
        element={
          <RotaProtegida>
            <Fiscais />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/fornecedores"
        element={
          <RotaProtegida>
            <Fornecedores />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/:id"
        element={
          <RotaProtegida>
            <ContratoDetalhe />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas"
        element={
          <RotaProtegida>
            <FaturasKanban />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/nova"
        element={
          <RotaProtegida>
            <NovaFatura />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/painel-anual"
        element={
          <RotaProtegida>
            <PainelAnual />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/medicoes"
        element={
          <RotaProtegida>
            <Medicoes />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/configuracao"
        element={
          <RotaProtegida>
            <ConfiguracaoFaturamento />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/:id"
        element={
          <RotaProtegida>
            <FaturaDetalhe />
          </RotaProtegida>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Rotas />
        <Rodape />
      </ToastProvider>
    </AuthProvider>
  );
}

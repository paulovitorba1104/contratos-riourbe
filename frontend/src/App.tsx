import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import { AuthProvider, useAuth } from "./lib/AuthContext";
import { podeAcessar, type ModuloSistema } from "./lib/navegacao";
import { ToastProvider } from "./lib/ToastContext";
import { Cadastro } from "./pages/Cadastro";
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
import { TrocarSenha } from "./pages/TrocarSenha";
import { Usuarios } from "./pages/Usuarios";

function SemAcesso() {
  return (
    <div className="page-shell">
      <main className="mx-auto max-w-xl p-6">
        <div className="card p-6">
          <h1 className="text-base font-semibold text-slate-900">Sem acesso a este módulo</h1>
          <p className="mt-1 text-sm text-slate-600">
            Peça a um administrador para liberar este módulo para você.
          </p>
          <Link to="/" className="btn-secondary btn-sm mt-4 inline-flex">
            Voltar ao início
          </Link>
        </div>
      </main>
    </div>
  );
}

function RotaProtegida({ children, modulo }: { children: React.ReactNode; modulo?: ModuloSistema }) {
  const { usuario, carregando } = useAuth();
  const { pathname } = useLocation();

  if (carregando) {
    return <div className="flex min-h-screen items-center justify-center">Carregando...</div>;
  }
  if (!usuario) {
    return <Navigate to="/login" replace />;
  }
  // Senha temporária: a API recusa tudo até a troca, então a tela também.
  if (usuario.trocar_senha_obrigatorio) {
    return pathname === "/trocar-senha" ? <TrocarSenha /> : <Navigate to="/trocar-senha" replace />;
  }
  if (modulo && !podeAcessar(usuario, modulo)) {
    return (
      <AppShell>
        <SemAcesso />
      </AppShell>
    );
  }
  return <AppShell>{children}</AppShell>;
}

function Rotas() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/cadastro" element={<Cadastro />} />
      <Route
        path="/"
        element={
          <RotaProtegida>
            <Hub />
          </RotaProtegida>
        }
      />
      <Route
        path="/trocar-senha"
        element={
          <RotaProtegida>
            <TrocarSenha />
          </RotaProtegida>
        }
      />
      <Route
        path="/usuarios"
        element={
          <RotaProtegida>
            <Usuarios />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos"
        element={
          <RotaProtegida modulo="contratos">
            <ContratosKanban />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/novo"
        element={
          <RotaProtegida modulo="contratos">
            <NovoContrato />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/atas"
        element={
          <RotaProtegida modulo="contratos">
            <Atas />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/fiscais"
        element={
          <RotaProtegida modulo="contratos">
            <Fiscais />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/fornecedores"
        element={
          <RotaProtegida modulo="contratos">
            <Fornecedores />
          </RotaProtegida>
        }
      />
      <Route
        path="/contratos/:id"
        element={
          <RotaProtegida modulo="contratos">
            <ContratoDetalhe />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas"
        element={
          <RotaProtegida modulo="faturas">
            <FaturasKanban />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/nova"
        element={
          <RotaProtegida modulo="faturas">
            <NovaFatura />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/painel-anual"
        element={
          <RotaProtegida modulo="faturas">
            <PainelAnual />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/medicoes"
        element={
          <RotaProtegida modulo="faturas">
            <Medicoes />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/configuracao"
        element={
          <RotaProtegida modulo="faturas">
            <ConfiguracaoFaturamento />
          </RotaProtegida>
        }
      />
      <Route
        path="/faturas/:id"
        element={
          <RotaProtegida modulo="faturas">
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
      </ToastProvider>
    </AuthProvider>
  );
}

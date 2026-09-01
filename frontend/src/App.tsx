import { Navigate, Route, Routes } from "react-router-dom";

import { Rodape } from "./components/Rodape";
import { AuthProvider, useAuth } from "./lib/AuthContext";
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
  return <>{children}</>;
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
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Rotas />
      <Rodape />
    </AuthProvider>
  );
}

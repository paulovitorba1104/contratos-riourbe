import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { api, type Usuario } from "./api";

interface AuthContextValor {
  usuario: Usuario | null;
  carregando: boolean;
  entrar: (identificador: string, senha: string) => Promise<void>;
  sair: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValor | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    api
      .me()
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setCarregando(false));
  }, []);

  async function entrar(identificador: string, senha: string) {
    const resposta = await api.login(identificador, senha);
    setUsuario(resposta.usuario);
  }

  async function sair() {
    await api.logout();
    setUsuario(null);
  }

  return (
    <AuthContext.Provider value={{ usuario, carregando, entrar, sair }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValor {
  const contexto = useContext(AuthContext);
  if (!contexto) {
    throw new Error("useAuth deve ser usado dentro de AuthProvider.");
  }
  return contexto;
}

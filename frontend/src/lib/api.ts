export interface Usuario {
  id: string;
  nome: string;
  matricula: string | null;
  cpf: string;
  email: string;
  papel: "administrador" | "operador";
  ativo: boolean;
}

class ErroApi extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function requisicao<T>(caminho: string, init?: RequestInit): Promise<T> {
  const resposta = await fetch(`/api${caminho}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!resposta.ok) {
    let mensagem = "Erro ao comunicar com o servidor.";
    try {
      const corpo = await resposta.json();
      mensagem = corpo.detail ?? mensagem;
    } catch {
      // corpo sem JSON — mantém mensagem genérica
    }
    throw new ErroApi(resposta.status, mensagem);
  }

  if (resposta.status === 204) {
    return undefined as T;
  }
  return (await resposta.json()) as T;
}

export const api = {
  login: (identificador: string, senha: string) =>
    requisicao<{ usuario: Usuario }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identificador, senha }),
    }),
  logout: () => requisicao<void>("/auth/logout", { method: "POST" }),
  me: () => requisicao<Usuario>("/auth/me"),
};

export { ErroApi };

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

/** FastAPI manda `detail` como string (HTTPException) ou como lista de erros
 * de validação do Pydantic ([{loc, msg, type}, ...]) — sem isso, um 422
 * vira "[object Object]" na tela em vez da mensagem de verdade. */
function extrairMensagemErro(corpo: unknown, padrao: string): string {
  if (corpo && typeof corpo === "object" && "detail" in corpo) {
    const detail = (corpo as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      const mensagens = detail
        .map((item) => (item && typeof item === "object" && "msg" in item ? String(item.msg) : null))
        .filter((m): m is string => Boolean(m));
      if (mensagens.length > 0) {
        return mensagens.join(" ");
      }
    }
  }
  return padrao;
}

export async function requisicao<T>(caminho: string, init?: RequestInit): Promise<T> {
  const resposta = await fetch(`/api${caminho}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!resposta.ok) {
    let mensagem = "Erro ao comunicar com o servidor.";
    try {
      const corpo = await resposta.json();
      mensagem = extrairMensagemErro(corpo, mensagem);
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

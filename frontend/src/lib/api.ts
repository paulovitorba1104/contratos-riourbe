import type { ModuloSistema } from "./navegacao";

export interface Usuario {
  id: string;
  nome: string;
  matricula: string | null;
  cpf: string;
  email: string;
  papel: "administrador" | "operador";
  ativo: boolean;
  trocar_senha_obrigatorio: boolean;
  modulos: ModuloSistema[];
}

export type SituacaoUsuario = "pendente" | "recusado" | "ativo" | "desativado";

/** Como o administrador vê cada usuário na tela de Usuários. */
export interface UsuarioGestao extends Usuario {
  situacao: SituacaoUsuario;
  criado_em: string;
}

export interface AcessoUsuario {
  papel: Usuario["papel"];
  modulos: ModuloSistema[];
}

export interface DadosPessoais {
  nome: string;
  matricula: string;
  cpf: string;
  email: string;
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
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String(item.msg).replace(/^Value error, /, "")
            : null,
        )
        .filter((m): m is string => Boolean(m));
      if (mensagens.length > 0) {
        return mensagens.join(" ");
      }
    }
  }
  return padrao;
}

async function _tratarResposta<T>(resposta: Response): Promise<T> {
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

export async function requisicao<T>(caminho: string, init?: RequestInit): Promise<T> {
  const resposta = await fetch(`/api${caminho}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  return _tratarResposta<T>(resposta);
}

/** Upload de arquivo (multipart/form-data) — sem Content-Type manual: o
 * navegador define sozinho, com o boundary certo. Definir à mão (como
 * `requisicao` faz para JSON) quebraria o parsing do formulário. */
export async function requisicaoComArquivo<T>(caminho: string, formData: FormData): Promise<T> {
  const resposta = await fetch(`/api${caminho}`, {
    method: "POST",
    credentials: "include",
    body: formData,
  });
  return _tratarResposta<T>(resposta);
}

export const api = {
  login: (identificador: string, senha: string) =>
    requisicao<{ usuario: Usuario }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ identificador, senha }),
    }),
  logout: () => requisicao<void>("/auth/logout", { method: "POST" }),
  me: () => requisicao<Usuario>("/auth/me"),
  solicitarCadastro: (dados: DadosPessoais & { senha: string }) =>
    requisicao<{ mensagem: string }>("/auth/cadastro", { method: "POST", body: JSON.stringify(dados) }),
  trocarSenha: (senha_atual: string, nova_senha: string) =>
    requisicao<Usuario>("/auth/trocar-senha", {
      method: "POST",
      body: JSON.stringify({ senha_atual, nova_senha }),
    }),
};

type SenhaTemporaria = { usuario: UsuarioGestao; senha_temporaria: string };

export const apiUsuarios = {
  listar: () => requisicao<UsuarioGestao[]>("/usuarios"),
  criar: (dados: DadosPessoais & AcessoUsuario) =>
    requisicao<SenhaTemporaria>("/usuarios", { method: "POST", body: JSON.stringify(dados) }),
  aprovar: (id: string, acesso: AcessoUsuario) =>
    requisicao<UsuarioGestao>(`/usuarios/${id}/aprovar`, { method: "POST", body: JSON.stringify(acesso) }),
  recusar: (id: string) => requisicao<UsuarioGestao>(`/usuarios/${id}/recusar`, { method: "POST" }),
  atualizarAcesso: (id: string, acesso: AcessoUsuario) =>
    requisicao<UsuarioGestao>(`/usuarios/${id}/acesso`, { method: "PATCH", body: JSON.stringify(acesso) }),
  redefinirSenha: (id: string) =>
    requisicao<SenhaTemporaria>(`/usuarios/${id}/redefinir-senha`, { method: "POST" }),
  desativar: (id: string) => requisicao<void>(`/usuarios/${id}`, { method: "DELETE" }),
  reativar: (id: string) => requisicao<UsuarioGestao>(`/usuarios/${id}/reativar`, { method: "POST" }),
};

export { ErroApi };

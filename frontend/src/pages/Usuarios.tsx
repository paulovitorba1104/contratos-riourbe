import { Check, Copy, UserPlus } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";

import {
  apiUsuarios,
  ErroApi,
  type AcessoUsuario,
  type SituacaoUsuario,
  type UsuarioGestao,
} from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import { mascararCpf } from "../lib/mascaras";
import { MODULOS, type ModuloSistema } from "../lib/navegacao";
import { useToast } from "../lib/ToastContext";

const TITULO_MODULO = Object.fromEntries(MODULOS.map((m) => [m.valor, m.titulo])) as Record<ModuloSistema, string>;

function mensagemDeErro(e: unknown, padrao: string): string {
  return e instanceof ErroApi ? e.message : padrao;
}

/** Papel + módulos: usado para aprovar um pedido, editar o acesso e no
 * cadastro direto. Administrador acessa tudo, então os módulos somem. */
function CamposAcesso({ acesso, aoMudar }: { acesso: AcessoUsuario; aoMudar: (a: AcessoUsuario) => void }) {
  function alternarModulo(modulo: ModuloSistema) {
    const modulos = acesso.modulos.includes(modulo)
      ? acesso.modulos.filter((m) => m !== modulo)
      : [...acesso.modulos, modulo];
    aoMudar({ ...acesso, modulos });
  }

  return (
    <div className="space-y-3">
      <fieldset>
        <legend className="mb-1.5 text-xs font-medium text-slate-600">Papel</legend>
        <div className="flex flex-wrap gap-4 text-sm">
          {(["operador", "administrador"] as const).map((papel) => (
            <label key={papel} className="flex items-center gap-2">
              <input
                type="radio"
                name="papel"
                checked={acesso.papel === papel}
                onChange={() => aoMudar({ ...acesso, papel })}
              />
              {papel === "operador" ? "Operador" : "Administrador"}
            </label>
          ))}
        </div>
      </fieldset>

      {acesso.papel === "administrador" ? (
        <p className="rounded-md bg-slate-50 p-3 text-xs text-slate-600">
          Administrador acessa todos os módulos e gerencia usuários, inclusive aprovando pedidos de
          acesso.
        </p>
      ) : (
        <fieldset>
          <legend className="mb-1.5 text-xs font-medium text-slate-600">Módulos liberados</legend>
          <div className="space-y-2">
            {MODULOS.map((modulo) => (
              <label key={modulo.valor} className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={acesso.modulos.includes(modulo.valor)}
                  onChange={() => alternarModulo(modulo.valor)}
                />
                <span>
                  <span className="font-medium text-slate-800">{modulo.titulo}</span>
                  <span className="block text-xs text-slate-500">{modulo.descricao}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      )}
    </div>
  );
}

function acessoValido(acesso: AcessoUsuario): boolean {
  return acesso.papel === "administrador" || acesso.modulos.length > 0;
}

function FormAcesso({
  inicial,
  rotuloConfirmar,
  aoConfirmar,
  aoCancelar,
}: {
  inicial: AcessoUsuario;
  rotuloConfirmar: string;
  aoConfirmar: (acesso: AcessoUsuario) => Promise<void>;
  aoCancelar: () => void;
}) {
  const [acesso, setAcesso] = useState<AcessoUsuario>(inicial);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function confirmar() {
    setErro(null);
    setEnviando(true);
    try {
      await aoConfirmar({ ...acesso, modulos: acesso.papel === "administrador" ? [] : acesso.modulos });
    } catch (e) {
      setErro(mensagemDeErro(e, "Não foi possível salvar o acesso."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mt-3 space-y-3 rounded-lg border border-slate-200 bg-white p-4">
      <CamposAcesso acesso={acesso} aoMudar={setAcesso} />
      {!acessoValido(acesso) && <p className="text-xs text-amber-700">Escolha pelo menos um módulo.</p>}
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={confirmar}
          disabled={enviando || !acessoValido(acesso)}
          className="btn-primary btn-sm"
        >
          {enviando ? "Salvando..." : rotuloConfirmar}
        </button>
        <button type="button" onClick={aoCancelar} className="btn-secondary btn-sm">
          Cancelar
        </button>
      </div>
    </div>
  );
}

function FormNovoUsuario({
  aoCriar,
  aoCancelar,
}: {
  aoCriar: (resultado: { nome: string; senha: string }) => void;
  aoCancelar: () => void;
}) {
  const [nome, setNome] = useState("");
  const [matricula, setMatricula] = useState("");
  const [cpf, setCpf] = useState("");
  const [email, setEmail] = useState("");
  const [acesso, setAcesso] = useState<AcessoUsuario>({ papel: "operador", modulos: [] });
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      const resposta = await apiUsuarios.criar({
        nome,
        matricula,
        cpf,
        email,
        papel: acesso.papel,
        modulos: acesso.papel === "administrador" ? [] : acesso.modulos,
      });
      aoCriar({ nome: resposta.usuario.nome, senha: resposta.senha_temporaria });
    } catch (e) {
      setErro(mensagemDeErro(e, "Não foi possível cadastrar o usuário."));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={aoEnviar} className="card mb-6 space-y-4 p-5">
      <h2 className="text-sm font-semibold text-slate-900">Novo usuário</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs text-slate-600" htmlFor="novo_nome">
            Nome completo
          </label>
          <input id="novo_nome" className="field-input" value={nome} onChange={(e) => setNome(e.target.value)} required />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-600" htmlFor="novo_matricula">
            Matrícula
          </label>
          <input
            id="novo_matricula"
            className="field-input"
            value={matricula}
            onChange={(e) => setMatricula(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-600" htmlFor="novo_cpf">
            CPF
          </label>
          <input
            id="novo_cpf"
            className="field-input"
            value={cpf}
            onChange={(e) => setCpf(mascararCpf(e.target.value))}
            placeholder="000.000.000-00"
            required
          />
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-xs text-slate-600" htmlFor="novo_email">
            E-mail
          </label>
          <input
            id="novo_email"
            type="email"
            className="field-input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
      </div>
      <CamposAcesso acesso={acesso} aoMudar={setAcesso} />
      <p className="text-xs text-slate-500">
        O sistema gera uma senha temporária para você repassar; no primeiro acesso a pessoa cria a
        própria senha.
      </p>
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={enviando || !acessoValido(acesso)} className="btn-primary">
          {enviando ? "Cadastrando..." : "Cadastrar"}
        </button>
        <button type="button" onClick={aoCancelar} className="btn-secondary">
          Cancelar
        </button>
      </div>
    </form>
  );
}

function SenhaGerada({ nome, senha, aoFechar }: { nome: string; senha: string; aoFechar: () => void }) {
  const [copiada, setCopiada] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(senha);
      setCopiada(true);
    } catch {
      // Sem permissão de área de transferência: a senha continua visível para anotar.
    }
  }

  return (
    <div className="card mb-6 border-amber-200 bg-amber-50 p-5">
      <p className="text-sm font-medium text-amber-900">Senha temporária de {nome}</p>
      <div className="mt-3 flex items-center gap-2">
        <code className="rounded-md border border-amber-200 bg-white px-3 py-2 font-mono text-lg tracking-wider text-slate-900">
          {senha}
        </code>
        <button type="button" onClick={copiar} className="btn-secondary btn-sm" aria-label="Copiar senha">
          {copiada ? <Check size={14} /> : <Copy size={14} />}
          <span className="ml-1">{copiada ? "Copiada" : "Copiar"}</span>
        </button>
      </div>
      <p className="mt-3 text-xs text-amber-800">
        Ela aparece só agora: o sistema não guarda a senha em texto. Repasse ao usuário pessoalmente
        ou por um canal seguro. No primeiro acesso ele será obrigado a criar uma senha nova.
      </p>
      <button type="button" onClick={aoFechar} className="btn-primary btn-sm mt-3">
        Já repassei, ocultar
      </button>
    </div>
  );
}

function SeloSituacao({ usuario }: { usuario: UsuarioGestao }) {
  const estilos: Record<SituacaoUsuario, [string, string]> = {
    ativo: ["bg-emerald-50 text-emerald-700", "Ativo"],
    desativado: ["bg-slate-100 text-slate-500", "Desativado"],
    recusado: ["bg-red-50 text-red-700", "Pedido recusado"],
    pendente: ["bg-amber-100 text-amber-800", "Aguardando aprovação"],
  };
  const [classe, rotulo] =
    usuario.situacao === "ativo" && usuario.trocar_senha_obrigatorio
      ? ["bg-amber-100 text-amber-800", "Aguardando troca de senha"]
      : estilos[usuario.situacao];
  return <span className={`whitespace-nowrap rounded-full px-2 py-0.5 text-xs ${classe}`}>{rotulo}</span>;
}

function DescricaoAcesso({ usuario }: { usuario: UsuarioGestao }) {
  if (usuario.papel === "administrador") {
    return <span className="text-xs text-slate-600">Administrador · todos os módulos</span>;
  }
  if (usuario.modulos.length === 0) {
    return <span className="text-xs text-slate-400">Operador · nenhum módulo</span>;
  }
  return (
    <span className="flex flex-wrap items-center gap-1 text-xs text-slate-600">
      Operador ·
      {usuario.modulos.map((m) => (
        <span key={m} className="rounded bg-institucional-50 px-1.5 py-0.5 text-institucional-700">
          {TITULO_MODULO[m] ?? m}
        </span>
      ))}
    </span>
  );
}

function PedidoPendente({
  usuario,
  aoAprovar,
  aoRecusar,
}: {
  usuario: UsuarioGestao;
  aoAprovar: (acesso: AcessoUsuario) => Promise<void>;
  aoRecusar: () => void;
}) {
  const [aprovando, setAprovando] = useState(false);

  return (
    <li className="card p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="text-sm">
          <p className="font-medium text-slate-900">{usuario.nome}</p>
          <p className="text-xs text-slate-500">
            Matrícula {usuario.matricula} · CPF {mascararCpf(usuario.cpf)} · {usuario.email}
          </p>
          <p className="text-xs text-slate-400">
            Pedido em {new Date(usuario.criado_em).toLocaleString("pt-BR")}
          </p>
        </div>
        {!aprovando && (
          <div className="flex gap-2">
            <button type="button" onClick={() => setAprovando(true)} className="btn-primary btn-sm">
              Aprovar
            </button>
            <button type="button" onClick={aoRecusar} className="btn-danger btn-sm">
              Recusar
            </button>
          </div>
        )}
      </div>
      {aprovando && (
        <FormAcesso
          inicial={{ papel: "operador", modulos: [] }}
          rotuloConfirmar="Confirmar aprovação"
          aoConfirmar={aoAprovar}
          aoCancelar={() => setAprovando(false)}
        />
      )}
    </li>
  );
}

export function Usuarios() {
  const { usuario: eu } = useAuth();
  const { mostrarToast } = useToast();
  const [usuarios, setUsuarios] = useState<UsuarioGestao[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [gerada, setGerada] = useState<{ nome: string; senha: string } | null>(null);
  const [mostrarNovo, setMostrarNovo] = useState(false);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const ehAdministrador = eu?.papel === "administrador";

  function carregar() {
    apiUsuarios
      .listar()
      .then(setUsuarios)
      .catch(() => setErro("Não foi possível carregar os usuários."));
  }

  useEffect(() => {
    if (ehAdministrador) carregar();
  }, [ehAdministrador]);

  async function executar(acao: () => Promise<unknown>, sucesso: string, falha: string) {
    try {
      await acao();
      carregar();
      mostrarToast(sucesso);
    } catch (e) {
      mostrarToast(mensagemDeErro(e, falha), "erro");
    }
  }

  async function aprovar(alvo: UsuarioGestao, acesso: AcessoUsuario) {
    await apiUsuarios.aprovar(alvo.id, acesso);
    carregar();
    mostrarToast(`Acesso de ${alvo.nome} aprovado.`);
  }

  async function salvarAcesso(alvo: UsuarioGestao, acesso: AcessoUsuario) {
    await apiUsuarios.atualizarAcesso(alvo.id, acesso);
    setEditandoId(null);
    carregar();
    mostrarToast(`Acesso de ${alvo.nome} atualizado.`);
  }

  function recusar(alvo: UsuarioGestao) {
    if (!window.confirm(`Recusar o pedido de acesso de ${alvo.nome}?`)) return;
    void executar(() => apiUsuarios.recusar(alvo.id), "Pedido recusado.", "Não foi possível recusar o pedido.");
  }

  function desativar(alvo: UsuarioGestao) {
    if (!window.confirm(`Desativar ${alvo.nome}? Ele perde o acesso na hora.`)) return;
    void executar(() => apiUsuarios.desativar(alvo.id), "Usuário desativado.", "Não foi possível desativar.");
  }

  async function redefinir(alvo: UsuarioGestao) {
    const confirmado = window.confirm(
      `Gerar uma senha temporária para ${alvo.nome}? A senha atual dele deixa de funcionar na hora.`,
    );
    if (!confirmado) return;
    try {
      const resposta = await apiUsuarios.redefinirSenha(alvo.id);
      setGerada({ nome: resposta.usuario.nome, senha: resposta.senha_temporaria });
      carregar();
    } catch (e) {
      mostrarToast(mensagemDeErro(e, "Não foi possível redefinir a senha."), "erro");
    }
  }

  if (!ehAdministrador) {
    return (
      <div className="page-shell">
        <main className="mx-auto max-w-3xl p-6">
          <p className="text-sm text-slate-600">Acesso restrito a administradores.</p>
        </main>
      </div>
    );
  }

  const pendentes = usuarios.filter((u) => u.situacao === "pendente");
  const demais = usuarios.filter((u) => u.situacao !== "pendente");

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <h1 className="page-title">Usuários</h1>
          <p className="text-sm text-slate-500">
            Aprove pedidos de acesso, defina o papel e os módulos de cada pessoa e redefina senhas.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setMostrarNovo((v) => !v)}
          className="btn-primary inline-flex items-center gap-1.5"
        >
          <UserPlus size={15} />
          {mostrarNovo ? "Cancelar" : "Novo usuário"}
        </button>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 p-6">
        {erro && <p className="text-sm text-red-600">{erro}</p>}

        {gerada && <SenhaGerada nome={gerada.nome} senha={gerada.senha} aoFechar={() => setGerada(null)} />}

        {mostrarNovo && (
          <FormNovoUsuario
            aoCriar={(resultado) => {
              setMostrarNovo(false);
              setGerada(resultado);
              carregar();
            }}
            aoCancelar={() => setMostrarNovo(false)}
          />
        )}

        {pendentes.length > 0 && (
          <section>
            <h2 className="mb-2 text-sm font-semibold text-slate-900">
              Pedidos de acesso{" "}
              <span className="ml-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                {pendentes.length}
              </span>
            </h2>
            <ul className="space-y-3">
              {pendentes.map((u) => (
                <PedidoPendente
                  key={u.id}
                  usuario={u}
                  aoAprovar={(acesso) => aprovar(u, acesso)}
                  aoRecusar={() => recusar(u)}
                />
              ))}
            </ul>
          </section>
        )}

        <section className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs text-slate-500">
              <tr>
                <th className="px-4 py-2">Nome</th>
                <th className="px-4 py-2">Matrícula</th>
                <th className="px-4 py-2">Acesso</th>
                <th className="px-4 py-2">Situação</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {demais.map((u) => (
                <tr key={u.id} className="border-t border-slate-200 align-top">
                  <td className="px-4 py-2 text-slate-900">{u.nome}</td>
                  <td className="whitespace-nowrap px-4 py-2 text-slate-600">{u.matricula ?? "—"}</td>
                  <td className="px-4 py-2">
                    <DescricaoAcesso usuario={u} />
                    {editandoId === u.id && (
                      <FormAcesso
                        inicial={{ papel: u.papel, modulos: u.modulos }}
                        rotuloConfirmar={u.situacao === "recusado" ? "Confirmar aprovação" : "Salvar acesso"}
                        aoConfirmar={(acesso) =>
                          u.situacao === "recusado"
                            ? aprovar(u, acesso).then(() => setEditandoId(null))
                            : salvarAcesso(u, acesso)
                        }
                        aoCancelar={() => setEditandoId(null)}
                      />
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <SeloSituacao usuario={u} />
                  </td>
                  <td className="px-4 py-2">
                    {u.id === eu?.id ? (
                      <span className="text-xs text-slate-400">você</span>
                    ) : (
                      <div className="flex flex-wrap justify-end gap-1.5">
                        {u.situacao === "ativo" && (
                          <>
                            <button
                              type="button"
                              onClick={() => setEditandoId(editandoId === u.id ? null : u.id)}
                              className="btn-secondary btn-sm"
                            >
                              Editar acesso
                            </button>
                            <button type="button" onClick={() => redefinir(u)} className="btn-secondary btn-sm">
                              Redefinir senha
                            </button>
                            <button type="button" onClick={() => desativar(u)} className="btn-danger btn-sm">
                              Desativar
                            </button>
                          </>
                        )}
                        {u.situacao === "desativado" && (
                          <button
                            type="button"
                            onClick={() =>
                              executar(
                                () => apiUsuarios.reativar(u.id),
                                "Usuário reativado.",
                                "Não foi possível reativar.",
                              )
                            }
                            className="btn-secondary btn-sm"
                          >
                            Reativar
                          </button>
                        )}
                        {u.situacao === "recusado" && (
                          <button
                            type="button"
                            onClick={() => setEditandoId(editandoId === u.id ? null : u.id)}
                            className="btn-secondary btn-sm"
                          >
                            Aprovar mesmo assim
                          </button>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}

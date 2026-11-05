import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";

import { apiUsuarios, ErroApi, type Usuario } from "../lib/api";
import { useAuth } from "../lib/AuthContext";
import { useToast } from "../lib/ToastContext";

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
        ou por um canal seguro. No primeiro acesso ele será obrigado a criar uma senha nova, e as
        sessões que estavam abertas com a senha antiga já foram encerradas.
      </p>
      <button type="button" onClick={aoFechar} className="btn-primary btn-sm mt-3">
        Já repassei, ocultar
      </button>
    </div>
  );
}

export function Usuarios() {
  const { usuario: eu } = useAuth();
  const { mostrarToast } = useToast();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [gerada, setGerada] = useState<{ nome: string; senha: string } | null>(null);
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

  async function redefinir(alvo: Usuario) {
    const confirmado = window.confirm(
      `Gerar uma senha temporária para ${alvo.nome}? A senha atual dele deixa de funcionar na hora.`,
    );
    if (!confirmado) return;
    try {
      const resposta = await apiUsuarios.redefinirSenha(alvo.id);
      setGerada({ nome: resposta.usuario.nome, senha: resposta.senha_temporaria });
      carregar();
    } catch (e) {
      mostrarToast(e instanceof ErroApi ? e.message : "Não foi possível redefinir a senha.", "erro");
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

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <h1 className="page-title">Usuários</h1>
          <p className="text-sm text-slate-500">
            Redefinição de senha sem e-mail: gere uma senha temporária e repasse ao usuário.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-4xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        {gerada && <SenhaGerada nome={gerada.nome} senha={gerada.senha} aoFechar={() => setGerada(null)} />}

        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs text-slate-500">
              <tr>
                <th className="px-4 py-2">Nome</th>
                <th className="px-4 py-2">Matrícula</th>
                <th className="px-4 py-2">Papel</th>
                <th className="px-4 py-2">Situação</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((u) => (
                <tr key={u.id} className="border-t border-slate-200">
                  <td className="px-4 py-2 text-slate-900">{u.nome}</td>
                  <td className="px-4 py-2 text-slate-600">{u.matricula ?? "—"}</td>
                  <td className="px-4 py-2 capitalize text-slate-600">{u.papel}</td>
                  <td className="px-4 py-2">
                    {!u.ativo ? (
                      <span className="text-xs text-slate-400">Desativado</span>
                    ) : u.trocar_senha_obrigatorio ? (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
                        Aguardando troca de senha
                      </span>
                    ) : (
                      <span className="text-xs text-emerald-700">Ativo</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {u.id === eu?.id ? (
                      <span className="text-xs text-slate-400">você</span>
                    ) : (
                      u.ativo && (
                        <button type="button" onClick={() => redefinir(u)} className="btn-secondary btn-sm">
                          Redefinir senha
                        </button>
                      )
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

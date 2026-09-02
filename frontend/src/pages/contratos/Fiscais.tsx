import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiFiscais } from "../../lib/apiContratos";
import { useAuth } from "../../lib/AuthContext";
import { mascararCpf, mascararMatricula } from "../../lib/mascaras";
import type { Fiscal } from "../../lib/tiposContratos";
import { useToast } from "../../lib/ToastContext";

const campoClasse =
  "w-full rounded border border-institucional-200 px-3 py-2 text-sm focus:border-institucional-500 focus:outline-none";

function FormularioFiscal({
  inicial,
  aoSalvar,
  aoCancelar,
}: {
  inicial?: Fiscal;
  aoSalvar: (dados: { nome: string; matricula: string; cpf: string | null }) => Promise<void>;
  aoCancelar?: () => void;
}) {
  const [nome, setNome] = useState(inicial?.nome ?? "");
  const [matricula, setMatricula] = useState(inicial ? mascararMatricula(inicial.matricula) : "");
  const [cpf, setCpf] = useState(inicial?.cpf ? mascararCpf(inicial.cpf) : "");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await aoSalvar({ nome, matricula, cpf: cpf || null });
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar o fiscal.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={aoEnviar} className="mb-6 space-y-3 rounded-lg bg-white p-5 shadow-sm">
      <div>
        <label className="mb-1 block text-xs text-institucional-700" htmlFor="fiscal_nome">
          Nome
        </label>
        <input
          id="fiscal_nome"
          className={campoClasse}
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="mb-1 block text-xs text-institucional-700" htmlFor="fiscal_matricula">
          Matrícula (formato 00/000.000-0)
        </label>
        <input
          id="fiscal_matricula"
          className={campoClasse}
          value={matricula}
          onChange={(e) => setMatricula(mascararMatricula(e.target.value))}
          placeholder="00/000.000-0"
          required
        />
      </div>
      <div>
        <label className="mb-1 block text-xs text-institucional-700" htmlFor="fiscal_cpf">
          CPF (opcional, formato 000.000.000-00)
        </label>
        <input
          id="fiscal_cpf"
          className={campoClasse}
          value={cpf}
          onChange={(e) => setCpf(mascararCpf(e.target.value))}
          placeholder="000.000.000-00"
        />
      </div>
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={enviando}
          className="rounded bg-institucional-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-institucional-700 disabled:opacity-60"
        >
          {enviando ? "Salvando..." : inicial ? "Salvar alterações" : "Cadastrar"}
        </button>
        {aoCancelar && (
          <button
            type="button"
            onClick={aoCancelar}
            className="rounded border border-institucional-300 px-3 py-1.5 text-sm text-institucional-700 hover:bg-institucional-100"
          >
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}

export function Fiscais() {
  const [fiscais, setFiscais] = useState<Fiscal[]>([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [fiscalEmEdicao, setFiscalEmEdicao] = useState<Fiscal | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const { mostrarToast } = useToast();
  const { usuario } = useAuth();
  const ehAdministrador = usuario?.papel === "administrador";

  function carregar() {
    apiFiscais
      .listar(false)
      .then(setFiscais)
      .catch(() => setErro("Não foi possível carregar os fiscais."));
  }

  useEffect(carregar, []);

  async function criar(dados: { nome: string; matricula: string; cpf: string | null }) {
    await apiFiscais.criar(dados);
    setMostrarForm(false);
    carregar();
    mostrarToast("Fiscal cadastrado com sucesso.");
  }

  async function salvarEdicao(dados: { nome: string; matricula: string; cpf: string | null }) {
    if (!fiscalEmEdicao) return;
    await apiFiscais.atualizar(fiscalEmEdicao.id, dados);
    setFiscalEmEdicao(null);
    carregar();
    mostrarToast("Fiscal atualizado com sucesso.");
  }

  async function alternarAtivo(fiscal: Fiscal) {
    try {
      await apiFiscais.atualizar(fiscal.id, { ativo: !fiscal.ativo });
      carregar();
      mostrarToast(fiscal.ativo ? "Fiscal inativado." : "Fiscal reativado.");
    } catch (e) {
      mostrarToast(e instanceof ErroApi ? e.message : "Não foi possível alterar o status do fiscal.", "erro");
    }
  }

  async function excluir(fiscal: Fiscal) {
    if (!window.confirm(`Excluir "${fiscal.nome}" definitivamente? Essa ação não pode ser desfeita.`)) return;
    try {
      await apiFiscais.excluir(fiscal.id);
      carregar();
      mostrarToast("Fiscal excluído.");
    } catch (e) {
      mostrarToast(e instanceof ErroApi ? e.message : "Não foi possível excluir o fiscal.", "erro");
    }
  }

  return (
    <div className="min-h-screen bg-institucional-50 pb-16">
      <header className="flex items-center justify-between border-b border-institucional-100 bg-white px-6 py-4">
        <div>
          <Link to="/contratos" className="text-xs text-institucional-600 hover:underline">
            ← Contratos
          </Link>
          <h1 className="text-lg font-semibold text-institucional-900">Fiscais</h1>
        </div>
        <button
          onClick={() => {
            setFiscalEmEdicao(null);
            setMostrarForm((v) => !v);
          }}
          className="rounded bg-institucional-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-institucional-700"
        >
          {mostrarForm ? "Cancelar" : "+ Novo fiscal"}
        </button>
      </header>

      <main className="mx-auto max-w-3xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        {mostrarForm && <FormularioFiscal aoSalvar={criar} />}

        {fiscalEmEdicao && (
          <FormularioFiscal
            inicial={fiscalEmEdicao}
            aoSalvar={salvarEdicao}
            aoCancelar={() => setFiscalEmEdicao(null)}
          />
        )}

        <div className="overflow-hidden rounded-lg bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-institucional-100 text-left text-xs text-institucional-700">
              <tr>
                <th className="px-4 py-2">Nome</th>
                <th className="px-4 py-2">Matrícula</th>
                <th className="px-4 py-2">CPF</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {fiscais.map((f) => (
                <tr key={f.id} className="border-t border-institucional-100">
                  <td className="px-4 py-2 text-institucional-900">{f.nome}</td>
                  <td className="px-4 py-2 text-institucional-700">{mascararMatricula(f.matricula)}</td>
                  <td className="px-4 py-2 text-institucional-700">{f.cpf ? mascararCpf(f.cpf) : "—"}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs ${f.ativo ? "bg-green-100 text-green-800" : "bg-slate-200 text-slate-700"}`}
                    >
                      {f.ativo ? "Ativo" : "Inativo"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => {
                        setMostrarForm(false);
                        setFiscalEmEdicao(f);
                      }}
                      className="mr-2 rounded border border-institucional-300 px-2 py-1 text-xs text-institucional-700 hover:bg-institucional-100"
                    >
                      Editar
                    </button>
                    <button
                      onClick={() => alternarAtivo(f)}
                      className="mr-2 rounded border border-institucional-300 px-2 py-1 text-xs text-institucional-700 hover:bg-institucional-100"
                    >
                      {f.ativo ? "Inativar" : "Reativar"}
                    </button>
                    {ehAdministrador && (
                      <button
                        onClick={() => excluir(f)}
                        className="rounded border border-red-200 px-2 py-1 text-xs text-red-700 hover:bg-red-50"
                        title="Exclusão definitiva — restrita a administrador"
                      >
                        Excluir
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {fiscais.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-3 text-center text-institucional-500">
                    Nenhum fiscal cadastrado ainda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

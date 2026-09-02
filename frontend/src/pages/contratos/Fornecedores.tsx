import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiFornecedores } from "../../lib/apiContratos";
import { useAuth } from "../../lib/AuthContext";
import { mascararCnpj } from "../../lib/mascaras";
import type { Fornecedor } from "../../lib/tiposContratos";
import { useToast } from "../../lib/ToastContext";

const campoClasse =
  "w-full rounded border border-institucional-200 px-3 py-2 text-sm focus:border-institucional-500 focus:outline-none";

function FormularioFornecedor({
  inicial,
  aoSalvar,
  aoCancelar,
}: {
  inicial?: Fornecedor;
  aoSalvar: (dados: { razao_social: string; cnpj: string }) => Promise<void>;
  aoCancelar?: () => void;
}) {
  const [razaoSocial, setRazaoSocial] = useState(inicial?.razao_social ?? "");
  const [cnpj, setCnpj] = useState(inicial ? mascararCnpj(inicial.cnpj) : "");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await aoSalvar({ razao_social: razaoSocial, cnpj });
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar o fornecedor.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={aoEnviar} className="mb-6 space-y-3 rounded-lg bg-white p-5 shadow-sm">
      <div>
        <label className="mb-1 block text-xs text-institucional-700" htmlFor="fornecedor_razao_social">
          Razão social
        </label>
        <input
          id="fornecedor_razao_social"
          className={campoClasse}
          value={razaoSocial}
          onChange={(e) => setRazaoSocial(e.target.value)}
          required
        />
      </div>
      <div>
        <label className="mb-1 block text-xs text-institucional-700" htmlFor="fornecedor_cnpj">
          CNPJ (formato 00.000.000/0000-00)
        </label>
        <input
          id="fornecedor_cnpj"
          className={campoClasse}
          value={cnpj}
          onChange={(e) => setCnpj(mascararCnpj(e.target.value))}
          placeholder="00.000.000/0000-00"
          required
        />
        <p className="mt-1 text-xs text-institucional-500">
          Ao salvar, o CNPJ é conferido na Receita Federal — só é aceito se estiver com situação ativa.
        </p>
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

export function Fornecedores() {
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [fornecedorEmEdicao, setFornecedorEmEdicao] = useState<Fornecedor | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const { mostrarToast } = useToast();
  const { usuario } = useAuth();
  const ehAdministrador = usuario?.papel === "administrador";

  function carregar() {
    apiFornecedores.listar().then(setFornecedores).catch(() => setErro("Não foi possível carregar os fornecedores."));
  }

  useEffect(carregar, []);

  async function criar(dados: { razao_social: string; cnpj: string }) {
    await apiFornecedores.criar(dados);
    setMostrarForm(false);
    carregar();
    mostrarToast("Fornecedor cadastrado com sucesso.");
  }

  async function salvarEdicao(dados: { razao_social: string; cnpj: string }) {
    if (!fornecedorEmEdicao) return;
    await apiFornecedores.atualizar(fornecedorEmEdicao.id, dados);
    setFornecedorEmEdicao(null);
    carregar();
    mostrarToast("Fornecedor atualizado com sucesso.");
  }

  async function alternarAtivo(fornecedor: Fornecedor) {
    try {
      await apiFornecedores.atualizar(fornecedor.id, { ativo: !fornecedor.ativo });
      carregar();
      mostrarToast(fornecedor.ativo ? "Fornecedor inativado." : "Fornecedor reativado.");
    } catch (e) {
      mostrarToast(e instanceof ErroApi ? e.message : "Não foi possível alterar o status do fornecedor.", "erro");
    }
  }

  async function excluir(fornecedor: Fornecedor) {
    if (!window.confirm(`Excluir "${fornecedor.razao_social}" definitivamente? Essa ação não pode ser desfeita.`)) {
      return;
    }
    try {
      await apiFornecedores.excluir(fornecedor.id);
      carregar();
      mostrarToast("Fornecedor excluído.");
    } catch (e) {
      mostrarToast(e instanceof ErroApi ? e.message : "Não foi possível excluir o fornecedor.", "erro");
    }
  }

  return (
    <div className="min-h-screen bg-institucional-50 pb-16">
      <header className="flex items-center justify-between border-b border-institucional-100 bg-white px-6 py-4">
        <div>
          <Link to="/contratos" className="text-xs text-institucional-600 hover:underline">
            ← Contratos
          </Link>
          <h1 className="text-lg font-semibold text-institucional-900">Fornecedores</h1>
        </div>
        <button
          onClick={() => {
            setFornecedorEmEdicao(null);
            setMostrarForm((v) => !v);
          }}
          className="rounded bg-institucional-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-institucional-700"
        >
          {mostrarForm ? "Cancelar" : "+ Novo fornecedor"}
        </button>
      </header>

      <main className="mx-auto max-w-3xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        {mostrarForm && <FormularioFornecedor aoSalvar={criar} />}

        {fornecedorEmEdicao && (
          <FormularioFornecedor
            inicial={fornecedorEmEdicao}
            aoSalvar={salvarEdicao}
            aoCancelar={() => setFornecedorEmEdicao(null)}
          />
        )}

        <div className="overflow-hidden rounded-lg bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-institucional-100 text-left text-xs text-institucional-700">
              <tr>
                <th className="px-4 py-2">Razão social</th>
                <th className="px-4 py-2">CNPJ</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {fornecedores.map((f) => (
                <tr key={f.id} className="border-t border-institucional-100">
                  <td className="px-4 py-2 text-institucional-900">{f.razao_social}</td>
                  <td className="px-4 py-2 text-institucional-700">{mascararCnpj(f.cnpj)}</td>
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
                        setFornecedorEmEdicao(f);
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
              {fornecedores.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-3 text-center text-institucional-500">
                    Nenhum fornecedor cadastrado ainda.
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

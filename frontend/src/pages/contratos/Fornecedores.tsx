import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiFornecedores } from "../../lib/apiContratos";
import type { Fornecedor } from "../../lib/tiposContratos";

const campoClasse =
  "w-full rounded border border-institucional-200 px-3 py-2 text-sm focus:border-institucional-500 focus:outline-none";

export function Fornecedores() {
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [razaoSocial, setRazaoSocial] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  function carregar() {
    apiFornecedores.listar().then(setFornecedores).catch(() => setErro("Não foi possível carregar os fornecedores."));
  }

  useEffect(carregar, []);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await apiFornecedores.criar({ razao_social: razaoSocial, cnpj });
      setRazaoSocial("");
      setCnpj("");
      setMostrarForm(false);
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível cadastrar o fornecedor.");
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
          onClick={() => setMostrarForm((v) => !v)}
          className="rounded bg-institucional-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-institucional-700"
        >
          {mostrarForm ? "Cancelar" : "+ Novo fornecedor"}
        </button>
      </header>

      <main className="mx-auto max-w-3xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        {mostrarForm && (
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
                CNPJ
              </label>
              <input
                id="fornecedor_cnpj"
                className={campoClasse}
                value={cnpj}
                onChange={(e) => setCnpj(e.target.value)}
                required
              />
            </div>
            <button
              type="submit"
              className="rounded bg-institucional-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-institucional-700"
            >
              Cadastrar
            </button>
          </form>
        )}

        <div className="overflow-hidden rounded-lg bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-institucional-100 text-left text-xs text-institucional-700">
              <tr>
                <th className="px-4 py-2">Razão social</th>
                <th className="px-4 py-2">CNPJ</th>
              </tr>
            </thead>
            <tbody>
              {fornecedores.map((f) => (
                <tr key={f.id} className="border-t border-institucional-100">
                  <td className="px-4 py-2 text-institucional-900">{f.razao_social}</td>
                  <td className="px-4 py-2 text-institucional-700">{f.cnpj}</td>
                </tr>
              ))}
              {fornecedores.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-4 py-3 text-center text-institucional-500">
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

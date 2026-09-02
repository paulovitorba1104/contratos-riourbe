import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiFiscais } from "../../lib/apiContratos";
import type { Fiscal } from "../../lib/tiposContratos";

const campoClasse =
  "w-full rounded border border-institucional-200 px-3 py-2 text-sm focus:border-institucional-500 focus:outline-none";

export function Fiscais() {
  const [fiscais, setFiscais] = useState<Fiscal[]>([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [nome, setNome] = useState("");
  const [matricula, setMatricula] = useState("");
  const [cpf, setCpf] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  function carregar() {
    apiFiscais.listar().then(setFiscais).catch(() => setErro("Não foi possível carregar os fiscais."));
  }

  useEffect(carregar, []);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await apiFiscais.criar({ nome, matricula, cpf: cpf || null });
      setNome("");
      setMatricula("");
      setCpf("");
      setMostrarForm(false);
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível cadastrar o fiscal.");
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
          onClick={() => setMostrarForm((v) => !v)}
          className="rounded bg-institucional-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-institucional-700"
        >
          {mostrarForm ? "Cancelar" : "+ Novo fiscal"}
        </button>
      </header>

      <main className="mx-auto max-w-3xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        {mostrarForm && (
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
                Matrícula
              </label>
              <input
                id="fiscal_matricula"
                className={campoClasse}
                value={matricula}
                onChange={(e) => setMatricula(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-institucional-700" htmlFor="fiscal_cpf">
                CPF (opcional)
              </label>
              <input id="fiscal_cpf" className={campoClasse} value={cpf} onChange={(e) => setCpf(e.target.value)} />
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
                <th className="px-4 py-2">Nome</th>
                <th className="px-4 py-2">Matrícula</th>
                <th className="px-4 py-2">CPF</th>
              </tr>
            </thead>
            <tbody>
              {fiscais.map((f) => (
                <tr key={f.id} className="border-t border-institucional-100">
                  <td className="px-4 py-2 text-institucional-900">{f.nome}</td>
                  <td className="px-4 py-2 text-institucional-700">{f.matricula}</td>
                  <td className="px-4 py-2 text-institucional-700">{f.cpf ?? "—"}</td>
                </tr>
              ))}
              {fiscais.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-3 text-center text-institucional-500">
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

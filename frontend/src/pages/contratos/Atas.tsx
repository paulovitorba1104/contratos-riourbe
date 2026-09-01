import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiAtas } from "../../lib/apiContratos";
import type { AtaRegistroPreco } from "../../lib/tiposContratos";

const campoClasse =
  "w-full rounded border border-institucional-200 px-3 py-2 text-sm focus:border-institucional-500 focus:outline-none";

export function Atas() {
  const [atas, setAtas] = useState<AtaRegistroPreco[]>([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [orgao, setOrgao] = useState("");
  const [numeroAta, setNumeroAta] = useState("");
  const [objeto, setObjeto] = useState("");
  const [dataValidade, setDataValidade] = useState("");
  const [erro, setErro] = useState<string | null>(null);

  function carregar() {
    apiAtas.listar(true).then(setAtas).catch(() => setErro("Não foi possível carregar as atas."));
  }

  useEffect(carregar, []);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await apiAtas.criar({ orgao, numero_ata: numeroAta, objeto, data_validade: dataValidade });
      setOrgao("");
      setNumeroAta("");
      setObjeto("");
      setDataValidade("");
      setMostrarForm(false);
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível cadastrar a ata.");
    }
  }

  return (
    <div className="min-h-screen bg-institucional-50 pb-16">
      <header className="flex items-center justify-between border-b border-institucional-100 bg-white px-6 py-4">
        <div>
          <Link to="/contratos" className="text-xs text-institucional-600 hover:underline">
            ← Contratos
          </Link>
          <h1 className="text-lg font-semibold text-institucional-900">Atas de registro de preço</h1>
        </div>
        <button
          onClick={() => setMostrarForm((v) => !v)}
          className="rounded bg-institucional-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-institucional-700"
        >
          {mostrarForm ? "Cancelar" : "+ Nova ata"}
        </button>
      </header>

      <main className="mx-auto max-w-3xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        {mostrarForm && (
          <form onSubmit={aoEnviar} className="mb-6 space-y-3 rounded-lg bg-white p-5 shadow-sm">
            <input
              className={campoClasse}
              placeholder="Órgão"
              value={orgao}
              onChange={(e) => setOrgao(e.target.value)}
              required
            />
            <input
              className={campoClasse}
              placeholder="Número da ata"
              value={numeroAta}
              onChange={(e) => setNumeroAta(e.target.value)}
              required
            />
            <textarea
              className={campoClasse}
              placeholder="Objeto"
              rows={2}
              value={objeto}
              onChange={(e) => setObjeto(e.target.value)}
              required
            />
            <div>
              <label className="mb-1 block text-xs text-institucional-700">Validade</label>
              <input
                type="date"
                className={campoClasse}
                value={dataValidade}
                onChange={(e) => setDataValidade(e.target.value)}
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

        <div className="space-y-2">
          {atas.map((ata) => (
            <div key={ata.id} className="rounded-lg bg-white p-4 shadow-sm">
              <p className="font-medium text-institucional-900">
                {ata.orgao} — {ata.numero_ata}
              </p>
              <p className="text-sm text-institucional-700">{ata.objeto}</p>
              <p className="text-xs text-institucional-500">Válida até {ata.data_validade}</p>
            </div>
          ))}
          {atas.length === 0 && <p className="text-sm text-institucional-500">Nenhuma ata disponível para adesão.</p>}
        </div>
      </main>
    </div>
  );
}

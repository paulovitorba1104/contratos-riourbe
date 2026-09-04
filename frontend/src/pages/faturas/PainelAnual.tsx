import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { apiFaturas } from "../../lib/apiFaturas";
import type { LinhaPainelAnual, StatusFatura } from "../../lib/tiposFaturas";
import { MESES_CURTOS, ROTULOS_STATUS_FATURA } from "../../lib/tiposFaturas";

/** Cor de cada situação na matriz — a leitura de relance que a planilha dava
 * com o "X", agora dizendo também em que etapa a fatura do mês está. */
const CORES_CELULA: Record<StatusFatura, string> = {
  recebida: "bg-slate-200 text-slate-700",
  em_conferencia: "bg-amber-100 text-amber-800",
  conferida: "bg-sky-100 text-sky-800",
  atestada: "bg-institucional-100 text-institucional-800",
  paga: "bg-emerald-100 text-emerald-800",
  devolvida: "bg-red-100 text-red-800",
  cancelada: "bg-slate-100 text-slate-400 line-through",
};

const SIGLAS: Record<StatusFatura, string> = {
  recebida: "REC",
  em_conferencia: "CONF",
  conferida: "OK",
  atestada: "ATE",
  paga: "PG",
  devolvida: "DEV",
  cancelada: "CANC",
};

export function PainelAnual() {
  const [ano, setAno] = useState(new Date().getFullYear());
  const [linhas, setLinhas] = useState<LinhaPainelAnual[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [somenteComFatura, setSomenteComFatura] = useState(true);

  useEffect(() => {
    setLinhas(null);
    apiFaturas
      .painelAnual(ano)
      .then(setLinhas)
      .catch(() => setErro("Não foi possível carregar o painel anual."));
  }, [ano]);

  const visiveis = (linhas ?? []).filter(
    (l) => !somenteComFatura || l.meses.some((m) => m !== null),
  );

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <Link to="/faturas" className="text-xs font-medium text-institucional-600 hover:underline">
            ← Faturas
          </Link>
          <h1 className="page-title mt-0.5">Painel anual</h1>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => setAno((a) => a - 1)} className="btn-secondary btn-sm">
            ←
          </button>
          <span className="px-2 font-semibold tabular-nums text-slate-900">{ano}</span>
          <button onClick={() => setAno((a) => a + 1)} className="btn-secondary btn-sm">
            →
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-7xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}
        {!linhas && !erro && <p className="text-sm text-slate-500">Carregando...</p>}

        {linhas && (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={somenteComFatura}
                  onChange={(e) => setSomenteComFatura(e.target.checked)}
                />
                Mostrar só contratos com fatura em {ano}
              </label>
              <div className="flex flex-wrap gap-1.5">
                {(Object.keys(SIGLAS) as StatusFatura[]).map((s) => (
                  <span key={s} className={`rounded px-2 py-0.5 text-xs ${CORES_CELULA[s]}`}>
                    {SIGLAS[s]} · {ROTULOS_STATUS_FATURA[s]}
                  </span>
                ))}
              </div>
            </div>

            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 text-left text-xs text-slate-500">
                    <th className="sticky left-0 bg-slate-50 px-4 py-2">Contrato</th>
                    <th className="px-3 py-2">Fornecedor</th>
                    <th className="px-3 py-2 whitespace-nowrap">Fim da vigência</th>
                    {MESES_CURTOS.map((m) => (
                      <th key={m} className="px-2 py-2 text-center">
                        {m}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {visiveis.map((linha) => (
                    <tr key={linha.contrato_id} className="border-t border-slate-200">
                      <td className="sticky left-0 bg-white px-4 py-2 font-medium text-slate-900">
                        <Link
                          to={`/contratos/${linha.contrato_id}`}
                          className="hover:text-institucional-600 hover:underline"
                        >
                          {linha.contrato_numero}
                        </Link>
                      </td>
                      <td className="px-3 py-2 text-slate-600">{linha.fornecedor_nome}</td>
                      <td className="px-3 py-2 text-xs text-slate-500 tabular-nums">
                        {linha.vigencia_fim ?? "—"}
                      </td>
                      {linha.meses.map((mes, indice) => (
                        <td key={indice} className="px-1.5 py-2 text-center">
                          {mes ? (
                            <span
                              className={`inline-block min-w-[38px] rounded px-1.5 py-0.5 text-[11px] font-medium ${CORES_CELULA[mes]}`}
                              title={ROTULOS_STATUS_FATURA[mes]}
                            >
                              {SIGLAS[mes]}
                            </span>
                          ) : (
                            <span className="text-slate-300">·</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                  {visiveis.length === 0 && (
                    <tr>
                      <td colSpan={15} className="px-4 py-6 text-center text-sm text-slate-500">
                        Nenhuma fatura registrada em {ano}.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

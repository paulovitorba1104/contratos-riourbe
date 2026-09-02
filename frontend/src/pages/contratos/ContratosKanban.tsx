import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { BadgeAlerta } from "../../components/BadgeAlerta";
import { apiContratos } from "../../lib/apiContratos";
import type { Contrato, StatusContrato } from "../../lib/tiposContratos";
import { ROTULOS_FORMA_CONTRATACAO, ROTULOS_STATUS_CONTRATO } from "../../lib/tiposContratos";

const COLUNAS: StatusContrato[] = ["vigente", "suspenso", "encerrado"];

const CORES_COLUNA: Record<StatusContrato, string> = {
  vigente: "border-t-institucional-600",
  suspenso: "border-t-amber-500",
  encerrado: "border-t-slate-400",
};

function CartaoContrato({ contrato }: { contrato: Contrato }) {
  return (
    <Link
      to={`/contratos/${contrato.id}`}
      className="block rounded border border-institucional-100 bg-white p-3 text-sm shadow-sm transition hover:shadow-md"
    >
      <p className="font-semibold text-institucional-900">{contrato.numero_contrato}</p>
      <p className="mt-0.5 text-sm text-institucional-800">{contrato.tipo_servico}</p>
      <p className="mt-1 text-xs text-institucional-700">{contrato.processo_sei}</p>
      <p className="mt-1 text-xs text-institucional-600">
        {ROTULOS_FORMA_CONTRATACAO[contrato.forma_contratacao]}
      </p>
      <p className="mt-2 text-sm font-semibold text-institucional-800">
        R$ {Number(contrato.valor_inicial).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
      </p>
      {(contrato.alerta_vigencia || contrato.alerta_garantia) && (
        <div className="mt-2 flex flex-wrap gap-1">
          {contrato.alerta_vigencia && (
            <BadgeAlerta alerta={contrato.alerta_vigencia} rotuloOk="Vigência em dia" />
          )}
          {contrato.alerta_garantia && (
            <span title="Garantia">
              <BadgeAlerta alerta={contrato.alerta_garantia} rotuloOk="Garantia em dia" />
            </span>
          )}
        </div>
      )}
    </Link>
  );
}

export function ContratosKanban() {
  const [contratos, setContratos] = useState<Contrato[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    apiContratos
      .listar()
      .then(setContratos)
      .catch(() => setErro("Não foi possível carregar os contratos."));
  }, []);

  return (
    <div className="min-h-screen bg-institucional-50 pb-16">
      <header className="flex items-center justify-between border-b border-institucional-100 bg-white px-6 py-4">
        <div>
          <Link to="/" className="text-xs text-institucional-600 hover:underline">
            ← Hub
          </Link>
          <h1 className="text-lg font-semibold text-institucional-900">Contratos</h1>
        </div>
        <div className="flex gap-2">
          <Link
            to="/contratos/fiscais"
            className="rounded border border-institucional-300 px-3 py-1.5 text-sm text-institucional-700 hover:bg-institucional-100"
          >
            Fiscais
          </Link>
          <Link
            to="/contratos/fornecedores"
            className="rounded border border-institucional-300 px-3 py-1.5 text-sm text-institucional-700 hover:bg-institucional-100"
          >
            Fornecedores
          </Link>
          <Link
            to="/contratos/atas"
            className="rounded border border-institucional-300 px-3 py-1.5 text-sm text-institucional-700 hover:bg-institucional-100"
          >
            Atas para adesão
          </Link>
          <Link
            to="/contratos/novo"
            className="rounded bg-institucional-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-institucional-700"
          >
            + Novo contrato
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        {!contratos && !erro && <p className="text-sm text-institucional-700">Carregando...</p>}

        {contratos && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {COLUNAS.map((coluna) => {
              const contratosDaColuna = contratos.filter((c) => c.status === coluna);
              return (
                <div key={coluna} className={`rounded-lg border-t-4 bg-institucional-100/50 p-3 ${CORES_COLUNA[coluna]}`}>
                  <h2 className="mb-3 flex items-center justify-between text-sm font-semibold text-institucional-900">
                    {ROTULOS_STATUS_CONTRATO[coluna]}
                    <span className="rounded-full bg-white px-2 py-0.5 text-xs text-institucional-700">
                      {contratosDaColuna.length}
                    </span>
                  </h2>
                  <div className="space-y-2">
                    {contratosDaColuna.map((contrato) => (
                      <CartaoContrato key={contrato.id} contrato={contrato} />
                    ))}
                    {contratosDaColuna.length === 0 && (
                      <p className="text-xs text-institucional-500">Nenhum contrato aqui.</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

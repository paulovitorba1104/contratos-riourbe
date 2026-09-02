import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { BadgeAlerta } from "../../components/BadgeAlerta";
import { apiContratos } from "../../lib/apiContratos";
import type { Contrato, StatusContrato } from "../../lib/tiposContratos";
import { ROTULOS_FORMA_CONTRATACAO, ROTULOS_STATUS_CONTRATO } from "../../lib/tiposContratos";

const COLUNAS: StatusContrato[] = ["vigente", "suspenso", "encerrado"];

const CORES_COLUNA: Record<StatusContrato, string> = {
  vigente: "border-t-institucional-500",
  suspenso: "border-t-amber-400",
  encerrado: "border-t-slate-300",
};

function resumoProcesso(contrato: Contrato): string {
  const principal = contrato.processos.find((p) => p.tipo === "principal") ?? contrato.processos[0];
  if (!principal) return "sem processo";
  const apensos = contrato.processos.length - 1;
  return `${principal.numero_processo}${apensos > 0 ? ` +${apensos} apenso${apensos > 1 ? "s" : ""}` : ""}`;
}

function CartaoContrato({ contrato }: { contrato: Contrato }) {
  return (
    <Link
      to={`/contratos/${contrato.id}`}
      className="card card-hover block p-3.5 text-sm"
    >
      <p className="font-semibold text-slate-900">{contrato.numero_contrato}</p>
      <p className="mt-0.5 text-sm text-slate-600">{contrato.tipo_servico}</p>
      <p className="mt-1 text-xs text-slate-500">{resumoProcesso(contrato)}</p>
      <p className="mt-1 text-xs text-slate-400">
        {ROTULOS_FORMA_CONTRATACAO[contrato.forma_contratacao]}
      </p>
      <p className="mt-2 text-sm font-semibold text-slate-800">
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
    <div className="page-shell">
      <header className="page-header">
        <div>
          <Link to="/" className="text-xs font-medium text-institucional-600 hover:underline">
            ← Hub
          </Link>
          <h1 className="page-title mt-0.5">Contratos</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/contratos/fiscais" className="btn-secondary btn-sm">
            Fiscais
          </Link>
          <Link to="/contratos/fornecedores" className="btn-secondary btn-sm">
            Fornecedores
          </Link>
          <Link to="/contratos/atas" className="btn-secondary btn-sm">
            Atas para adesão
          </Link>
          <Link to="/contratos/novo" className="btn-primary btn-sm">
            + Novo contrato
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        {!contratos && !erro && <p className="text-sm text-slate-500">Carregando...</p>}

        {contratos && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {COLUNAS.map((coluna) => {
              const contratosDaColuna = contratos.filter((c) => c.status === coluna);
              return (
                <div key={coluna} className={`rounded-xl border-t-4 bg-slate-100/60 p-3 ${CORES_COLUNA[coluna]}`}>
                  <h2 className="mb-3 flex items-center justify-between text-sm font-semibold text-slate-800">
                    {ROTULOS_STATUS_CONTRATO[coluna]}
                    <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-500 shadow-sm">
                      {contratosDaColuna.length}
                    </span>
                  </h2>
                  <div className="space-y-2">
                    {contratosDaColuna.map((contrato) => (
                      <CartaoContrato key={contrato.id} contrato={contrato} />
                    ))}
                    {contratosDaColuna.length === 0 && (
                      <p className="text-xs text-slate-400">Nenhum contrato aqui.</p>
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

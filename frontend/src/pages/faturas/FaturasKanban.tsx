import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { apiFaturas } from "../../lib/apiFaturas";
import type { AlertaVencimento, Fatura, StatusFatura } from "../../lib/tiposFaturas";
import { ROTULOS_STATUS_FATURA } from "../../lib/tiposFaturas";

/** Colunas do fluxo normal. Devolvida e cancelada são saídas de exceção e
 * aparecem numa faixa à parte, para não poluir o acompanhamento do dia a dia. */
const COLUNAS: StatusFatura[] = ["recebida", "em_conferencia", "conferida", "atestada", "paga"];
const EXCECOES: StatusFatura[] = ["devolvida", "cancelada"];

const CORES_COLUNA: Record<StatusFatura, string> = {
  recebida: "border-t-slate-400",
  em_conferencia: "border-t-amber-400",
  conferida: "border-t-sky-400",
  atestada: "border-t-institucional-500",
  paga: "border-t-emerald-500",
  devolvida: "border-t-red-400",
  cancelada: "border-t-slate-300",
};

const CORES_ALERTA: Record<AlertaVencimento, string> = {
  vencido: "bg-red-100 text-red-800",
  "1_semana": "bg-orange-100 text-orange-800",
  "1_mes": "bg-amber-100 text-amber-800",
};

const ROTULOS_ALERTA: Record<AlertaVencimento, string> = {
  vencido: "Vencida",
  "1_semana": "Vence em 1 semana",
  "1_mes": "Vence em 1 mês",
};

export function formatarMoeda(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function competenciaLegivel(competencia: string): string {
  const [ano, mes] = competencia.split("-");
  const nomes = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
  ];
  return `${nomes[Number(mes) - 1]}/${ano}`;
}

function CartaoFatura({ fatura }: { fatura: Fatura }) {
  return (
    <Link to={`/faturas/${fatura.id}`} className="card card-hover block p-3.5 text-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold text-slate-900">NF {fatura.numero_nota_fiscal}</p>
        <span className="text-xs text-slate-400">{competenciaLegivel(fatura.competencia)}</span>
      </div>
      <p className="mt-0.5 text-sm text-slate-600">{fatura.fornecedor_nome}</p>
      <p className="mt-1 text-xs text-slate-500">Contrato {fatura.contrato_numero}</p>
      {fatura.numero_processo_sei && (
        <p className="mt-0.5 text-xs text-slate-400">{fatura.numero_processo_sei}</p>
      )}
      <p className="mt-2 text-sm font-semibold text-slate-800">{formatarMoeda(fatura.valor_bruto)}</p>
      {(fatura.alerta_vencimento || fatura.divergencia_tributaria) && (
        <div className="mt-2 flex flex-wrap gap-1">
          {fatura.alerta_vencimento && (
            <span
              className={`rounded-full px-2 py-0.5 text-xs ${CORES_ALERTA[fatura.alerta_vencimento]}`}
            >
              {ROTULOS_ALERTA[fatura.alerta_vencimento]}
            </span>
          )}
          {fatura.divergencia_tributaria && (
            <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-800">
              Divergência tributária
            </span>
          )}
        </div>
      )}
    </Link>
  );
}

function ResumoAlertas({ faturas }: { faturas: Fatura[] }) {
  const vencidas = faturas.filter((f) => f.alerta_vencimento === "vencido").length;
  const vencendo = faturas.filter((f) => f.alerta_vencimento === "1_semana").length;
  const divergentes = faturas.filter((f) => f.divergencia_tributaria).length;
  const emAberto = faturas.filter(
    (f) => !["paga", "devolvida", "cancelada"].includes(f.status),
  ).length;

  const chips = [
    emAberto > 0 && { texto: `${emAberto} em andamento`, cor: "bg-slate-200 text-slate-700" },
    vencidas > 0 && { texto: `${vencidas} vencida${vencidas > 1 ? "s" : ""}`, cor: "bg-red-100 text-red-800" },
    vencendo > 0 && { texto: `${vencendo} vencendo em 1 semana`, cor: "bg-orange-100 text-orange-800" },
    divergentes > 0 && {
      texto: `${divergentes} com divergência tributária`,
      cor: "bg-red-100 text-red-800",
    },
  ].filter((c): c is { texto: string; cor: string } => Boolean(c));

  if (chips.length === 0) return null;
  return (
    <div className="mb-4 flex flex-wrap gap-2">
      {chips.map((chip) => (
        <span key={chip.texto} className={`rounded-full px-3 py-1 text-xs font-medium ${chip.cor}`}>
          {chip.texto}
        </span>
      ))}
    </div>
  );
}

export function FaturasKanban() {
  const [faturas, setFaturas] = useState<Fatura[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [busca, setBusca] = useState("");

  useEffect(() => {
    apiFaturas
      .listar()
      .then(setFaturas)
      .catch(() => setErro("Não foi possível carregar as faturas."));
  }, []);

  const filtradas = useMemo(() => {
    if (!faturas) return null;
    const alvo = busca.trim().toLowerCase();
    if (!alvo) return faturas;
    return faturas.filter(
      (f) =>
        f.numero_nota_fiscal.toLowerCase().includes(alvo) ||
        f.fornecedor_nome.toLowerCase().includes(alvo) ||
        f.contrato_numero.toLowerCase().includes(alvo) ||
        (f.numero_processo_sei ?? "").toLowerCase().includes(alvo),
    );
  }, [faturas, busca]);

  const excecoes = (filtradas ?? []).filter((f) => EXCECOES.includes(f.status));

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <Link to="/" className="text-xs font-medium text-institucional-600 hover:underline">
            ← Hub
          </Link>
          <h1 className="page-title mt-0.5">Faturas</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/faturas/painel-anual" className="btn-secondary btn-sm">
            Painel anual
          </Link>
          <Link to="/faturas/medicoes" className="btn-secondary btn-sm">
            Medições
          </Link>
          <Link to="/faturas/configuracao" className="btn-secondary btn-sm">
            Configuração
          </Link>
          <Link to="/faturas/nova" className="btn-primary btn-sm">
            + Nova fatura
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-7xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}
        {!faturas && !erro && <p className="text-sm text-slate-500">Carregando...</p>}

        {faturas && (
          <>
            <ResumoAlertas faturas={faturas} />

            <div className="mb-4">
              <input
                type="text"
                placeholder="Buscar por nº da NF, fornecedor, contrato ou processo..."
                className="field-input max-w-md"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              {COLUNAS.map((coluna) => {
                const daColuna = (filtradas ?? []).filter((f) => f.status === coluna);
                return (
                  <div
                    key={coluna}
                    className={`rounded-xl border-t-4 bg-slate-100/60 p-3 ${CORES_COLUNA[coluna]}`}
                  >
                    <h2 className="mb-3 flex items-center justify-between text-sm font-semibold text-slate-800">
                      {ROTULOS_STATUS_FATURA[coluna]}
                      <span className="rounded-full bg-white px-2 py-0.5 text-xs text-slate-500 shadow-sm">
                        {daColuna.length}
                      </span>
                    </h2>
                    <div className="space-y-2">
                      {daColuna.map((f) => (
                        <CartaoFatura key={f.id} fatura={f} />
                      ))}
                      {daColuna.length === 0 && (
                        <p className="text-xs text-slate-400">Nenhuma fatura aqui.</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {excecoes.length > 0 && (
              <section className="mt-6">
                <h2 className="section-title mb-2">Fora do fluxo</h2>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 lg:grid-cols-5">
                  {excecoes.map((f) => (
                    <div key={f.id} className="opacity-75">
                      <CartaoFatura fatura={f} />
                      <p className="mt-1 px-1 text-xs text-slate-500">
                        {ROTULOS_STATUS_FATURA[f.status]}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}

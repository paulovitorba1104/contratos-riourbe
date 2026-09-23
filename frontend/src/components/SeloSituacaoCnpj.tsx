import { Loader2 } from "lucide-react";

import type { ConsultaCnpj } from "../lib/tiposContratos";

/** Selo com o resultado da consulta do CNPJ na Receita Federal — a mesma
 * consulta que o backend refaz (e de fato aplica) ao salvar; aqui é só
 * prévia visual, nunca bloqueia o preenchimento. */
export function SeloSituacaoCnpj({
  consulta,
  consultando,
}: {
  consulta: ConsultaCnpj | null;
  consultando: boolean;
}) {
  if (consultando) {
    return (
      <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
        <Loader2 className="h-3 w-3 animate-spin" /> Consultando CNPJ na Receita Federal...
      </p>
    );
  }
  if (consulta === null) return null;
  if (!consulta.encontrado) {
    return <p className="mt-1 text-xs text-slate-500">Não foi possível consultar agora — será conferido ao salvar.</p>;
  }
  return (
    <p className="mt-1 text-xs">
      <span
        className={
          consulta.ativo
            ? "pill bg-green-100 text-green-800"
            : "pill bg-red-100 text-red-800"
        }
      >
        Situação: {consulta.situacao_cadastral ?? "não informada"}
      </span>
    </p>
  );
}

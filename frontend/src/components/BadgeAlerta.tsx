import type { NivelAlerta } from "../lib/tiposContratos";

const CORES_ALERTA: Record<NivelAlerta, string> = {
  "6_meses": "bg-amber-100 text-amber-800",
  "3_meses": "bg-orange-100 text-orange-800",
  "1_meses": "bg-red-100 text-red-800",
  vencido: "bg-red-200 text-red-900",
};

const ROTULOS_ALERTA: Record<NivelAlerta, string> = {
  "6_meses": "Vence em até 6 meses",
  "3_meses": "Vence em até 3 meses",
  "1_meses": "Vence em até 1 mês",
  vencido: "Vencido",
};

export function BadgeAlerta({ alerta, rotuloOk = "Dentro do prazo" }: { alerta: NivelAlerta | null; rotuloOk?: string }) {
  if (!alerta) {
    return <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">{rotuloOk}</span>;
  }
  return <span className={`rounded-full px-2 py-0.5 text-xs ${CORES_ALERTA[alerta]}`}>{ROTULOS_ALERTA[alerta]}</span>;
}

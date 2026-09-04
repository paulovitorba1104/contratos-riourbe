import { requisicao } from "./api";
import type {
  ConferenciaPayload,
  EventoPayload,
  Fatura,
  FaturaAtualizarPayload,
  FaturaDetalhada,
  LinhaPainelAnual,
  Medicao,
  ModeloChecklist,
  ModeloChecklistPayload,
  NovaFaturaPayload,
  NovaMedicaoPayload,
  RegraTributaria,
  RegraTributariaPayload,
  RetencaoPayload,
  RetencaoSugerida,
  StatusFatura,
} from "./tiposFaturas";

function query(params: Record<string, string | undefined>): string {
  const partes = Object.entries(params)
    .filter(([, valor]) => valor !== undefined && valor !== "")
    .map(([chave, valor]) => `${chave}=${encodeURIComponent(valor as string)}`);
  return partes.length > 0 ? `?${partes.join("&")}` : "";
}

export const apiFaturas = {
  listar: (filtros: { contrato_id?: string; status_filtro?: StatusFatura; competencia?: string } = {}) =>
    requisicao<Fatura[]>(`/faturas${query(filtros)}`),
  obter: (id: string) => requisicao<FaturaDetalhada>(`/faturas/${id}`),
  criar: (dados: NovaFaturaPayload) =>
    requisicao<FaturaDetalhada>("/faturas", { method: "POST", body: JSON.stringify(dados) }),
  atualizar: (id: string, dados: FaturaAtualizarPayload) =>
    requisicao<FaturaDetalhada>(`/faturas/${id}`, { method: "PATCH", body: JSON.stringify(dados) }),
  excluir: (id: string) => requisicao<void>(`/faturas/${id}`, { method: "DELETE" }),

  atestar: (id: string, dados: EventoPayload) =>
    requisicao<FaturaDetalhada>(`/faturas/${id}/atesto`, { method: "POST", body: JSON.stringify(dados) }),
  registrarPagamento: (id: string, dados: EventoPayload) =>
    requisicao<FaturaDetalhada>(`/faturas/${id}/pagamento`, { method: "POST", body: JSON.stringify(dados) }),
  devolver: (id: string, dados: EventoPayload) =>
    requisicao<FaturaDetalhada>(`/faturas/${id}/devolucao`, { method: "POST", body: JSON.stringify(dados) }),
  cancelar: (id: string, dados: EventoPayload) =>
    requisicao<FaturaDetalhada>(`/faturas/${id}/cancelamento`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),

  registrarConferencia: (id: string, dados: ConferenciaPayload) =>
    requisicao<FaturaDetalhada>(`/faturas/${id}/conferencias`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),

  registrarGlosa: (id: string, dados: { valor: string; motivo: string }) =>
    requisicao<FaturaDetalhada>(`/faturas/${id}/glosas`, { method: "POST", body: JSON.stringify(dados) }),
  excluirGlosa: (id: string, glosaId: string) =>
    requisicao<FaturaDetalhada>(`/faturas/${id}/glosas/${glosaId}`, { method: "DELETE" }),

  sugerirRetencoes: (id: string) => requisicao<RetencaoSugerida[]>(`/faturas/${id}/retencoes/sugestao`),
  registrarRetencoes: (id: string, dados: RetencaoPayload[]) =>
    requisicao<FaturaDetalhada>(`/faturas/${id}/retencoes`, { method: "PUT", body: JSON.stringify(dados) }),

  painelAnual: (ano: number) => requisicao<LinhaPainelAnual[]>(`/faturas/painel-anual?ano=${ano}`),
};

export const apiMedicoes = {
  listar: (filtros: { contrato_id?: string; apenas_disponiveis?: boolean } = {}) =>
    requisicao<Medicao[]>(
      `/medicoes${query({
        contrato_id: filtros.contrato_id,
        apenas_disponiveis: filtros.apenas_disponiveis ? "true" : undefined,
      })}`,
    ),
  criar: (dados: NovaMedicaoPayload) =>
    requisicao<Medicao>("/medicoes", { method: "POST", body: JSON.stringify(dados) }),
  aprovar: (id: string) => requisicao<Medicao>(`/medicoes/${id}/aprovar`, { method: "POST" }),
  rejeitar: (id: string) => requisicao<Medicao>(`/medicoes/${id}/rejeitar`, { method: "POST" }),
  excluir: (id: string) => requisicao<void>(`/medicoes/${id}`, { method: "DELETE" }),
};

export const apiRegrasTributarias = {
  listar: () => requisicao<RegraTributaria[]>("/regras-tributarias"),
  criar: (dados: RegraTributariaPayload) =>
    requisicao<RegraTributaria>("/regras-tributarias", { method: "POST", body: JSON.stringify(dados) }),
  atualizar: (id: string, dados: Partial<RegraTributariaPayload> & { ativo?: boolean }) =>
    requisicao<RegraTributaria>(`/regras-tributarias/${id}`, {
      method: "PATCH",
      body: JSON.stringify(dados),
    }),
  excluir: (id: string) => requisicao<void>(`/regras-tributarias/${id}`, { method: "DELETE" }),
};

export const apiModelosChecklist = {
  listar: (apenasAtivos = true) =>
    requisicao<ModeloChecklist[]>(`/modelos-checklist?apenas_ativos=${apenasAtivos}`),
  criar: (dados: ModeloChecklistPayload) =>
    requisicao<ModeloChecklist>("/modelos-checklist", { method: "POST", body: JSON.stringify(dados) }),
  atualizar: (id: string, dados: Partial<ModeloChecklistPayload> & { ativo?: boolean }) =>
    requisicao<ModeloChecklist>(`/modelos-checklist/${id}`, {
      method: "PATCH",
      body: JSON.stringify(dados),
    }),
  excluir: (id: string) => requisicao<void>(`/modelos-checklist/${id}`, { method: "DELETE" }),
};

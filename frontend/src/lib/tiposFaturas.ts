export type StatusFatura =
  | "recebida"
  | "em_conferencia"
  | "conferida"
  | "atestada"
  | "paga"
  | "devolvida"
  | "cancelada";

export type StatusMedicao = "em_elaboracao" | "aprovada" | "rejeitada";
export type TipoEventoFatura =
  | "recebimento"
  | "conferencia"
  | "atesto"
  | "pagamento"
  | "devolucao"
  | "cancelamento";
export type Tributo = "irrf" | "inss" | "iss" | "pis" | "cofins" | "csll";
export type SituacaoItemConferencia = "conforme" | "nao_conforme" | "nao_aplicavel";
export type AlertaVencimento = "vencido" | "1_semana" | "1_mes";

export const ROTULOS_STATUS_FATURA: Record<StatusFatura, string> = {
  recebida: "Recebida",
  em_conferencia: "Em conferência",
  conferida: "Conferida",
  atestada: "Atestada",
  paga: "Paga",
  devolvida: "Devolvida",
  cancelada: "Cancelada",
};

export const ROTULOS_STATUS_MEDICAO: Record<StatusMedicao, string> = {
  em_elaboracao: "Em elaboração",
  aprovada: "Aprovada",
  rejeitada: "Rejeitada",
};

export const ROTULOS_TIPO_EVENTO: Record<TipoEventoFatura, string> = {
  recebimento: "Fatura recebida",
  conferencia: "Conferência registrada",
  atesto: "Atesto do fiscal",
  pagamento: "Pagamento registrado",
  devolucao: "Devolvida ao fornecedor",
  cancelamento: "Fatura cancelada",
};

export const ROTULOS_TRIBUTO: Record<Tributo, string> = {
  irrf: "IRRF",
  inss: "INSS",
  iss: "ISS",
  pis: "PIS",
  cofins: "COFINS",
  csll: "CSLL",
};

export const ROTULOS_SITUACAO_ITEM: Record<SituacaoItemConferencia, string> = {
  conforme: "Conforme",
  nao_conforme: "Não conforme",
  nao_aplicavel: "Não se aplica",
};

export const MESES_CURTOS = [
  "Jan",
  "Fev",
  "Mar",
  "Abr",
  "Mai",
  "Jun",
  "Jul",
  "Ago",
  "Set",
  "Out",
  "Nov",
  "Dez",
];

export interface Glosa {
  id: string;
  valor: string;
  motivo: string;
  registrado_por_nome: string;
  registrado_em: string;
}

export interface Retencao {
  id: string;
  tributo: Tributo;
  base_calculo: string;
  aliquota: string;
  valor_esperado: string;
  valor_informado: string;
  divergente: boolean;
  observacao: string | null;
}

export interface RetencaoSugerida {
  tributo: Tributo;
  descricao: string;
  base_legal: string | null;
  base_calculo: string;
  aliquota: string;
  valor_esperado: string;
}

export interface ItemConferencia {
  id: string;
  ordem: number;
  descricao: string;
  obrigatorio: boolean;
  situacao: SituacaoItemConferencia;
  observacao: string | null;
}

export interface Conferencia {
  id: string;
  modelo_checklist_id: string | null;
  conferido_por_nome: string;
  conferido_em: string;
  observacoes: string | null;
  itens: ItemConferencia[];
}

export interface EventoFatura {
  id: string;
  tipo: TipoEventoFatura;
  data_evento: string;
  responsavel_nome: string;
  observacoes: string | null;
}

export interface Fatura {
  id: string;
  contrato_id: string;
  contrato_numero: string;
  fornecedor_nome: string;
  medicao_id: string | null;
  numero_nota_fiscal: string;
  serie: string | null;
  numero_processo_sei: string | null;
  competencia: string;
  data_emissao: string;
  data_recebimento: string;
  data_vencimento: string | null;
  data_envio_gco: string | null;
  data_liquidacao: string | null;
  data_pagamento: string | null;
  valor_bruto: string;
  valor_glosas: string;
  valor_retencoes: string;
  valor_liquido: string;
  status: StatusFatura;
  observacoes: string | null;
  alerta_vencimento: AlertaVencimento | null;
  divergencia_tributaria: boolean;
}

export interface FaturaDetalhada extends Fatura {
  fatura_origem_id: string | null;
  glosas: Glosa[];
  retencoes: Retencao[];
  conferencias: Conferencia[];
  eventos: EventoFatura[];
}

export interface Medicao {
  id: string;
  contrato_id: string;
  numero_medicao: string;
  competencia: string;
  periodo_inicio: string;
  periodo_fim: string;
  valor_medido: string;
  status: StatusMedicao;
  aprovado_por_nome: string | null;
  aprovado_em: string | null;
  observacoes: string | null;
}

export interface LinhaPainelAnual {
  contrato_id: string;
  contrato_numero: string;
  fornecedor_nome: string;
  vigencia_fim: string | null;
  status_contrato: string;
  meses: (StatusFatura | null)[];
}

export interface RegraTributaria {
  id: string;
  tributo: Tributo;
  descricao: string;
  base_legal: string | null;
  aliquota: string;
  percentual_base: string;
  vigencia_inicio: string;
  vigencia_fim: string | null;
  ativo: boolean;
}

export interface ItemModeloChecklist {
  id: string;
  ordem: number;
  descricao: string;
  obrigatorio: boolean;
}

export interface ModeloChecklist {
  id: string;
  nome: string;
  descricao: string | null;
  ativo: boolean;
  itens: ItemModeloChecklist[];
}

export interface NovaFaturaPayload {
  contrato_id: string;
  medicao_id?: string | null;
  fatura_origem_id?: string | null;
  numero_nota_fiscal: string;
  serie?: string | null;
  numero_processo_sei?: string | null;
  competencia: string;
  data_emissao: string;
  data_recebimento: string;
  valor_bruto: string;
  data_vencimento?: string | null;
  observacoes?: string | null;
}

export interface FaturaAtualizarPayload {
  numero_nota_fiscal?: string;
  serie?: string | null;
  numero_processo_sei?: string | null;
  competencia?: string;
  data_emissao?: string;
  data_recebimento?: string;
  valor_bruto?: string;
  data_vencimento?: string | null;
  data_envio_gco?: string | null;
  data_liquidacao?: string | null;
  observacoes?: string | null;
}

export interface EventoPayload {
  data_evento: string;
  observacoes?: string | null;
}

export interface ItemConferenciaPayload {
  descricao: string;
  obrigatorio: boolean;
  situacao: SituacaoItemConferencia;
  observacao?: string | null;
  ordem: number;
}

export interface ConferenciaPayload {
  modelo_checklist_id?: string | null;
  itens: ItemConferenciaPayload[];
  observacoes?: string | null;
}

export interface RetencaoPayload {
  tributo: Tributo;
  valor_informado: string;
  observacao?: string | null;
}

export interface NovaMedicaoPayload {
  contrato_id: string;
  numero_medicao: string;
  competencia: string;
  periodo_inicio: string;
  periodo_fim: string;
  valor_medido: string;
  observacoes?: string | null;
}

export interface RegraTributariaPayload {
  tributo: Tributo;
  descricao: string;
  base_legal?: string | null;
  aliquota: string;
  percentual_base: string;
  vigencia_inicio: string;
  vigencia_fim?: string | null;
}

export interface ModeloChecklistPayload {
  nome: string;
  descricao?: string | null;
  itens: { descricao: string; obrigatorio: boolean; ordem: number }[];
}

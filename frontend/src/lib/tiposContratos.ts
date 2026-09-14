export type FormaContratacao = "pregao_eletronico" | "dispensa" | "inexigibilidade";
export type StatusContrato = "vigente" | "suspenso" | "encerrado";
export type TipoInstrumento =
  | "origem"
  | "prorrogacao"
  | "acrescimo_valor"
  | "supressao_valor"
  | "alteracao_qualitativa"
  | "reequilibrio"
  | "apostilamento"
  | "suspensao"
  | "rescisao_extincao";
export type SubStatusInstrumento = "elaboracao" | "parecer_juridico" | "assinatura" | "publicado";
export type FundamentacaoLei = "lei_13303_16" | "lei_14133_21";
export type NivelAlerta = "1_meses" | "3_meses" | "6_meses" | "vencido";
export type SistemaProcesso = "sicop" | "processo_rio" | "sei_rio";
export type TipoProcesso = "principal" | "apenso";
export type ExcecaoTetoVigencia = "art_71_i" | "art_71_ii";
export type TipoReajuste = "automatico" | "mediante_solicitacao";

export const ROTULOS_FORMA_CONTRATACAO: Record<FormaContratacao, string> = {
  pregao_eletronico: "Pregão Eletrônico",
  dispensa: "Dispensa",
  inexigibilidade: "Inexigibilidade",
};

export const ROTULOS_STATUS_CONTRATO: Record<StatusContrato, string> = {
  vigente: "Vigente",
  suspenso: "Suspenso",
  encerrado: "Encerrado",
};

export const ROTULOS_TIPO_INSTRUMENTO: Record<TipoInstrumento, string> = {
  origem: "Origem",
  prorrogacao: "Prorrogação",
  acrescimo_valor: "Acréscimo de valor",
  supressao_valor: "Supressão de valor",
  alteracao_qualitativa: "Alteração qualitativa",
  reequilibrio: "Reequilíbrio econômico-financeiro",
  apostilamento: "Apostilamento",
  suspensao: "Suspensão",
  rescisao_extincao: "Rescisão/Extinção",
};

export const ROTULOS_SUB_STATUS: Record<SubStatusInstrumento, string> = {
  elaboracao: "Elaboração",
  parecer_juridico: "Parecer jurídico",
  assinatura: "Assinatura",
  publicado: "Publicado",
};

export const ROTULOS_SISTEMA_PROCESSO: Record<SistemaProcesso, string> = {
  sicop: "SICOP (físico)",
  processo_rio: "Processo.Rio",
  sei_rio: "SEI.Rio",
};

export const ROTULOS_TIPO_PROCESSO: Record<TipoProcesso, string> = {
  principal: "Principal",
  apenso: "Apenso",
};

export const ROTULOS_EXCECAO_TETO: Record<ExcecaoTetoVigencia, string> = {
  art_71_i: "Art. 71, I — projeto do plano de negócios e investimentos",
  art_71_ii: "Art. 71, II — prazo maior é prática rotineira de mercado",
};

export const ROTULOS_TIPO_REAJUSTE: Record<TipoReajuste, string> = {
  automatico: "Obrigatório — reajusta assim que completa o prazo, sem precisar de pedido",
  mediante_solicitacao: "Só se a contratada pedir",
};

export const ROTULOS_ACAO_AUDITORIA: Record<string, string> = {
  criar_contrato: "Contrato criado",
  atualizar_contrato: "Dados do contrato atualizados",
  excluir_contrato: "Contrato excluído",
  adicionar_processo_contrato: "Processo adicionado",
  atualizar_processo_contrato: "Processo atualizado",
  excluir_processo_contrato: "Processo excluído",
  registrar_garantia_contrato: "Garantia registrada",
  atualizar_pagamento_contrato: "Valor pago atualizado",
  adicionar_fiscal_contrato: "Fiscal designado",
  encerrar_vinculo_fiscal: "Vínculo de fiscal encerrado",
  excluir_vinculo_fiscal: "Fiscal removido",
  criar_instrumento_processual: "Instrumento registrado",
  atualizar_sub_status_instrumento: "Sub-status do instrumento atualizado",
  excluir_instrumento_processual: "Instrumento excluído",
  anexar_arquivo_instrumento: "Arquivo anexado",
  excluir_anexo_instrumento: "Anexo excluído",
};

export const TIPOS_QUE_DEFINEM_VIGENCIA: TipoInstrumento[] = ["origem", "prorrogacao"];

export interface Fornecedor {
  id: string;
  razao_social: string;
  cnpj: string;
  ativo: boolean;
}

export interface Fiscal {
  id: string;
  nome: string;
  matricula: string;
  cpf: string | null;
  ativo: boolean;
}

export interface FiscalVinculo {
  id: string;
  fiscal_id: string;
  nome: string;
  matricula: string;
  data_inicio: string;
  data_fim: string | null;
}

export interface ModeloRipm {
  id: string;
  codigo: string;
  nome: string;
  itens_checklist: string[] | null;
  ativo: boolean;
}

export interface AtaRegistroPreco {
  id: string;
  orgao: string;
  numero_ata: string;
  objeto: string;
  data_validade: string;
  disponivel_para_adesao: boolean;
  observacoes: string | null;
}

export interface AnexoInstrumento {
  id: string;
  nome_arquivo: string;
  tipo_mime: string;
  tamanho_bytes: number;
  enviado_por_nome: string;
  enviado_em: string;
}

export interface InstrumentoProcessual {
  id: string;
  contrato_id: string;
  tipo: TipoInstrumento;
  modelo_ripm_id: string | null;
  fundamentacao_lei: FundamentacaoLei;
  fundamentacao_artigo: string;
  sub_status: SubStatusInstrumento;
  numero_documento_sei: string | null;
  data_inicio_vigencia: string | null;
  data_fim_vigencia: string | null;
  valor_delta: string | null;
  // Preenchidos só quando o apostilamento é de reajuste.
  reajuste_indice_nome: string | null;
  reajuste_indice_atual: string | null;
  reajuste_indice_base: string | null;
  reajuste_valor_mensal_antigo: string | null;
  reajuste_valor_mensal_novo: string | null;
  reajuste_data_inicio: string | null;
  reajuste_data_fim: string | null;
  observacoes: string | null;
  anexos: AnexoInstrumento[];
}

export interface Processo {
  id: string;
  numero_processo: string;
  sistema_origem: SistemaProcesso;
  tipo: TipoProcesso;
  criado_em: string;
}

export interface Contrato {
  id: string;
  numero_contrato: string;
  tipo_servico: string;
  objeto: string;
  fornecedor_id: string;
  forma_contratacao: FormaContratacao;
  status: StatusContrato;
  data_assinatura_original: string;
  valor_inicial: string;
  valor_pago: string;
  nota_reserva: string | null;
  nota_empenho: string | null;
  pt: string | null;
  nd: string | null;
  fr: string | null;
  tipo_patrimonial: string | null;
  item_patrimonial: string | null;
  codigo_ccon: string | null;
  observacoes: string | null;
  processos: Processo[];
  alerta_vigencia: NivelAlerta | null;
  alerta_garantia: NivelAlerta | null;
  alerta_reajuste: NivelAlerta | null;
  // Nem todo contrato é faturado pela GCT (benefícios são faturados pelo RH,
  // jurídicos pela AJU, por exemplo). Falso bloqueia fatura no módulo de
  // Faturamento — a GCT só gerencia prazo e renovação desse contrato.
  faturamento_gerido_pela_gct: boolean;
  setor_responsavel_faturamento: string | null;
}

export interface LogAuditoria {
  id: string;
  acao: string;
  usuario_nome: string | null;
  detalhes: Record<string, unknown> | null;
  criado_em: string;
}

export interface TempoRestante {
  vencido: boolean;
  dias_totais: number;
  meses: number;
  dias: number;
}

export interface CalculoVigencia {
  data_inicio: string;
  meses: number;
  data_fim: string;
  teto_cinco_anos: string | null;
  excede_teto: boolean;
}

export interface LinhaReajuste {
  competencia: string;
  valor_antigo: string;
  valor_reajustado: string;
  diferenca: string;
}

export interface CalculoReajuste {
  valor_mensal_antigo: string;
  valor_mensal_novo: string;
  percentual_variacao: string;
  linhas: LinhaReajuste[];
  valor_total_apostilamento: string;
}

export interface GarantiaHistorico {
  id: string;
  data_inicio_garantia: string | null;
  data_fim_garantia: string | null;
  observacao: string | null;
  registrado_por_nome: string;
  registrado_em: string;
}

export interface ContratoDetalhado extends Contrato {
  fiscais: FiscalVinculo[];
  valor_atualizado: string;
  saldo_a_pagar: string;
  // Parte manual do valor pago (histórico anterior à entrada no sistema, ou
  // total de contrato cujo faturamento é de outro setor) — a tela de edição
  // pré-carrega o ajuste a partir daqui, não de valor_pago (que já soma as
  // faturas pagas no sistema).
  valor_pago_anterior_sistema: string;
  vigencia_inicio: string | null;
  vigencia_fim: string | null;
  // Nulo quando o contrato tem exceção registrada — a lei remove o teto
  // nesses casos, não impõe um novo (art. 71, I ou II, da Lei 13.303/16).
  teto_vigencia: string | null;
  excecao_teto_vigencia: ExcecaoTetoVigencia | null;
  excecao_teto_justificativa: string | null;
  excecao_teto_documento_sei: string | null;
  tempo_restante_vigencia: TempoRestante | null;
  garantia_inicio: string | null;
  garantia_fim: string | null;
  garantias: GarantiaHistorico[];
  // Reajuste — nulo quando o contrato não tem cláusula de reajuste.
  tipo_reajuste: TipoReajuste | null;
  periodicidade_reajuste_meses: number | null;
  indice_reajuste_padrao: string | null;
  proximo_marco_reajuste: string | null;
  instrumentos: InstrumentoProcessual[];
}

export interface InstrumentoOrigemPayload {
  modelo_ripm_id?: string | null;
  fundamentacao_lei: FundamentacaoLei;
  fundamentacao_artigo: string;
  numero_documento_sei?: string | null;
  data_inicio_vigencia: string;
  data_fim_vigencia: string;
}

export interface ProcessoPayload {
  numero_processo: string;
  sistema_origem: SistemaProcesso;
  tipo: TipoProcesso;
}

export interface NovoContratoPayload {
  numero_contrato: string;
  tipo_servico: string;
  objeto: string;
  fornecedor_id: string;
  forma_contratacao: FormaContratacao;
  data_assinatura_original: string;
  valor_inicial: string;
  observacoes?: string | null;
  instrumento_origem: InstrumentoOrigemPayload;
  processos: ProcessoPayload[];
  fiscais_ids: string[];
  excecao_teto_vigencia?: ExcecaoTetoVigencia | null;
  excecao_teto_justificativa?: string | null;
  excecao_teto_documento_sei?: string | null;
  faturamento_gerido_pela_gct?: boolean;
  setor_responsavel_faturamento?: string | null;
  // Contrato antigo entrando no sistema agora: total já pago lançado de uma
  // vez, sem fatura por fatura. Fica 0 (padrão do backend) em contrato novo.
  valor_pago_anterior_sistema?: string;
  // Reajuste — nulo quando o contrato não tem cláusula de reajuste.
  tipo_reajuste?: TipoReajuste | null;
  periodicidade_reajuste_meses?: number | null;
  indice_reajuste_padrao?: string | null;
}

export interface ContratoAtualizarPayload {
  numero_contrato?: string;
  tipo_servico?: string;
  objeto?: string;
  fornecedor_id?: string;
  forma_contratacao?: FormaContratacao;
  data_assinatura_original?: string;
  valor_inicial?: string;
  // valor_pago não é editável aqui — sempre calculado. Ajuste pelo endpoint
  // dedicado (apiContratos.atualizarPagamento).
  nota_reserva?: string | null;
  nota_empenho?: string | null;
  pt?: string | null;
  nd?: string | null;
  fr?: string | null;
  tipo_patrimonial?: string | null;
  item_patrimonial?: string | null;
  codigo_ccon?: string | null;
  observacoes?: string | null;
  excecao_teto_vigencia?: ExcecaoTetoVigencia | null;
  excecao_teto_justificativa?: string | null;
  excecao_teto_documento_sei?: string | null;
  faturamento_gerido_pela_gct?: boolean;
  setor_responsavel_faturamento?: string | null;
  tipo_reajuste?: TipoReajuste | null;
  periodicidade_reajuste_meses?: number | null;
  indice_reajuste_padrao?: string | null;
}

export interface NovoInstrumentoPayload {
  tipo: TipoInstrumento;
  modelo_ripm_id?: string | null;
  fundamentacao_lei: FundamentacaoLei;
  fundamentacao_artigo: string;
  numero_documento_sei?: string | null;
  data_inicio_vigencia?: string | null;
  data_fim_vigencia?: string | null;
  valor_delta?: string | null;
  // Reajuste (só para tipo="apostilamento") — os 6 vêm juntos ou nenhum; o
  // backend calcula reajuste_valor_mensal_novo e valor_delta sozinho.
  reajuste_indice_nome?: string | null;
  reajuste_indice_atual?: string | null;
  reajuste_indice_base?: string | null;
  reajuste_valor_mensal_antigo?: string | null;
  reajuste_data_inicio?: string | null;
  reajuste_data_fim?: string | null;
  observacoes?: string | null;
}

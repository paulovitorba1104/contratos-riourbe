import { requisicao } from "./api";
import type {
  AtaRegistroPreco,
  Contrato,
  ContratoAtualizarPayload,
  ContratoDetalhado,
  Fiscal,
  Fornecedor,
  ModeloRipm,
  NovoContratoPayload,
  NovoInstrumentoPayload,
  StatusContrato,
  SubStatusInstrumento,
} from "./tiposContratos";

export const apiContratos = {
  listar: (statusFiltro?: StatusContrato) =>
    requisicao<Contrato[]>(`/contratos${statusFiltro ? `?status_filtro=${statusFiltro}` : ""}`),
  obter: (id: string) => requisicao<ContratoDetalhado>(`/contratos/${id}`),
  criar: (dados: NovoContratoPayload) =>
    requisicao<ContratoDetalhado>("/contratos", { method: "POST", body: JSON.stringify(dados) }),
  atualizar: (id: string, dados: ContratoAtualizarPayload) =>
    requisicao<ContratoDetalhado>(`/contratos/${id}`, { method: "PATCH", body: JSON.stringify(dados) }),
  excluir: (id: string) => requisicao<void>(`/contratos/${id}`, { method: "DELETE" }),
  registrarGarantia: (
    id: string,
    dados: { data_inicio_garantia: string | null; data_fim_garantia: string | null; observacao?: string | null },
  ) =>
    requisicao<ContratoDetalhado>(`/contratos/${id}/garantia`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),
  atualizarPagamento: (id: string, valor_pago: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${id}/pagamento`, {
      method: "PATCH",
      body: JSON.stringify({ valor_pago }),
    }),
  adicionarFiscal: (contratoId: string, fiscal_id: string, data_inicio: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/fiscais`, {
      method: "POST",
      body: JSON.stringify({ fiscal_id, data_inicio }),
    }),
  encerrarVinculoFiscal: (contratoId: string, vinculoId: string, data_fim: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/fiscais/${vinculoId}/encerrar`, {
      method: "PATCH",
      body: JSON.stringify({ data_fim }),
    }),
  excluirVinculoFiscal: (contratoId: string, vinculoId: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/fiscais/${vinculoId}`, { method: "DELETE" }),
  criarInstrumento: (contratoId: string, dados: NovoInstrumentoPayload) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/instrumentos`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),
  atualizarSubStatusInstrumento: (contratoId: string, instrumentoId: string, sub_status: SubStatusInstrumento) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/instrumentos/${instrumentoId}/sub-status`, {
      method: "PATCH",
      body: JSON.stringify({ sub_status }),
    }),
  excluirInstrumento: (contratoId: string, instrumentoId: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/instrumentos/${instrumentoId}`, { method: "DELETE" }),
};

export const apiFornecedores = {
  listar: () => requisicao<Fornecedor[]>("/fornecedores"),
  criar: (dados: { razao_social: string; cnpj: string }) =>
    requisicao<Fornecedor>("/fornecedores", { method: "POST", body: JSON.stringify(dados) }),
  atualizar: (id: string, dados: { razao_social?: string; cnpj?: string; ativo?: boolean }) =>
    requisicao<Fornecedor>(`/fornecedores/${id}`, { method: "PATCH", body: JSON.stringify(dados) }),
  excluir: (id: string) => requisicao<void>(`/fornecedores/${id}`, { method: "DELETE" }),
};

export const apiFiscais = {
  listar: (apenasAtivos = true) => requisicao<Fiscal[]>(`/fiscais?apenas_ativos=${apenasAtivos}`),
  criar: (dados: { nome: string; matricula: string; cpf?: string | null }) =>
    requisicao<Fiscal>("/fiscais", { method: "POST", body: JSON.stringify(dados) }),
  atualizar: (id: string, dados: { nome?: string; matricula?: string; cpf?: string | null; ativo?: boolean }) =>
    requisicao<Fiscal>(`/fiscais/${id}`, { method: "PATCH", body: JSON.stringify(dados) }),
  excluir: (id: string) => requisicao<void>(`/fiscais/${id}`, { method: "DELETE" }),
};

export const apiModelosRipm = {
  listar: () => requisicao<ModeloRipm[]>("/modelos-ripm"),
};

export const apiAtas = {
  listar: (apenasDisponiveis = true) =>
    requisicao<AtaRegistroPreco[]>(`/atas-registro-preco?apenas_disponiveis=${apenasDisponiveis}`),
  criar: (dados: {
    orgao: string;
    numero_ata: string;
    objeto: string;
    data_validade: string;
    observacoes?: string | null;
  }) => requisicao<AtaRegistroPreco>("/atas-registro-preco", { method: "POST", body: JSON.stringify(dados) }),
  excluir: (id: string) => requisicao<void>(`/atas-registro-preco/${id}`, { method: "DELETE" }),
};

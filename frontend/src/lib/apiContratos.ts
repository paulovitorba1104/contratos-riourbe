import { requisicao } from "./api";
import type {
  AtaRegistroPreco,
  Contrato,
  ContratoDetalhado,
  Fornecedor,
  ModeloRipm,
  NovoContratoPayload,
  NovoInstrumentoPayload,
  StatusContrato,
  SubStatusInstrumento,
  UsuarioBasico,
} from "./tiposContratos";

export const apiContratos = {
  listar: (statusFiltro?: StatusContrato) =>
    requisicao<Contrato[]>(`/contratos${statusFiltro ? `?status_filtro=${statusFiltro}` : ""}`),
  obter: (id: string) => requisicao<ContratoDetalhado>(`/contratos/${id}`),
  criar: (dados: NovoContratoPayload) =>
    requisicao<ContratoDetalhado>("/contratos", { method: "POST", body: JSON.stringify(dados) }),
  atualizarGarantia: (id: string, dados: { data_inicio_garantia: string | null; data_fim_garantia: string | null }) =>
    requisicao<ContratoDetalhado>(`/contratos/${id}/garantia`, {
      method: "PATCH",
      body: JSON.stringify(dados),
    }),
  atualizarPagamento: (id: string, valor_pago: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${id}/pagamento`, {
      method: "PATCH",
      body: JSON.stringify({ valor_pago }),
    }),
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
};

export const apiFornecedores = {
  listar: () => requisicao<Fornecedor[]>("/fornecedores"),
  criar: (dados: { razao_social: string; cnpj: string }) =>
    requisicao<Fornecedor>("/fornecedores", { method: "POST", body: JSON.stringify(dados) }),
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
};

export const apiUsuariosBasico = {
  listar: () => requisicao<UsuarioBasico[]>("/usuarios/basico"),
};

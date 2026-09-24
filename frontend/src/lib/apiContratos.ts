import { requisicao, requisicaoComArquivo } from "./api";
import type {
  AtaRegistroPreco,
  CalculoReajuste,
  CalculoValorMensal,
  CalculoVigencia,
  ConsultaCnpj,
  ConsultaIndice,
  Contrato,
  ContratoAtualizarPayload,
  ContratoDetalhado,
  ExcecaoTetoVigencia,
  ExecucaoPayload,
  Fiscal,
  FornecedorAdicionalPayload,
  Fornecedor,
  GarantiaPayload,
  InstrumentoDatasPayload,
  LogAuditoria,
  ModeloRipm,
  NovoContratoPayload,
  NovoInstrumentoPayload,
  ProcessoPayload,
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
  registrarGarantia: (id: string, dados: GarantiaPayload) =>
    requisicao<ContratoDetalhado>(`/contratos/${id}/garantia`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),
  /** Ajusta só a parte manual do valor pago (histórico anterior à entrada no
   * sistema, ou total de um contrato cujo faturamento é de outro setor) — o
   * backend soma isso ao que as faturas pagas no sistema já cobrem, nunca
   * substitui. */
  atualizarPagamento: (id: string, valor_pago_anterior_sistema: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${id}/pagamento`, {
      method: "PATCH",
      body: JSON.stringify({ valor_pago_anterior_sistema }),
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
  /** Data de formalização/assinatura e data de publicação (ex.: Diário
   * Oficial) do instrumento — independentes do sub-status, preenchidas
   * quando ficam conhecidas (geralmente depois da criação). */
  atualizarDatasInstrumento: (contratoId: string, instrumentoId: string, dados: InstrumentoDatasPayload) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/instrumentos/${instrumentoId}/datas`, {
      method: "PATCH",
      body: JSON.stringify(dados),
    }),
  excluirInstrumento: (contratoId: string, instrumentoId: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/instrumentos/${instrumentoId}`, { method: "DELETE" }),
  adicionarProcesso: (contratoId: string, dados: ProcessoPayload) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/processos`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),
  atualizarProcesso: (contratoId: string, processoId: string, dados: Partial<ProcessoPayload>) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/processos/${processoId}`, {
      method: "PATCH",
      body: JSON.stringify(dados),
    }),
  excluirProcesso: (contratoId: string, processoId: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/processos/${processoId}`, { method: "DELETE" }),
  auditoria: (contratoId: string) => requisicao<LogAuditoria[]>(`/contratos/${contratoId}/auditoria`),
  /** Contador de datas: início + prazo em meses = fim da vigência. O cálculo
   * fica no backend para não divergir do que é validado ao salvar. Com
   * excecaoTeto informado, não há teto de 5 anos a calcular (art. 71, I ou
   * II, da Lei 13.303/16 — ex.: locação de imóvel). */
  calcularVigencia: (
    dataInicio: string,
    meses: number,
    dataAssinatura?: string,
    excecaoTeto?: ExcecaoTetoVigencia | null,
  ) =>
    requisicao<CalculoVigencia>(
      `/contratos/calcular-vigencia?data_inicio=${dataInicio}&meses=${meses}` +
        (dataAssinatura ? `&data_assinatura=${dataAssinatura}` : "") +
        (excecaoTeto ? `&excecao_teto_vigencia=${excecaoTeto}` : ""),
    ),
  /** Calculadora de reajuste/apostilamento — substitui a calculadora do
   * cidadão para a parte de conta. `dataInicio` é o marco do reajuste (ex.:
   * aniversário da vigência); `dataFim` é o próximo marco ou o fim da
   * vigência do contrato, o que vier primeiro. */
  calcularReajuste: (
    valorMensalAntigo: string,
    indiceAtual: string,
    indiceBase: string,
    dataInicio: string,
    dataFim: string,
  ) =>
    requisicao<CalculoReajuste>(
      `/contratos/calcular-reajuste?valor_mensal_antigo=${valorMensalAntigo}` +
        `&indice_atual=${indiceAtual}&indice_base=${indiceBase}` +
        `&data_inicio=${dataInicio}&data_fim=${dataFim}`,
    ),
  /** Busca o IPCA-E direto no Banco Central (SGS, dados do IBGE) seguindo a
   * cláusula-padrão de reajuste (R = Po×[(I-Io)/Io]): Io é o índice do mês
   * anterior à apresentação da proposta (aqui, a data de assinatura do
   * contrato) e I é o índice do mês anterior ao aniversário sendo
   * reajustado — nunca o índice do próprio mês de referência. Prévia de
   * melhor esforço, nunca bloqueia: se falhar, os campos continuam
   * editáveis à mão. */
  consultarIndiceIpcaE: (dataApresentacaoProposta: string, dataAniversario: string) =>
    requisicao<ConsultaIndice>(
      `/contratos/consultar-indice-ipca-e?data_apresentacao_proposta=${dataApresentacaoProposta}` +
        `&data_aniversario=${dataAniversario}`,
    ),
  /** Registra uma execução do serviço (contrato controlado por quantidade —
   * ex.: limpeza de carpete). Cada aplicação é uma linha nova, nunca
   * editada depois. */
  registrarExecucao: (contratoId: string, dados: ExecucaoPayload) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/execucoes`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),
  excluirExecucao: (contratoId: string, execucaoId: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/execucoes/${execucaoId}`, { method: "DELETE" }),
  /** Calculadora de valor global a partir da mensalidade (ex.: locação de
   * imóvel) — pré-visualiza o valor a lançar antes de criar/editar o
   * contrato; o backend recalcula de novo ao salvar. */
  calcularValorMensal: (valorMensal: string, prazoMeses: number, carenciaMeses: number) =>
    requisicao<CalculoValorMensal>(
      `/contratos/calcular-valor-mensal?valor_mensal=${valorMensal}` +
        `&prazo_meses=${prazoMeses}&carencia_meses=${carenciaMeses}`,
    ),
  /** Vincula mais um fornecedor ao contrato, além do principal — caso da
   * locação de imóvel em que uma empresa recebe o aluguel e outra
   * administra o condomínio. */
  adicionarFornecedor: (contratoId: string, dados: FornecedorAdicionalPayload) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/fornecedores`, {
      method: "POST",
      body: JSON.stringify(dados),
    }),
  excluirFornecedor: (contratoId: string, vinculoId: string) =>
    requisicao<ContratoDetalhado>(`/contratos/${contratoId}/fornecedores/${vinculoId}`, { method: "DELETE" }),
  anexarArquivo: (contratoId: string, instrumentoId: string, arquivo: File) => {
    const formData = new FormData();
    formData.append("arquivo", arquivo);
    return requisicaoComArquivo<ContratoDetalhado>(
      `/contratos/${contratoId}/instrumentos/${instrumentoId}/anexos`,
      formData,
    );
  },
};

/** URL de download/visualização de um anexo — usar direto num link (a
 * sessão vai junto via cookie, não precisa de token na URL). */
export function urlAnexo(anexoId: string): string {
  return `/api/anexos/${anexoId}`;
}

/** URL do PDF "Distribuição do Apostilamento" de um instrumento de
 * reajuste — mesmo padrão de urlAnexo, usar direto num link. */
export function urlDistribuicaoReajustePdf(contratoId: string, instrumentoId: string): string {
  return `/api/contratos/${contratoId}/instrumentos/${instrumentoId}/distribuicao-reajuste.pdf`;
}

export const apiAnexos = {
  excluir: (anexoId: string) => requisicao<void>(`/anexos/${anexoId}`, { method: "DELETE" }),
};

export const apiFornecedores = {
  listar: () => requisicao<Fornecedor[]>("/fornecedores"),
  criar: (dados: { razao_social: string; cnpj: string }) =>
    requisicao<Fornecedor>("/fornecedores", { method: "POST", body: JSON.stringify(dados) }),
  atualizar: (id: string, dados: { razao_social?: string; cnpj?: string; ativo?: boolean }) =>
    requisicao<Fornecedor>(`/fornecedores/${id}`, { method: "PATCH", body: JSON.stringify(dados) }),
  excluir: (id: string) => requisicao<void>(`/fornecedores/${id}`, { method: "DELETE" }),
  /** Prévia ao vivo na Receita Federal (via BrasilAPI) enquanto o CNPJ é
   * digitado — autopreenche a razão social e mostra a situação cadastral
   * antes de salvar. `cnpjDigitos` são só os 14 dígitos, sem máscara. */
  consultarCnpj: (cnpjDigitos: string) => requisicao<ConsultaCnpj>(`/fornecedores/consulta-cnpj/${cnpjDigitos}`),
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

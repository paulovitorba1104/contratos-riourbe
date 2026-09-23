import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { SeloSituacaoCnpj } from "../../components/SeloSituacaoCnpj";
import { apiContratos, apiFiscais, apiFornecedores } from "../../lib/apiContratos";
import { ErroApi } from "../../lib/api";
import {
  formatarMoedaInicial,
  mascararCnpj,
  mascararCpf,
  mascararMatricula,
  mascararMoeda,
  moedaParaNumero,
} from "../../lib/mascaras";
import { useConsultaCnpj } from "../../lib/useConsultaCnpj";
import type {
  CalculoValorMensal,
  ExcecaoTetoVigencia,
  Fiscal,
  Fornecedor,
  FormaContratacao,
  ModoExecucao,
  ModoValorContrato,
  ProcessoPayload,
  SistemaProcesso,
  TipoProcesso,
  TipoReajuste,
} from "../../lib/tiposContratos";
import {
  ROTULOS_EXCECAO_TETO,
  ROTULOS_FORMA_CONTRATACAO,
  ROTULOS_MODO_EXECUCAO,
  ROTULOS_MODO_VALOR,
  ROTULOS_SISTEMA_PROCESSO,
  ROTULOS_TIPO_PROCESSO,
  ROTULOS_TIPO_REAJUSTE,
} from "../../lib/tiposContratos";
import { useToast } from "../../lib/ToastContext";

const campoClasse = "field-input";
const rotuloClasse = "field-label";

export function NovoContrato() {
  const navegar = useNavigate();
  const { mostrarToast } = useToast();

  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [mostrarNovoFornecedor, setMostrarNovoFornecedor] = useState(false);
  const [novoFornecedorNome, setNovoFornecedorNome] = useState("");
  const [novoFornecedorCnpj, setNovoFornecedorCnpj] = useState("");
  const { consulta: consultaNovoFornecedorCnpj, consultando: consultandoNovoFornecedorCnpj } =
    useConsultaCnpj(novoFornecedorCnpj);

  // Autopreenche a razão social a partir da Receita Federal — só quando o
  // campo ainda está vazio, nunca sobrescreve o que a pessoa já digitou.
  useEffect(() => {
    if (consultaNovoFornecedorCnpj?.encontrado && consultaNovoFornecedorCnpj.razao_social && !novoFornecedorNome.trim()) {
      setNovoFornecedorNome(consultaNovoFornecedorCnpj.razao_social);
    }
  }, [consultaNovoFornecedorCnpj]);

  const [fiscais, setFiscais] = useState<Fiscal[]>([]);
  const [mostrarNovoFiscal, setMostrarNovoFiscal] = useState(false);
  const [novoFiscalNome, setNovoFiscalNome] = useState("");
  const [novoFiscalMatricula, setNovoFiscalMatricula] = useState("");
  const [novoFiscalCpf, setNovoFiscalCpf] = useState("");

  const [numeroContrato, setNumeroContrato] = useState("");
  const [processos, setProcessos] = useState<ProcessoPayload[]>([
    { numero_processo: "", sistema_origem: "sei_rio", tipo: "principal" },
  ]);
  const [tipoServico, setTipoServico] = useState("");
  const [objeto, setObjeto] = useState("");
  const [fornecedorId, setFornecedorId] = useState("");
  const [formaContratacao, setFormaContratacao] = useState<FormaContratacao>("pregao_eletronico");
  const [dataAssinatura, setDataAssinatura] = useState("");
  const [valorInicial, setValorInicial] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [fiscaisSelecionados, setFiscaisSelecionados] = useState<string[]>([]);

  const [fundamentacao, setFundamentacao] = useState("");
  const [numeroDocumentoSei, setNumeroDocumentoSei] = useState("");
  const [dataInicioVigencia, setDataInicioVigencia] = useState("");
  const [dataFimVigencia, setDataFimVigencia] = useState("");
  const [prazoMeses, setPrazoMeses] = useState("");
  const [calculandoVigencia, setCalculandoVigencia] = useState(false);
  const [avisoTeto, setAvisoTeto] = useState<string | null>(null);

  // Exceção ao teto de 5 anos (art. 71, I ou II, da Lei 13.303/16) — nula na
  // imensa maioria dos contratos; marcada, exige justificativa e o documento
  // (parecer jurídico/SEI) que a formaliza. Ex.: locação de imóvel, cujo
  // prazo longo é prática rotineira de mercado (inciso II).
  const [temExcecaoTeto, setTemExcecaoTeto] = useState(false);
  const [excecaoTeto, setExcecaoTeto] = useState<ExcecaoTetoVigencia>("art_71_ii");
  const [excecaoJustificativa, setExcecaoJustificativa] = useState("");
  const [excecaoDocumentoSei, setExcecaoDocumentoSei] = useState("");

  // Nem todo contrato é faturado pela GCT (benefícios pelo RH, jurídicos pela
  // AJU, por exemplo) — desmarcado, o contrato não entra no módulo de
  // Faturamento, a GCT só gerencia prazo e renovação dele.
  const [faturamentoPelaGct, setFaturamentoPelaGct] = useState(true);
  const [setorResponsavelFaturamento, setSetorResponsavelFaturamento] = useState("");

  // A maioria dos contratos exige garantia contratual — alguns não (ex.:
  // valor baixo dispensado pela lei). Desmarcado, o card de garantia sai
  // da urgência de alerta na ficha e no Kanban.
  const [exigeGarantia, setExigeGarantia] = useState(true);

  // Contrato antigo entrando no sistema agora: total já pago até hoje,
  // lançado de uma vez — não vale a pena lançar fatura por fatura do
  // histórico. Fica 0,00 (padrão) em contrato genuinamente novo.
  const [valorPagoAnteriorSistema, setValorPagoAnteriorSistema] = useState("");

  // Reajuste — nulo (padrão) quando o contrato não tem cláusula de
  // reajuste (ex.: compra pontual, licença sem previsão de correção).
  const [temClausulaReajuste, setTemClausulaReajuste] = useState(false);
  const [tipoReajuste, setTipoReajuste] = useState<TipoReajuste>("automatico");
  const [periodicidadeReajusteMeses, setPeriodicidadeReajusteMeses] = useState("24");
  const [indiceReajustePadrao, setIndiceReajustePadrao] = useState("IPCA-E");

  // Controle por quantidade de execuções — dispensa sazonal cujo termo de
  // referência prevê a quantidade de vezes que o serviço será aplicado
  // dentro do exercício (ex.: limpeza de carpete, 3x/ano), em vez de um
  // prazo em dias. A vigência abaixo continua sendo informada (ainda limita
  // o exercício), só não é mais o critério de conclusão do contrato.
  const [modoExecucao, setModoExecucao] = useState<ModoExecucao>("por_vigencia");
  const [quantidadeExecucoesPrevistas, setQuantidadeExecucoesPrevistas] = useState("");

  // Valor global (padrão, digitado direto) ou por mensalidade — caso da
  // locação de imóvel, em que o valor global do contrato é calculado a
  // partir do aluguel mensal, do prazo (já informado na vigência abaixo) e
  // da carência (meses de aluguel gratuito no início, se houver).
  const [modoValor, setModoValor] = useState<ModoValorContrato>("global");
  const [valorMensal, setValorMensal] = useState("");
  const [carenciaMeses, setCarenciaMeses] = useState("0");
  const [previaValorGlobal, setPreviaValorGlobal] = useState<CalculoValorMensal | null>(null);

  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    apiFornecedores.listar().then(setFornecedores).catch(() => setErro("Não foi possível carregar fornecedores."));
    apiFiscais.listar().then(setFiscais).catch(() => setErro("Não foi possível carregar fiscais."));
  }, []);

  /** Contador de datas: início + prazo em meses = fim da vigência. O cálculo
   * roda no backend para não divergir do que é validado ao salvar (mês de 30/31
   * dias, fevereiro, ano bissexto) e já avisa se o prazo estoura os 5 anos. */
  useEffect(() => {
    const meses = Number(prazoMeses);
    if (!dataInicioVigencia || !Number.isInteger(meses) || meses < 1 || meses > 1200) {
      setAvisoTeto(null);
      return;
    }

    let cancelado = false;
    setCalculandoVigencia(true);
    apiContratos
      .calcularVigencia(
        dataInicioVigencia,
        meses,
        dataAssinatura || undefined,
        temExcecaoTeto ? excecaoTeto : null,
      )
      .then((calculo) => {
        if (cancelado) return;
        setDataFimVigencia(calculo.data_fim);
        setAvisoTeto(
          calculo.excede_teto
            ? `Esse prazo leva a vigência até ${calculo.data_fim}, ultrapassando o teto de 5 anos ` +
              `da Lei 13.303/16 (limite: ${calculo.teto_cinco_anos}).`
            : null,
        );
      })
      .catch(() => {
        if (!cancelado) setAvisoTeto(null);
      })
      .finally(() => {
        if (!cancelado) setCalculandoVigencia(false);
      });

    return () => {
      cancelado = true;
    };
  }, [dataInicioVigencia, prazoMeses, dataAssinatura, temExcecaoTeto, excecaoTeto]);

  /** Prévia ao vivo do valor global a partir da mensalidade — mesmo cálculo
   * que o backend refaz de verdade ao salvar. Usa o prazo já digitado na
   * vigência acima, sem pedir de novo. */
  useEffect(() => {
    const meses = Number(prazoMeses);
    const carencia = Number(carenciaMeses || "0");
    if (
      modoValor !== "mensal" ||
      !valorMensal.trim() ||
      !Number.isInteger(meses) ||
      meses < 1 ||
      !Number.isInteger(carencia) ||
      carencia < 0
    ) {
      setPreviaValorGlobal(null);
      return;
    }

    let cancelado = false;
    apiContratos
      .calcularValorMensal(moedaParaNumero(valorMensal), meses, carencia)
      .then((calculo) => {
        if (!cancelado) setPreviaValorGlobal(calculo);
      })
      .catch(() => {
        if (!cancelado) setPreviaValorGlobal(null);
      });

    return () => {
      cancelado = true;
    };
  }, [modoValor, valorMensal, carenciaMeses, prazoMeses]);

  async function criarFornecedor() {
    setErro(null);
    try {
      const fornecedor = await apiFornecedores.criar({
        razao_social: novoFornecedorNome,
        cnpj: novoFornecedorCnpj,
      });
      setFornecedores((atual) => [...atual, fornecedor]);
      setFornecedorId(fornecedor.id);
      setMostrarNovoFornecedor(false);
      setNovoFornecedorNome("");
      setNovoFornecedorCnpj("");
      mostrarToast("Fornecedor cadastrado com sucesso.");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível cadastrar o fornecedor.");
    }
  }

  async function criarFiscal() {
    setErro(null);
    try {
      const fiscal = await apiFiscais.criar({
        nome: novoFiscalNome,
        matricula: novoFiscalMatricula,
        cpf: novoFiscalCpf || null,
      });
      setFiscais((atual) => [...atual, fiscal]);
      setFiscaisSelecionados((atual) => [...atual, fiscal.id]);
      setMostrarNovoFiscal(false);
      setNovoFiscalNome("");
      setNovoFiscalMatricula("");
      setNovoFiscalCpf("");
      mostrarToast("Fiscal cadastrado com sucesso.");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível cadastrar o fiscal.");
    }
  }

  function alternarFiscal(id: string) {
    setFiscaisSelecionados((atual) =>
      atual.includes(id) ? atual.filter((f) => f !== id) : [...atual, id],
    );
  }

  function adicionarProcesso() {
    setProcessos((atual) => [...atual, { numero_processo: "", sistema_origem: "sei_rio", tipo: "apenso" }]);
  }

  function removerProcesso(indice: number) {
    setProcessos((atual) => atual.filter((_, i) => i !== indice));
  }

  function atualizarProcesso(indice: number, alteracoes: Partial<ProcessoPayload>) {
    setProcessos((atual) => atual.map((p, i) => (i === indice ? { ...p, ...alteracoes } : p)));
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);

    if (!fornecedorId) {
      setErro("Selecione um fornecedor.");
      return;
    }
    if (fiscaisSelecionados.length === 0) {
      setErro("Selecione ao menos um fiscal do contrato.");
      return;
    }
    if (processos.some((p) => !p.numero_processo.trim())) {
      setErro("Preencha o número de todos os processos ou remova as linhas vazias.");
      return;
    }
    if (temExcecaoTeto && (!excecaoJustificativa.trim() || !excecaoDocumentoSei.trim())) {
      setErro("A exceção ao teto de 5 anos exige justificativa e o número do documento (parecer jurídico/SEI).");
      return;
    }
    if (!faturamentoPelaGct && !setorResponsavelFaturamento.trim()) {
      setErro("Informe o setor responsável pelo faturamento quando ele não é feito pela Gerência de Contratos.");
      return;
    }
    if (temClausulaReajuste && !periodicidadeReajusteMeses.trim()) {
      setErro("Informe a periodicidade do reajuste (em meses).");
      return;
    }
    if (modoExecucao === "por_quantidade" && !quantidadeExecucoesPrevistas.trim()) {
      setErro("Informe a quantidade de execuções previstas.");
      return;
    }
    if (modoValor === "mensal" && !valorMensal.trim()) {
      setErro("Informe o valor mensal do contrato.");
      return;
    }
    if (modoValor === "global" && !valorInicial.trim()) {
      setErro("Informe o valor inicial do contrato.");
      return;
    }
    setEnviando(true);
    try {
      const contrato = await apiContratos.criar({
        numero_contrato: numeroContrato,
        tipo_servico: tipoServico,
        objeto,
        fornecedor_id: fornecedorId,
        forma_contratacao: formaContratacao,
        data_assinatura_original: dataAssinatura,
        ...(modoValor === "mensal"
          ? {
              modo_valor: modoValor,
              valor_mensal: moedaParaNumero(valorMensal),
              carencia_meses: Number(carenciaMeses || "0"),
            }
          : { valor_inicial: moedaParaNumero(valorInicial) }),
        observacoes: observacoes || null,
        instrumento_origem: {
          fundamentacao,
          numero_documento_sei: numeroDocumentoSei || null,
          data_inicio_vigencia: dataInicioVigencia,
          data_fim_vigencia: dataFimVigencia,
        },
        processos,
        fiscais_ids: fiscaisSelecionados,
        faturamento_gerido_pela_gct: faturamentoPelaGct,
        setor_responsavel_faturamento: faturamentoPelaGct ? null : setorResponsavelFaturamento,
        exige_garantia: exigeGarantia,
        valor_pago_anterior_sistema: valorPagoAnteriorSistema
          ? moedaParaNumero(valorPagoAnteriorSistema)
          : undefined,
        ...(temExcecaoTeto
          ? {
              excecao_teto_vigencia: excecaoTeto,
              excecao_teto_justificativa: excecaoJustificativa,
              excecao_teto_documento_sei: excecaoDocumentoSei,
            }
          : {}),
        ...(temClausulaReajuste
          ? {
              tipo_reajuste: tipoReajuste,
              periodicidade_reajuste_meses: Number(periodicidadeReajusteMeses),
              indice_reajuste_padrao: indiceReajustePadrao || null,
            }
          : {}),
        ...(modoExecucao === "por_quantidade"
          ? { modo_execucao: modoExecucao, quantidade_execucoes_previstas: Number(quantidadeExecucoesPrevistas) }
          : {}),
      });
      mostrarToast("Contrato criado com sucesso.");
      navegar(`/contratos/${contrato.id}`);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível criar o contrato.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <Link to="/contratos" className="text-xs font-medium text-institucional-600 hover:underline">
            ← Contratos
          </Link>
          <h1 className="page-title mt-0.5">Novo contrato</h1>
        </div>
      </header>

      <main className="mx-auto max-w-2xl p-6">
        <form onSubmit={aoEnviar} className="card space-y-5 p-6">
          <div>
            <label className={rotuloClasse} htmlFor="numero_contrato">
              Número do contrato
            </label>
            <input
              id="numero_contrato"
              className={campoClasse}
              value={numeroContrato}
              onChange={(e) => setNumeroContrato(e.target.value)}
              required
            />
          </div>

          <div>
            <div className="mb-1 flex items-center justify-between">
              <span className={rotuloClasse}>Número(s) de processo *</span>
              <button type="button" onClick={adicionarProcesso} className="btn-ghost btn-sm">
                + Adicionar processo
              </button>
            </div>
            <p className="mb-3 text-xs text-slate-500">
              Um contrato pode ter mais de um número (SICOP físico, Processo.Rio, SEI.Rio) e/ou
              processos apensos ao principal.
            </p>
            <div className="space-y-2">
              {processos.map((processo, indice) => (
                <div
                  key={indice}
                  className="grid grid-cols-[2fr_1.3fr_1fr_auto] items-end gap-2 rounded-lg border border-slate-200 bg-slate-50/60 p-2.5"
                >
                  <div>
                    {indice === 0 && <label className="mb-1 block text-xs text-slate-500">Número</label>}
                    <input
                      id={indice === 0 ? "numero_processo_0" : undefined}
                      className={campoClasse}
                      value={processo.numero_processo}
                      onChange={(e) => atualizarProcesso(indice, { numero_processo: e.target.value })}
                      placeholder="ex.: SEI-04/000123/2026"
                      required
                    />
                  </div>
                  <div>
                    {indice === 0 && <label className="mb-1 block text-xs text-slate-500">Sistema</label>}
                    <select
                      className={campoClasse}
                      value={processo.sistema_origem}
                      onChange={(e) =>
                        atualizarProcesso(indice, { sistema_origem: e.target.value as SistemaProcesso })
                      }
                    >
                      {Object.entries(ROTULOS_SISTEMA_PROCESSO).map(([valor, rotulo]) => (
                        <option key={valor} value={valor}>
                          {rotulo}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    {indice === 0 && <label className="mb-1 block text-xs text-slate-500">Tipo</label>}
                    <select
                      className={campoClasse}
                      value={processo.tipo}
                      onChange={(e) => atualizarProcesso(indice, { tipo: e.target.value as TipoProcesso })}
                    >
                      {Object.entries(ROTULOS_TIPO_PROCESSO).map(([valor, rotulo]) => (
                        <option key={valor} value={valor}>
                          {rotulo}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={() => removerProcesso(indice)}
                    disabled={processos.length === 1}
                    className="btn-secondary btn-sm"
                    title={processos.length === 1 ? "O contrato precisa ter ao menos um processo" : "Remover"}
                  >
                    Remover
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className={rotuloClasse} htmlFor="tipo_servico">
              Tipo de serviço
            </label>
            <input
              id="tipo_servico"
              className={campoClasse}
              value={tipoServico}
              onChange={(e) => setTipoServico(e.target.value)}
              required
            />
          </div>

          <div>
            <label className={rotuloClasse} htmlFor="objeto">
              Objeto
            </label>
            <textarea
              id="objeto"
              className={campoClasse}
              rows={3}
              value={objeto}
              onChange={(e) => setObjeto(e.target.value)}
              required
            />
          </div>

          <div>
            <label className={rotuloClasse} htmlFor="fornecedor">
              Fornecedor
            </label>
            <div className="flex gap-2">
              <select
                id="fornecedor"
                className={campoClasse}
                value={fornecedorId}
                onChange={(e) => setFornecedorId(e.target.value)}
                required
              >
                <option value="">Selecione...</option>
                {fornecedores.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.razao_social}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setMostrarNovoFornecedor((v) => !v)}
                className="btn-secondary"
              >
                + Novo
              </button>
            </div>

            {mostrarNovoFornecedor && (
              <div className="mt-2 space-y-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
                <input
                  placeholder="Razão social"
                  className={campoClasse}
                  value={novoFornecedorNome}
                  onChange={(e) => setNovoFornecedorNome(e.target.value)}
                />
                <input
                  placeholder="00.000.000/0000-00"
                  className={campoClasse}
                  value={novoFornecedorCnpj}
                  onChange={(e) => setNovoFornecedorCnpj(mascararCnpj(e.target.value))}
                />
                <SeloSituacaoCnpj consulta={consultaNovoFornecedorCnpj} consultando={consultandoNovoFornecedorCnpj} />
                <button type="button" onClick={criarFornecedor} className="btn-primary btn-sm">
                  Cadastrar fornecedor
                </button>
              </div>
            )}
          </div>

          <div>
            <label className={rotuloClasse} htmlFor="forma_contratacao">
              Forma de contratação
            </label>
            <select
              id="forma_contratacao"
              className={campoClasse}
              value={formaContratacao}
              onChange={(e) => setFormaContratacao(e.target.value as FormaContratacao)}
            >
              {Object.entries(ROTULOS_FORMA_CONTRATACAO).map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className={rotuloClasse} htmlFor="modo_execucao">
              Modo de execução
            </label>
            <select
              id="modo_execucao"
              className={campoClasse}
              value={modoExecucao}
              onChange={(e) => setModoExecucao(e.target.value as ModoExecucao)}
            >
              {Object.entries(ROTULOS_MODO_EXECUCAO).map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Use "por quantidade" para dispensa sazonal cujo termo de referência prevê um número
              de aplicações no exercício (ex.: limpeza de carpete, 3x/ano) — a vigência abaixo
              continua sendo informada normalmente, ela só deixa de ser o critério de conclusão do
              contrato.
            </p>
            {modoExecucao === "por_quantidade" && (
              <div className="mt-2">
                <label className={rotuloClasse} htmlFor="quantidade_execucoes_previstas">
                  Quantidade de execuções previstas
                </label>
                <input
                  id="quantidade_execucoes_previstas"
                  type="number"
                  min={1}
                  max={1000}
                  className={campoClasse}
                  value={quantidadeExecucoesPrevistas}
                  onChange={(e) => setQuantidadeExecucoesPrevistas(e.target.value)}
                  placeholder="ex.: 3"
                />
              </div>
            )}
          </div>

          <div>
            <label className={rotuloClasse} htmlFor="modo_valor">
              Modo do valor
            </label>
            <select
              id="modo_valor"
              className={campoClasse}
              value={modoValor}
              onChange={(e) => setModoValor(e.target.value as ModoValorContrato)}
            >
              {Object.entries(ROTULOS_MODO_VALOR).map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">
              Use "por mensalidade" para contrato cotado por aluguel mensal (ex.: locação de
              imóvel) — o valor global é calculado a partir da mensalidade, do prazo informado na
              vigência acima e da carência, se houver.
            </p>
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                id="faturamento_gerido_pela_gct"
                type="checkbox"
                checked={faturamentoPelaGct}
                onChange={(e) => setFaturamentoPelaGct(e.target.checked)}
              />
              O faturamento deste contrato é feito pela Gerência de Contratos
            </label>
            <p className="mt-1 text-xs text-slate-500">
              Desmarque para contrato cujo faturamento é de outro setor (ex.: benefícios pelo RH,
              jurídicos pela AJU) — aqui a GCT só gerencia prazo e renovação; o contrato não entra
              no módulo de Faturamento.
            </p>
            {!faturamentoPelaGct && (
              <div className="mt-2">
                <label className={rotuloClasse} htmlFor="setor_responsavel_faturamento">
                  Setor responsável pelo faturamento
                </label>
                <input
                  id="setor_responsavel_faturamento"
                  className={campoClasse}
                  value={setorResponsavelFaturamento}
                  onChange={(e) => setSetorResponsavelFaturamento(e.target.value)}
                  placeholder="ex.: RH, AJU"
                />
              </div>
            )}
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                id="exige_garantia"
                type="checkbox"
                checked={exigeGarantia}
                onChange={(e) => setExigeGarantia(e.target.checked)}
              />
              Este contrato exige garantia contratual
            </label>
            <p className="mt-1 text-xs text-slate-500">
              Desmarque para contrato dispensado de garantia (ex.: valor baixo dispensado pela
              lei) — o card de garantia deixa de entrar na urgência de alerta na ficha e no
              Kanban.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={rotuloClasse} htmlFor="data_assinatura">
                {modoExecucao === "por_quantidade"
                  ? "Data de publicação no Diário Oficial"
                  : "Data de assinatura original"}
              </label>
              <input
                id="data_assinatura"
                type="date"
                className={campoClasse}
                value={dataAssinatura}
                onChange={(e) => setDataAssinatura(e.target.value)}
                required
              />
              {modoExecucao === "por_quantidade" && (
                <p className="mt-1 text-xs text-slate-500">
                  Contrato sem assinatura formal (dispensa sazonal) — a referência é a publicação
                  no D.O.
                </p>
              )}
            </div>
            {modoValor === "global" ? (
              <div>
                <label className={rotuloClasse} htmlFor="valor_inicial">
                  Valor inicial (R$)
                </label>
                <input
                  id="valor_inicial"
                  type="text"
                  inputMode="numeric"
                  placeholder="0,00"
                  className={campoClasse}
                  value={valorInicial}
                  onChange={(e) => setValorInicial(mascararMoeda(e.target.value))}
                  required
                />
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={rotuloClasse} htmlFor="valor_mensal">
                    Valor mensal (R$)
                  </label>
                  <input
                    id="valor_mensal"
                    type="text"
                    inputMode="numeric"
                    placeholder="0,00"
                    className={campoClasse}
                    value={valorMensal}
                    onChange={(e) => setValorMensal(mascararMoeda(e.target.value))}
                    required
                  />
                </div>
                <div>
                  <label className={rotuloClasse} htmlFor="carencia_meses">
                    Carência (meses)
                  </label>
                  <input
                    id="carencia_meses"
                    type="number"
                    min={0}
                    max={120}
                    className={campoClasse}
                    value={carenciaMeses}
                    onChange={(e) => setCarenciaMeses(e.target.value)}
                    placeholder="0"
                  />
                </div>
              </div>
            )}
          </div>

          {modoValor === "mensal" && (
            <div className="rounded-lg border border-institucional-200 bg-institucional-50 p-4 text-sm">
              {previaValorGlobal ? (
                <>
                  <p className="font-medium text-institucional-900">
                    Valor global calculado: R$ {formatarMoedaInicial(previaValorGlobal.valor_global)}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {previaValorGlobal.meses_cobrados} meses cobrados de{" "}
                    {previaValorGlobal.prazo_meses} meses de prazo
                    {previaValorGlobal.carencia_meses > 0
                      ? ` (${previaValorGlobal.carencia_meses} de carência)`
                      : ""}
                    .
                  </p>
                </>
              ) : (
                <p className="text-xs text-slate-500">
                  Informe o valor mensal e o prazo da vigência (acima) para ver o valor global
                  calculado.
                </p>
              )}
            </div>
          )}

          <div>
            <label className={rotuloClasse} htmlFor="valor_pago_anterior_sistema">
              Valor já pago (opcional)
            </label>
            <input
              id="valor_pago_anterior_sistema"
              type="text"
              inputMode="numeric"
              placeholder="0,00"
              className={campoClasse}
              value={valorPagoAnteriorSistema}
              onChange={(e) => setValorPagoAnteriorSistema(mascararMoeda(e.target.value))}
            />
            <p className="field-hint">
              Só para contrato que já vem de antes deste sistema: lance aqui o total já pago até
              hoje, de uma vez — não é preciso lançar fatura por fatura do histórico. A partir de
              agora, registre as próximas faturas pelo módulo de Faturamento normalmente.
            </p>
          </div>

          <div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                id="tem_clausula_reajuste"
                type="checkbox"
                checked={temClausulaReajuste}
                onChange={(e) => setTemClausulaReajuste(e.target.checked)}
              />
              Este contrato tem cláusula de reajuste
            </label>
            <p className="mt-1 text-xs text-slate-500">
              Desmarque para contrato sem previsão de reajuste (ex.: compra pontual, licença de
              software sem correção).
            </p>
            {temClausulaReajuste && (
              <div className="mt-2 grid grid-cols-1 gap-4 rounded-lg border border-slate-200 bg-slate-50/60 p-3 sm:grid-cols-3">
                <div>
                  <label className={rotuloClasse} htmlFor="tipo_reajuste">
                    Tipo de reajuste
                  </label>
                  <select
                    id="tipo_reajuste"
                    className={campoClasse}
                    value={tipoReajuste}
                    onChange={(e) => setTipoReajuste(e.target.value as TipoReajuste)}
                  >
                    {Object.entries(ROTULOS_TIPO_REAJUSTE).map(([valor, rotulo]) => (
                      <option key={valor} value={valor}>
                        {rotulo}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={rotuloClasse} htmlFor="periodicidade_reajuste_meses">
                    Periodicidade (meses)
                  </label>
                  <input
                    id="periodicidade_reajuste_meses"
                    type="number"
                    min={1}
                    max={120}
                    className={campoClasse}
                    value={periodicidadeReajusteMeses}
                    onChange={(e) => setPeriodicidadeReajusteMeses(e.target.value)}
                    placeholder="ex.: 24"
                  />
                </div>
                <div>
                  <label className={rotuloClasse} htmlFor="indice_reajuste_padrao">
                    Índice padrão
                  </label>
                  <input
                    id="indice_reajuste_padrao"
                    className={campoClasse}
                    value={indiceReajustePadrao}
                    onChange={(e) => setIndiceReajustePadrao(e.target.value)}
                    placeholder="ex.: IPCA-E"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
            <p className="mb-3 text-sm font-semibold text-slate-800">
              Vigência inicial (instrumento de Origem)
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={rotuloClasse} htmlFor="fundamentacao">
                  Fundamentação
                </label>
                <input
                  id="fundamentacao"
                  className={campoClasse}
                  value={fundamentacao}
                  onChange={(e) => setFundamentacao(e.target.value)}
                  placeholder="ex.: Lei 13.303/16, art. 71 ou Decreto nº 1234/2020"
                  required
                />
              </div>
              <div>
                <label className={rotuloClasse} htmlFor="numero_documento_sei">
                  Nº documento SEI (opcional)
                </label>
                <input
                  id="numero_documento_sei"
                  className={campoClasse}
                  value={numeroDocumentoSei}
                  onChange={(e) => setNumeroDocumentoSei(e.target.value)}
                />
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-4">
              <div>
                <label className={rotuloClasse} htmlFor="data_inicio_vigencia">
                  Início da vigência
                </label>
                <input
                  id="data_inicio_vigencia"
                  type="date"
                  className={campoClasse}
                  value={dataInicioVigencia}
                  onChange={(e) => setDataInicioVigencia(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className={rotuloClasse} htmlFor="prazo_meses">
                  Prazo (meses)
                </label>
                <input
                  id="prazo_meses"
                  type="number"
                  min={1}
                  max={1200}
                  className={campoClasse}
                  value={prazoMeses}
                  onChange={(e) => setPrazoMeses(e.target.value)}
                  placeholder="ex.: 24"
                />
              </div>
              <div>
                <label className={rotuloClasse} htmlFor="data_fim_vigencia">
                  Fim da vigência
                </label>
                <input
                  id="data_fim_vigencia"
                  type="date"
                  className={campoClasse}
                  value={dataFimVigencia}
                  onChange={(e) => setDataFimVigencia(e.target.value)}
                  required
                />
              </div>
            </div>

            {calculandoVigencia && (
              <p className="mt-2 text-xs text-slate-500">Calculando o fim da vigência...</p>
            )}
            {avisoTeto && <p className="mt-2 text-xs font-medium text-red-600">{avisoTeto}</p>}

            <p className="mt-2 text-xs text-slate-500">
              Informe o prazo em meses e o fim da vigência é calculado sozinho — 13/06/2022 por 24
              meses termina em 12/06/2024, contando o dia de início como primeiro dia. A data
              continua editável, para o caso de um prazo que não feche em meses redondos. As
              próximas prorrogações (feitas depois, na ficha do contrato) só são aceitas até
              completar 5 anos a partir da data de assinatura original.
            </p>

            <div className="mt-4 border-t border-slate-200 pt-4">
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  id="tem_excecao_teto"
                  type="checkbox"
                  checked={temExcecaoTeto}
                  onChange={(e) => setTemExcecaoTeto(e.target.checked)}
                />
                Este contrato tem exceção ao teto de 5 anos (art. 71, Lei 13.303/16)
              </label>
              <p className="mt-1 text-xs text-slate-500">
                Marque só quando o prazo do contrato pode, por lei, ultrapassar 5 anos — ex.:
                locação de imóvel, cujo prazo longo é prática rotineira de mercado (inciso II).
                Sem isto, o sistema sempre recusa prorrogação além de 5 anos da assinatura.
              </p>

              {temExcecaoTeto && (
                <div className="mt-3 space-y-3 rounded-lg border border-amber-200 bg-amber-50/60 p-3">
                  <div>
                    <label className={rotuloClasse} htmlFor="excecao_teto_vigencia">
                      Inciso do art. 71
                    </label>
                    <select
                      id="excecao_teto_vigencia"
                      className={campoClasse}
                      value={excecaoTeto}
                      onChange={(e) => setExcecaoTeto(e.target.value as ExcecaoTetoVigencia)}
                    >
                      {Object.entries(ROTULOS_EXCECAO_TETO).map(([valor, rotulo]) => (
                        <option key={valor} value={valor}>
                          {rotulo}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className={rotuloClasse} htmlFor="excecao_teto_justificativa">
                      Justificativa
                    </label>
                    <textarea
                      id="excecao_teto_justificativa"
                      className={campoClasse}
                      rows={2}
                      value={excecaoJustificativa}
                      onChange={(e) => setExcecaoJustificativa(e.target.value)}
                      placeholder="ex.: locação de imóvel para a sede — prazo de 10 anos é prática rotineira do mercado imobiliário comercial."
                    />
                  </div>
                  <div>
                    <label className={rotuloClasse} htmlFor="excecao_teto_documento_sei">
                      Documento que formaliza a exceção (parecer jurídico/SEI)
                    </label>
                    <input
                      id="excecao_teto_documento_sei"
                      className={campoClasse}
                      value={excecaoDocumentoSei}
                      onChange={(e) => setExcecaoDocumentoSei(e.target.value)}
                      placeholder="ex.: SEI-04/000123/2026"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <span className={rotuloClasse}>Fiscal(is) do contrato *</span>
              <button type="button" onClick={() => setMostrarNovoFiscal((v) => !v)} className="btn-ghost btn-sm">
                + Novo fiscal
              </button>
            </div>

            {mostrarNovoFiscal && (
              <div className="mb-2 space-y-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
                <input
                  placeholder="Nome"
                  className={campoClasse}
                  value={novoFiscalNome}
                  onChange={(e) => setNovoFiscalNome(e.target.value)}
                />
                <input
                  placeholder="Matrícula (00/000.000-0)"
                  className={campoClasse}
                  value={novoFiscalMatricula}
                  onChange={(e) => setNovoFiscalMatricula(mascararMatricula(e.target.value))}
                />
                <input
                  placeholder="CPF (opcional, 000.000.000-00)"
                  className={campoClasse}
                  value={novoFiscalCpf}
                  onChange={(e) => setNovoFiscalCpf(mascararCpf(e.target.value))}
                />
                <button type="button" onClick={criarFiscal} className="btn-primary btn-sm">
                  Cadastrar fiscal
                </button>
              </div>
            )}

            <div className="max-h-40 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
              {fiscais.map((f) => (
                <label key={f.id} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={fiscaisSelecionados.includes(f.id)}
                    onChange={() => alternarFiscal(f.id)}
                  />
                  {f.nome} <span className="text-xs text-slate-500">({mascararMatricula(f.matricula)})</span>
                </label>
              ))}
              {fiscais.length === 0 && <p className="text-xs text-slate-500">Nenhum fiscal cadastrado ainda.</p>}
            </div>
          </div>

          <div>
            <label className={rotuloClasse} htmlFor="observacoes">
              Observações
            </label>
            <textarea
              id="observacoes"
              className={campoClasse}
              rows={2}
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
            />
          </div>

          {erro && <p className="text-sm text-red-600">{erro}</p>}

          <button type="submit" disabled={enviando} className="btn-primary w-full py-2.5">
            {enviando ? "Criando..." : "Criar contrato"}
          </button>
        </form>
      </main>
    </div>
  );
}

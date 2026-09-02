import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { apiContratos, apiFiscais, apiFornecedores } from "../../lib/apiContratos";
import { ErroApi } from "../../lib/api";
import { mascararCnpj, mascararCpf, mascararMatricula, mascararMoeda, moedaParaNumero } from "../../lib/mascaras";
import type {
  Fiscal,
  Fornecedor,
  FormaContratacao,
  FundamentacaoLei,
  ProcessoPayload,
  SistemaProcesso,
  TipoProcesso,
} from "../../lib/tiposContratos";
import { ROTULOS_FORMA_CONTRATACAO, ROTULOS_SISTEMA_PROCESSO, ROTULOS_TIPO_PROCESSO } from "../../lib/tiposContratos";
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

  const [fundamentacaoLei, setFundamentacaoLei] = useState<FundamentacaoLei>("lei_13303_16");
  const [fundamentacaoArtigo, setFundamentacaoArtigo] = useState("");
  const [numeroDocumentoSei, setNumeroDocumentoSei] = useState("");
  const [dataInicioVigencia, setDataInicioVigencia] = useState("");
  const [dataFimVigencia, setDataFimVigencia] = useState("");

  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    apiFornecedores.listar().then(setFornecedores).catch(() => setErro("Não foi possível carregar fornecedores."));
    apiFiscais.listar().then(setFiscais).catch(() => setErro("Não foi possível carregar fiscais."));
  }, []);

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
    setEnviando(true);
    try {
      const contrato = await apiContratos.criar({
        numero_contrato: numeroContrato,
        tipo_servico: tipoServico,
        objeto,
        fornecedor_id: fornecedorId,
        forma_contratacao: formaContratacao,
        data_assinatura_original: dataAssinatura,
        valor_inicial: moedaParaNumero(valorInicial),
        observacoes: observacoes || null,
        instrumento_origem: {
          fundamentacao_lei: fundamentacaoLei,
          fundamentacao_artigo: fundamentacaoArtigo,
          numero_documento_sei: numeroDocumentoSei || null,
          data_inicio_vigencia: dataInicioVigencia,
          data_fim_vigencia: dataFimVigencia,
        },
        processos,
        fiscais_ids: fiscaisSelecionados,
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

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={rotuloClasse} htmlFor="data_assinatura">
                Data de assinatura original
              </label>
              <input
                id="data_assinatura"
                type="date"
                className={campoClasse}
                value={dataAssinatura}
                onChange={(e) => setDataAssinatura(e.target.value)}
                required
              />
            </div>
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
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-4">
            <p className="mb-3 text-sm font-semibold text-slate-800">
              Vigência inicial (instrumento de Origem)
            </p>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className={rotuloClasse} htmlFor="fundamentacao_lei">
                  Fundamentação (lei)
                </label>
                <select
                  id="fundamentacao_lei"
                  className={campoClasse}
                  value={fundamentacaoLei}
                  onChange={(e) => setFundamentacaoLei(e.target.value as FundamentacaoLei)}
                >
                  <option value="lei_13303_16">Lei 13.303/16</option>
                  <option value="lei_14133_21">Lei 14.133/21</option>
                </select>
              </div>
              <div>
                <label className={rotuloClasse} htmlFor="fundamentacao_artigo">
                  Artigo
                </label>
                <input
                  id="fundamentacao_artigo"
                  className={campoClasse}
                  value={fundamentacaoArtigo}
                  onChange={(e) => setFundamentacaoArtigo(e.target.value)}
                  placeholder="ex.: art. 71"
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

            <div className="mt-4 grid grid-cols-2 gap-4">
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
            <p className="mt-2 text-xs text-slate-500">
              Prazo inicial da vigência — as próximas prorrogações (feitas depois, na ficha do contrato)
              só são aceitas até completar 5 anos a partir da data de assinatura original.
            </p>
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

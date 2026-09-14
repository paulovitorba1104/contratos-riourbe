import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { BadgeAlerta } from "../../components/BadgeAlerta";
import { ErroApi } from "../../lib/api";
import { apiAnexos, apiContratos, apiFiscais, apiFornecedores, urlAnexo } from "../../lib/apiContratos";
import { apiFaturas } from "../../lib/apiFaturas";
import { useAuth } from "../../lib/AuthContext";
import { formatarMoedaInicial, mascararMatricula, mascararMoeda, moedaParaNumero } from "../../lib/mascaras";
import type {
  AnexoInstrumento,
  CalculoReajuste,
  ContratoDetalhado,
  ExcecaoTetoVigencia,
  Fiscal,
  FormaContratacao,
  Fornecedor,
  FundamentacaoLei,
  LogAuditoria,
  Processo,
  SistemaProcesso,
  SubStatusInstrumento,
  TempoRestante,
  TipoInstrumento,
  TipoProcesso,
  TipoReajuste,
} from "../../lib/tiposContratos";
import {
  ROTULOS_ACAO_AUDITORIA,
  ROTULOS_EXCECAO_TETO,
  ROTULOS_FORMA_CONTRATACAO,
  ROTULOS_SISTEMA_PROCESSO,
  ROTULOS_STATUS_CONTRATO,
  ROTULOS_SUB_STATUS,
  ROTULOS_TIPO_INSTRUMENTO,
  ROTULOS_TIPO_PROCESSO,
  ROTULOS_TIPO_REAJUSTE,
  TIPOS_QUE_DEFINEM_VIGENCIA,
} from "../../lib/tiposContratos";
import type { Fatura } from "../../lib/tiposFaturas";
import { ROTULOS_STATUS_FATURA } from "../../lib/tiposFaturas";
import { useToast } from "../../lib/ToastContext";

const campoClasse = "field-input py-1.5";

function formatarMoeda(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/** Contagem regressiva legível: "faltam 8 meses e 12 dias" / "vencido há 3 dias". */
function textoTempoRestante(tempo: TempoRestante): string {
  const partes: string[] = [];
  if (tempo.meses > 0) partes.push(`${tempo.meses} ${tempo.meses === 1 ? "mês" : "meses"}`);
  if (tempo.dias > 0) partes.push(`${tempo.dias} ${tempo.dias === 1 ? "dia" : "dias"}`);
  if (partes.length === 0) return tempo.vencido ? "Vence hoje" : "Vence hoje";

  const quanto = partes.join(" e ");
  return tempo.vencido ? `Vencido há ${quanto}` : `Faltam ${quanto}`;
}

function CampoInfo({ rotulo, valor }: { rotulo: string; valor: string | null }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{rotulo}</p>
      <p className={valor ? "font-medium text-slate-900" : "text-slate-400"}>{valor || "—"}</p>
    </div>
  );
}

function processoResumo(processos: Processo[]): string {
  const principal = processos.find((p) => p.tipo === "principal") ?? processos[0];
  if (!principal) return "sem processo";
  const apensos = processos.length - 1;
  return `${principal.numero_processo}${apensos > 0 ? ` (+${apensos} apenso${apensos > 1 ? "s" : ""})` : ""}`;
}

const CORES_STATUS: Record<string, string> = {
  vigente: "bg-institucional-100 text-institucional-800",
  suspenso: "bg-amber-100 text-amber-800",
  encerrado: "bg-slate-200 text-slate-700",
};

function NovoInstrumentoForm({
  contratoId,
  dataAssinatura,
  excecaoTetoVigencia,
  aoCriar,
}: {
  contratoId: string;
  dataAssinatura: string;
  excecaoTetoVigencia: ExcecaoTetoVigencia | null;
  aoCriar: (c: ContratoDetalhado) => void;
}) {
  const [tipo, setTipo] = useState<TipoInstrumento>("apostilamento");
  const [fundamentacaoLei, setFundamentacaoLei] = useState<FundamentacaoLei>("lei_13303_16");
  const [fundamentacaoArtigo, setFundamentacaoArtigo] = useState("");
  const [numeroDocumentoSei, setNumeroDocumentoSei] = useState("");
  const [dataInicioVigencia, setDataInicioVigencia] = useState("");
  const [dataFimVigencia, setDataFimVigencia] = useState("");
  const [valorDelta, setValorDelta] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [prazoMeses, setPrazoMeses] = useState("");
  const [avisoTeto, setAvisoTeto] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  // Apostilamento de reajuste: calculadora embutida (substitui a calculadora
  // do cidadão) — os campos abaixo só valem quando o apostilamento é de
  // reajuste, não um apostilamento qualquer (ex.: mudança de fiscal).
  const [ehReajuste, setEhReajuste] = useState(false);
  const [reajusteIndiceNome, setReajusteIndiceNome] = useState("");
  const [reajusteValorMensalAntigo, setReajusteValorMensalAntigo] = useState("");
  const [reajusteIndiceBase, setReajusteIndiceBase] = useState("");
  const [reajusteIndiceAtual, setReajusteIndiceAtual] = useState("");
  const [reajusteDataInicio, setReajusteDataInicio] = useState("");
  const [reajusteDataFim, setReajusteDataFim] = useState("");
  const [previaReajuste, setPreviaReajuste] = useState<CalculoReajuste | null>(null);
  const [erroPreviaReajuste, setErroPreviaReajuste] = useState<string | null>(null);

  const exigeVigencia = TIPOS_QUE_DEFINEM_VIGENCIA.includes(tipo);
  const exigeValor = tipo === "acrescimo_valor" || tipo === "supressao_valor" || tipo === "apostilamento";
  const podeSerReajuste = tipo === "apostilamento";

  /** Mesmo contador do cadastro: início + prazo em meses = fim da vigência,
   * com o aviso do teto de 5 anos aparecendo enquanto se digita. É na
   * prorrogação que o teto costuma morder. */
  useEffect(() => {
    const meses = Number(prazoMeses);
    if (!exigeVigencia || !dataInicioVigencia || !Number.isInteger(meses) || meses < 1 || meses > 1200) {
      setAvisoTeto(null);
      return;
    }

    let cancelado = false;
    apiContratos
      .calcularVigencia(dataInicioVigencia, meses, dataAssinatura, excecaoTetoVigencia)
      .then((calculo) => {
        if (cancelado) return;
        setDataFimVigencia(calculo.data_fim);
        setAvisoTeto(
          calculo.excede_teto
            ? `Essa prorrogação levaria a vigência até ${calculo.data_fim}, ultrapassando o teto de ` +
              `5 anos da Lei 13.303/16 (limite: ${calculo.teto_cinco_anos}).`
            : null,
        );
      })
      .catch(() => {
        if (!cancelado) setAvisoTeto(null);
      });

    return () => {
      cancelado = true;
    };
  }, [dataInicioVigencia, prazoMeses, dataAssinatura, exigeVigencia, excecaoTetoVigencia]);

  // Desliga o modo reajuste se o tipo do instrumento mudar para algo que
  // não é apostilamento — os campos de reajuste só fazem sentido ali.
  useEffect(() => {
    if (!podeSerReajuste) setEhReajuste(false);
  }, [podeSerReajuste]);

  /** Prévia ao vivo da calculadora de reajuste — mesmo cálculo que o backend
   * vai fazer de verdade ao salvar, só que sem persistir nada ainda. */
  useEffect(() => {
    if (
      !ehReajuste ||
      !reajusteValorMensalAntigo ||
      !reajusteIndiceAtual ||
      !reajusteIndiceBase ||
      !reajusteDataInicio ||
      !reajusteDataFim
    ) {
      setPreviaReajuste(null);
      setErroPreviaReajuste(null);
      return;
    }

    let cancelado = false;
    apiContratos
      .calcularReajuste(
        moedaParaNumero(reajusteValorMensalAntigo),
        reajusteIndiceAtual,
        reajusteIndiceBase,
        reajusteDataInicio,
        reajusteDataFim,
      )
      .then((calculo) => {
        if (cancelado) return;
        setPreviaReajuste(calculo);
        setErroPreviaReajuste(null);
      })
      .catch((e) => {
        if (cancelado) return;
        setPreviaReajuste(null);
        setErroPreviaReajuste(e instanceof ErroApi ? e.message : "Não foi possível calcular o reajuste.");
      });

    return () => {
      cancelado = true;
    };
  }, [
    ehReajuste,
    reajusteValorMensalAntigo,
    reajusteIndiceAtual,
    reajusteIndiceBase,
    reajusteDataInicio,
    reajusteDataFim,
  ]);

  async function enviar() {
    setErro(null);
    setEnviando(true);
    try {
      const contrato = await apiContratos.criarInstrumento(contratoId, {
        tipo,
        fundamentacao_lei: fundamentacaoLei,
        fundamentacao_artigo: fundamentacaoArtigo,
        numero_documento_sei: numeroDocumentoSei || null,
        data_inicio_vigencia: exigeVigencia ? dataInicioVigencia : null,
        data_fim_vigencia: exigeVigencia ? dataFimVigencia : null,
        // No modo reajuste o valor é calculado e persistido pelo backend a
        // partir dos campos de reajuste — nunca envia valor_delta aqui.
        valor_delta: exigeValor && !ehReajuste ? moedaParaNumero(valorDelta) : null,
        observacoes: observacoes || null,
        ...(ehReajuste
          ? {
              reajuste_indice_nome: reajusteIndiceNome,
              reajuste_indice_atual: reajusteIndiceAtual,
              reajuste_indice_base: reajusteIndiceBase,
              reajuste_valor_mensal_antigo: moedaParaNumero(reajusteValorMensalAntigo),
              reajuste_data_inicio: reajusteDataInicio,
              reajuste_data_fim: reajusteDataFim,
            }
          : {}),
      });
      aoCriar(contrato);
      setFundamentacaoArtigo("");
      setNumeroDocumentoSei("");
      setDataInicioVigencia("");
      setDataFimVigencia("");
      setPrazoMeses("");
      setValorDelta("");
      setObservacoes("");
      setEhReajuste(false);
      setReajusteIndiceNome("");
      setReajusteValorMensalAntigo("");
      setReajusteIndiceBase("");
      setReajusteIndiceAtual("");
      setReajusteDataInicio("");
      setReajusteDataFim("");
      setPreviaReajuste(null);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível criar o instrumento.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-slate-50/60 p-4">
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Tipo</label>
          <select className={campoClasse} value={tipo} onChange={(e) => setTipo(e.target.value as TipoInstrumento)}>
            {Object.entries(ROTULOS_TIPO_INSTRUMENTO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Fundamentação (lei)</label>
          <select
            className={campoClasse}
            value={fundamentacaoLei}
            onChange={(e) => setFundamentacaoLei(e.target.value as FundamentacaoLei)}
          >
            <option value="lei_13303_16">Lei 13.303/16</option>
            <option value="lei_14133_21">Lei 14.133/21</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Artigo</label>
          <input
            className={campoClasse}
            value={fundamentacaoArtigo}
            onChange={(e) => setFundamentacaoArtigo(e.target.value)}
            placeholder="ex.: art. 71"
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Nº documento SEI (opcional)</label>
        <input className={campoClasse} value={numeroDocumentoSei} onChange={(e) => setNumeroDocumentoSei(e.target.value)} />
      </div>

      {exigeVigencia && (
        <>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="instrumento_data_inicio">
                Início da vigência
              </label>
              <input
                id="instrumento_data_inicio"
                type="date"
                className={campoClasse}
                value={dataInicioVigencia}
                onChange={(e) => setDataInicioVigencia(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="instrumento_prazo_meses">
                Prazo (meses)
              </label>
              <input
                id="instrumento_prazo_meses"
                type="number"
                min={1}
                max={1200}
                className={campoClasse}
                value={prazoMeses}
                onChange={(e) => setPrazoMeses(e.target.value)}
                placeholder="ex.: 12"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="instrumento_data_fim">
                Fim da vigência
              </label>
              <input
                id="instrumento_data_fim"
                type="date"
                className={campoClasse}
                value={dataFimVigencia}
                onChange={(e) => setDataFimVigencia(e.target.value)}
              />
            </div>
          </div>
          {avisoTeto && <p className="text-xs font-medium text-red-600">{avisoTeto}</p>}
          {excecaoTetoVigencia && (
            <p className="text-xs text-amber-700">
              Este contrato tem exceção ao teto de 5 anos ({ROTULOS_EXCECAO_TETO[excecaoTetoVigencia]}) — sem
              limite de prazo a verificar.
            </p>
          )}
        </>
      )}

      {podeSerReajuste && (
        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            id="eh_reajuste"
            type="checkbox"
            checked={ehReajuste}
            onChange={(e) => setEhReajuste(e.target.checked)}
          />
          Este apostilamento é de reajuste — calcular pelo índice
        </label>
      )}

      {exigeValor && !ehReajuste && (
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">
            {tipo === "acrescimo_valor" ? "Valor do acréscimo" : "Valor da supressão (digite - na frente)"}
          </label>
          <input
            type="text"
            inputMode="numeric"
            className={campoClasse}
            value={valorDelta}
            onChange={(e) => setValorDelta(mascararMoeda(e.target.value, true))}
            placeholder="0,00"
          />
        </div>
      )}

      {ehReajuste && (
        <div className="space-y-3 rounded-lg border border-institucional-200 bg-institucional-50/40 p-3">
          <p className="text-xs text-slate-600">
            Calculadora de reajuste — mesma conta da calculadora do cidadão, feita aqui dentro. O
            valor do apostilamento (a diferença a pagar) é calculado e salvo automaticamente.
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="reajuste_indice_nome">
                Índice
              </label>
              <input
                id="reajuste_indice_nome"
                className={campoClasse}
                value={reajusteIndiceNome}
                onChange={(e) => setReajusteIndiceNome(e.target.value)}
                placeholder="ex.: IPCA-E"
              />
            </div>
            <div>
              <label
                className="mb-1 block text-xs font-medium text-slate-600"
                htmlFor="reajuste_valor_mensal_antigo"
              >
                Valor mensal atual
              </label>
              <input
                id="reajuste_valor_mensal_antigo"
                type="text"
                inputMode="numeric"
                className={campoClasse}
                value={reajusteValorMensalAntigo}
                onChange={(e) => setReajusteValorMensalAntigo(mascararMoeda(e.target.value))}
                placeholder="0,00"
              />
            </div>
            <div />
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="reajuste_indice_base">
                Índice na data-base
              </label>
              <input
                id="reajuste_indice_base"
                type="text"
                inputMode="decimal"
                className={campoClasse}
                value={reajusteIndiceBase}
                onChange={(e) => setReajusteIndiceBase(e.target.value)}
                placeholder="ex.: 6500.00"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="reajuste_indice_atual">
                Índice atual
              </label>
              <input
                id="reajuste_indice_atual"
                type="text"
                inputMode="decimal"
                className={campoClasse}
                value={reajusteIndiceAtual}
                onChange={(e) => setReajusteIndiceAtual(e.target.value)}
                placeholder="ex.: 7169.26"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="reajuste_data_inicio">
                Marco do reajuste (início)
              </label>
              <input
                id="reajuste_data_inicio"
                type="date"
                className={campoClasse}
                value={reajusteDataInicio}
                onChange={(e) => setReajusteDataInicio(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="reajuste_data_fim">
                Até (próximo marco ou fim da vigência)
              </label>
              <input
                id="reajuste_data_fim"
                type="date"
                className={campoClasse}
                value={reajusteDataFim}
                onChange={(e) => setReajusteDataFim(e.target.value)}
              />
            </div>
          </div>

          {erroPreviaReajuste && <p className="text-xs text-red-600">{erroPreviaReajuste}</p>}

          {previaReajuste && (
            <div className="space-y-2 rounded-md border border-institucional-200 bg-white p-2">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <p className="text-slate-500">Valor mensal novo</p>
                  <p className="font-medium text-slate-900">{formatarMoeda(previaReajuste.valor_mensal_novo)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Variação</p>
                  <p className="font-medium text-slate-900">
                    {(Number(previaReajuste.percentual_variacao) * 100).toLocaleString("pt-BR", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 4,
                    })}
                    %
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Total do apostilamento</p>
                  <p className="font-medium text-institucional-700">
                    {formatarMoeda(previaReajuste.valor_total_apostilamento)}
                  </p>
                </div>
              </div>
              <div className="max-h-40 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="py-0.5 pr-2">Competência</th>
                      <th className="py-0.5 pr-2">Antigo</th>
                      <th className="py-0.5 pr-2">Reajustado</th>
                      <th className="py-0.5">Diferença</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previaReajuste.linhas.map((l) => (
                      <tr key={l.competencia} className="text-slate-700">
                        <td className="py-0.5 pr-2">{l.competencia}</td>
                        <td className="py-0.5 pr-2">{formatarMoeda(l.valor_antigo)}</td>
                        <td className="py-0.5 pr-2">{formatarMoeda(l.valor_reajustado)}</td>
                        <td className="py-0.5">{formatarMoeda(l.diferenca)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Observações</label>
        <textarea className={campoClasse} rows={2} value={observacoes} onChange={(e) => setObservacoes(e.target.value)} />
      </div>

      {erro && <p className="text-sm text-red-600">{erro}</p>}

      <button
        type="button"
        onClick={enviar}
        disabled={enviando}
        className="btn-primary"
      >
        {enviando ? "Registrando..." : "Registrar instrumento"}
      </button>
    </div>
  );
}

function formatarTamanhoArquivo(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Anexos de um instrumento processual — visualização rápida de contrato,
 * termo aditivo etc. direto na ficha, sem depender de nada externo (uso
 * local, sem preocupação de "pesar o servidor"). */
function AnexosDoInstrumento({
  contratoId,
  instrumentoId,
  anexos,
  ehAdministrador,
  aoAtualizar,
  aoRecarregar,
}: {
  contratoId: string;
  instrumentoId: string;
  anexos: AnexoInstrumento[];
  ehAdministrador: boolean;
  aoAtualizar: (c: ContratoDetalhado) => void;
  aoRecarregar: () => void;
}) {
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviarArquivo(arquivo: File | undefined) {
    if (!arquivo) return;
    setErro(null);
    setEnviando(true);
    try {
      const contrato = await apiContratos.anexarArquivo(contratoId, instrumentoId, arquivo);
      aoAtualizar(contrato);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível anexar o arquivo.");
    } finally {
      setEnviando(false);
    }
  }

  async function excluir(anexoId: string, nomeArquivo: string) {
    if (!window.confirm(`Excluir o anexo "${nomeArquivo}"? Esta ação não pode ser desfeita.`)) return;
    setErro(null);
    try {
      await apiAnexos.excluir(anexoId);
      aoRecarregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível excluir o anexo.");
    }
  }

  return (
    <div className="mt-2 border-t border-slate-100 pt-2">
      {anexos.length > 0 && (
        <ul className="space-y-1">
          {anexos.map((a) => (
            <li key={a.id} className="flex items-center justify-between gap-2 text-xs">
              <a
                href={urlAnexo(a.id)}
                target="_blank"
                rel="noopener noreferrer"
                className="truncate text-institucional-600 hover:underline"
                title={a.nome_arquivo}
              >
                {a.nome_arquivo}
              </a>
              <div className="flex shrink-0 items-center gap-2 text-slate-400">
                <span>{formatarTamanhoArquivo(a.tamanho_bytes)}</span>
                {ehAdministrador && (
                  <button
                    onClick={() => excluir(a.id, a.nome_arquivo)}
                    className="text-red-600 hover:underline"
                    title="Exclusão definitiva — restrita a administrador"
                  >
                    Excluir
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
      <label className="mt-1 inline-block cursor-pointer text-xs text-institucional-600 hover:underline">
        {enviando ? "Enviando..." : "+ Anexar arquivo"}
        <input
          type="file"
          className="hidden"
          disabled={enviando}
          accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png"
          onChange={(e) => {
            void enviarArquivo(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </label>
      {erro && <p className="text-xs text-red-600">{erro}</p>}
    </div>
  );
}

function NovoVinculoFiscalForm({
  contratoId,
  fiscaisDisponiveis,
  aoVincular,
}: {
  contratoId: string;
  fiscaisDisponiveis: Fiscal[];
  aoVincular: (c: ContratoDetalhado) => void;
}) {
  const [fiscalId, setFiscalId] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setErro(null);
    if (!fiscalId || !dataInicio) {
      setErro("Selecione o fiscal e a data de início.");
      return;
    }
    setEnviando(true);
    try {
      const contrato = await apiContratos.adicionarFiscal(contratoId, fiscalId, dataInicio);
      aoVincular(contrato);
      setFiscalId("");
      setDataInicio("");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível designar o fiscal.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
      <div className="grid grid-cols-2 gap-2">
        <select
          id="novo_vinculo_fiscal_id"
          className={campoClasse}
          value={fiscalId}
          onChange={(e) => setFiscalId(e.target.value)}
        >
          <option value="">Selecione o fiscal...</option>
          {fiscaisDisponiveis.map((f) => (
            <option key={f.id} value={f.id}>
              {f.nome} ({mascararMatricula(f.matricula)})
            </option>
          ))}
        </select>
        <input
          id="novo_vinculo_data_inicio"
          type="date"
          className={campoClasse}
          value={dataInicio}
          onChange={(e) => setDataInicio(e.target.value)}
        />
      </div>
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <button
        type="button"
        onClick={enviar}
        disabled={enviando}
        className="btn-primary btn-sm"
      >
        {enviando ? "Designando..." : "Designar fiscal"}
      </button>
    </div>
  );
}

function RegistrarGarantiaForm({
  contratoId,
  aoRegistrar,
  aoCancelar,
}: {
  contratoId: string;
  aoRegistrar: (c: ContratoDetalhado) => void;
  aoCancelar: () => void;
}) {
  const [dataInicio, setDataInicio] = useState("");
  const [dataFim, setDataFim] = useState("");
  const [observacao, setObservacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setErro(null);
    setEnviando(true);
    try {
      const atualizado = await apiContratos.registrarGarantia(contratoId, {
        data_inicio_garantia: dataInicio || null,
        data_fim_garantia: dataFim || null,
        observacao: observacao || null,
      });
      aoRegistrar(atualizado);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível registrar a garantia.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="garantia_data_inicio">
            Início da garantia
          </label>
          <input
            id="garantia_data_inicio"
            type="date"
            className={campoClasse}
            value={dataInicio}
            onChange={(e) => setDataInicio(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="garantia_data_fim">
            Fim da garantia
          </label>
          <input
            id="garantia_data_fim"
            type="date"
            className={campoClasse}
            value={dataFim}
            onChange={(e) => setDataFim(e.target.value)}
          />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Observação (opcional)</label>
        <input
          className={campoClasse}
          value={observacao}
          onChange={(e) => setObservacao(e.target.value)}
          placeholder="ex.: correção do prazo lançado por engano"
        />
      </div>
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={enviar}
          disabled={enviando}
          className="btn-primary btn-sm"
        >
          {enviando ? "Registrando..." : "Registrar garantia"}
        </button>
        <button
          type="button"
          onClick={aoCancelar}
          className="btn-secondary btn-sm"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}

function CamposProcesso({
  numeroProcesso,
  sistemaOrigem,
  tipo,
  aoMudarNumero,
  aoMudarSistema,
  aoMudarTipo,
}: {
  numeroProcesso: string;
  sistemaOrigem: SistemaProcesso;
  tipo: TipoProcesso;
  aoMudarNumero: (v: string) => void;
  aoMudarSistema: (v: SistemaProcesso) => void;
  aoMudarTipo: (v: TipoProcesso) => void;
}) {
  return (
    <div className="grid grid-cols-[2fr_1.3fr_1fr] gap-2">
      <input
        className={campoClasse}
        value={numeroProcesso}
        onChange={(e) => aoMudarNumero(e.target.value)}
        placeholder="ex.: SEI-04/000123/2026"
      />
      <select className={campoClasse} value={sistemaOrigem} onChange={(e) => aoMudarSistema(e.target.value as SistemaProcesso)}>
        {Object.entries(ROTULOS_SISTEMA_PROCESSO).map(([valor, rotulo]) => (
          <option key={valor} value={valor}>
            {rotulo}
          </option>
        ))}
      </select>
      <select className={campoClasse} value={tipo} onChange={(e) => aoMudarTipo(e.target.value as TipoProcesso)}>
        {Object.entries(ROTULOS_TIPO_PROCESSO).map(([valor, rotulo]) => (
          <option key={valor} value={valor}>
            {rotulo}
          </option>
        ))}
      </select>
    </div>
  );
}

function NovoProcessoForm({
  contratoId,
  aoAdicionar,
  aoCancelar,
}: {
  contratoId: string;
  aoAdicionar: (c: ContratoDetalhado) => void;
  aoCancelar: () => void;
}) {
  const [numeroProcesso, setNumeroProcesso] = useState("");
  const [sistemaOrigem, setSistemaOrigem] = useState<SistemaProcesso>("sei_rio");
  const [tipo, setTipo] = useState<TipoProcesso>("apenso");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    if (!numeroProcesso.trim()) {
      setErro("Informe o número do processo.");
      return;
    }
    setErro(null);
    setEnviando(true);
    try {
      const atualizado = await apiContratos.adicionarProcesso(contratoId, {
        numero_processo: numeroProcesso,
        sistema_origem: sistemaOrigem,
        tipo,
      });
      aoAdicionar(atualizado);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível adicionar o processo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
      <CamposProcesso
        numeroProcesso={numeroProcesso}
        sistemaOrigem={sistemaOrigem}
        tipo={tipo}
        aoMudarNumero={setNumeroProcesso}
        aoMudarSistema={setSistemaOrigem}
        aoMudarTipo={setTipo}
      />
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={enviar}
          disabled={enviando}
          className="btn-primary btn-sm"
        >
          {enviando ? "Adicionando..." : "Adicionar processo"}
        </button>
        <button
          type="button"
          onClick={aoCancelar}
          className="btn-secondary btn-sm"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}

function EditarProcessoForm({
  contratoId,
  processo,
  aoSalvar,
  aoCancelar,
}: {
  contratoId: string;
  processo: Processo;
  aoSalvar: (c: ContratoDetalhado) => void;
  aoCancelar: () => void;
}) {
  const [numeroProcesso, setNumeroProcesso] = useState(processo.numero_processo);
  const [sistemaOrigem, setSistemaOrigem] = useState<SistemaProcesso>(processo.sistema_origem);
  const [tipo, setTipo] = useState<TipoProcesso>(processo.tipo);
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    if (!numeroProcesso.trim()) {
      setErro("Informe o número do processo.");
      return;
    }
    setErro(null);
    setEnviando(true);
    try {
      const atualizado = await apiContratos.atualizarProcesso(contratoId, processo.id, {
        numero_processo: numeroProcesso,
        sistema_origem: sistemaOrigem,
        tipo,
      });
      aoSalvar(atualizado);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar o processo.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
      <CamposProcesso
        numeroProcesso={numeroProcesso}
        sistemaOrigem={sistemaOrigem}
        tipo={tipo}
        aoMudarNumero={setNumeroProcesso}
        aoMudarSistema={setSistemaOrigem}
        aoMudarTipo={setTipo}
      />
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={enviar}
          disabled={enviando}
          className="btn-primary btn-sm"
        >
          {enviando ? "Salvando..." : "Salvar"}
        </button>
        <button
          type="button"
          onClick={aoCancelar}
          className="btn-secondary btn-sm"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}

function EditarContratoForm({
  contrato,
  fornecedores,
  aoSalvar,
  aoCancelar,
}: {
  contrato: ContratoDetalhado;
  fornecedores: Fornecedor[];
  aoSalvar: (c: ContratoDetalhado) => void;
  aoCancelar: () => void;
}) {
  const [numeroContrato, setNumeroContrato] = useState(contrato.numero_contrato);
  const [tipoServico, setTipoServico] = useState(contrato.tipo_servico);
  const [objeto, setObjeto] = useState(contrato.objeto);
  const [fornecedorId, setFornecedorId] = useState(contrato.fornecedor_id);
  const [formaContratacao, setFormaContratacao] = useState<FormaContratacao>(contrato.forma_contratacao);
  const [dataAssinatura, setDataAssinatura] = useState(contrato.data_assinatura_original);
  const [valorInicial, setValorInicial] = useState(formatarMoedaInicial(contrato.valor_inicial));
  // Valor pago não se edita aqui — é sempre calculado (histórico + faturas
  // pagas no sistema). Ajuste pelo box dedicado no card "Financeiro".
  const [notaReserva, setNotaReserva] = useState(contrato.nota_reserva ?? "");
  const [notaEmpenho, setNotaEmpenho] = useState(contrato.nota_empenho ?? "");
  const [pt, setPt] = useState(contrato.pt ?? "");
  const [nd, setNd] = useState(contrato.nd ?? "");
  const [fr, setFr] = useState(contrato.fr ?? "");
  const [tipoPatrimonial, setTipoPatrimonial] = useState(contrato.tipo_patrimonial ?? "");
  const [itemPatrimonial, setItemPatrimonial] = useState(contrato.item_patrimonial ?? "");
  const [codigoCcon, setCodigoCcon] = useState(contrato.codigo_ccon ?? "");
  const [observacoes, setObservacoes] = useState(contrato.observacoes ?? "");

  // Exceção ao teto de 5 anos (art. 71, I ou II, da Lei 13.303/16) — semeada
  // do que o contrato já tem registrado.
  const [temExcecaoTeto, setTemExcecaoTeto] = useState(contrato.excecao_teto_vigencia !== null);
  const [excecaoTeto, setExcecaoTeto] = useState<ExcecaoTetoVigencia>(
    contrato.excecao_teto_vigencia ?? "art_71_ii",
  );
  const [excecaoJustificativa, setExcecaoJustificativa] = useState(contrato.excecao_teto_justificativa ?? "");
  const [excecaoDocumentoSei, setExcecaoDocumentoSei] = useState(contrato.excecao_teto_documento_sei ?? "");

  // Setor responsável pelo faturamento — semeado do que o contrato já tem.
  const [faturamentoPelaGct, setFaturamentoPelaGct] = useState(contrato.faturamento_gerido_pela_gct);
  const [setorResponsavelFaturamento, setSetorResponsavelFaturamento] = useState(
    contrato.setor_responsavel_faturamento ?? "",
  );

  // Cláusula de reajuste — semeada do que o contrato já tem registrado.
  const [temClausulaReajuste, setTemClausulaReajuste] = useState(contrato.tipo_reajuste !== null);
  const [tipoReajuste, setTipoReajuste] = useState<TipoReajuste>(contrato.tipo_reajuste ?? "automatico");
  const [periodicidadeReajusteMeses, setPeriodicidadeReajusteMeses] = useState(
    contrato.periodicidade_reajuste_meses ? String(contrato.periodicidade_reajuste_meses) : "24",
  );
  const [indiceReajustePadrao, setIndiceReajustePadrao] = useState(contrato.indice_reajuste_padrao ?? "");

  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setErro(null);
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
    setEnviando(true);
    try {
      const atualizado = await apiContratos.atualizar(contrato.id, {
        numero_contrato: numeroContrato,
        tipo_servico: tipoServico,
        objeto,
        fornecedor_id: fornecedorId,
        forma_contratacao: formaContratacao,
        data_assinatura_original: dataAssinatura,
        valor_inicial: moedaParaNumero(valorInicial),
        nota_reserva: notaReserva || null,
        nota_empenho: notaEmpenho || null,
        pt: pt || null,
        nd: nd || null,
        fr: fr || null,
        tipo_patrimonial: tipoPatrimonial || null,
        item_patrimonial: itemPatrimonial || null,
        codigo_ccon: codigoCcon || null,
        observacoes: observacoes || null,
        excecao_teto_vigencia: temExcecaoTeto ? excecaoTeto : null,
        excecao_teto_justificativa: temExcecaoTeto ? excecaoJustificativa : null,
        excecao_teto_documento_sei: temExcecaoTeto ? excecaoDocumentoSei : null,
        faturamento_gerido_pela_gct: faturamentoPelaGct,
        setor_responsavel_faturamento: faturamentoPelaGct ? null : setorResponsavelFaturamento,
        tipo_reajuste: temClausulaReajuste ? tipoReajuste : null,
        periodicidade_reajuste_meses: temClausulaReajuste ? Number(periodicidadeReajusteMeses) : null,
        indice_reajuste_padrao: temClausulaReajuste ? indiceReajustePadrao || null : null,
      });
      aoSalvar(atualizado);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar as alterações do contrato.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="card space-y-3 p-5">
      <h2 className="text-sm font-semibold text-slate-900">Editar contrato</h2>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Número do contrato</label>
          <input
            className={campoClasse}
            value={numeroContrato}
            onChange={(e) => setNumeroContrato(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Tipo de serviço</label>
          <input className={campoClasse} value={tipoServico} onChange={(e) => setTipoServico(e.target.value)} />
        </div>
      </div>
      <p className="text-xs text-slate-500">
        Os números de processo são gerenciados na seção "Processos" abaixo.
      </p>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Objeto</label>
        <textarea className={campoClasse} rows={2} value={objeto} onChange={(e) => setObjeto(e.target.value)} />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Fornecedor</label>
          <select className={campoClasse} value={fornecedorId} onChange={(e) => setFornecedorId(e.target.value)}>
            {fornecedores.map((f) => (
              <option key={f.id} value={f.id}>
                {f.razao_social}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Forma de contratação</label>
          <select
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
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Data de assinatura original</label>
          <input
            type="date"
            className={campoClasse}
            value={dataAssinatura}
            onChange={(e) => setDataAssinatura(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Valor inicial</label>
          <input
            type="text"
            inputMode="numeric"
            placeholder="0,00"
            className={campoClasse}
            value={valorInicial}
            onChange={(e) => setValorInicial(mascararMoeda(e.target.value))}
          />
        </div>
      </div>
      <p className="text-xs text-slate-500">
        O valor pago se ajusta no card "Financeiro" da ficha, não aqui.
      </p>

      <div className="border-t border-slate-200 pt-3">
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
          jurídicos pela AJU) — aqui a GCT só gerencia prazo e renovação; o contrato sai do
          módulo de Faturamento.
        </p>
        {!faturamentoPelaGct && (
          <div className="mt-2">
            <label className="mb-1 block text-xs font-medium text-slate-600">
              Setor responsável pelo faturamento
            </label>
            <input
              className={campoClasse}
              value={setorResponsavelFaturamento}
              onChange={(e) => setSetorResponsavelFaturamento(e.target.value)}
              placeholder="ex.: RH, AJU"
            />
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Nota de reserva</label>
          <input className={campoClasse} value={notaReserva} onChange={(e) => setNotaReserva(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Nota de empenho</label>
          <input className={campoClasse} value={notaEmpenho} onChange={(e) => setNotaEmpenho(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">PT</label>
          <input className={campoClasse} value={pt} onChange={(e) => setPt(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">ND</label>
          <input className={campoClasse} value={nd} onChange={(e) => setNd(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">FR</label>
          <input className={campoClasse} value={fr} onChange={(e) => setFr(e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Tipo patrimonial</label>
          <input
            className={campoClasse}
            value={tipoPatrimonial}
            onChange={(e) => setTipoPatrimonial(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Item patrimonial</label>
          <input
            className={campoClasse}
            value={itemPatrimonial}
            onChange={(e) => setItemPatrimonial(e.target.value)}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Código CCON</label>
          <input className={campoClasse} value={codigoCcon} onChange={(e) => setCodigoCcon(e.target.value)} />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Observações</label>
        <textarea
          className={campoClasse}
          rows={2}
          value={observacoes}
          onChange={(e) => setObservacoes(e.target.value)}
        />
      </div>

      <div className="border-t border-slate-200 pt-3">
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
          Controla o alerta de próximo marco de reajuste na ficha — o cálculo em si é feito ao
          registrar o apostilamento de reajuste, na seção de instrumentos.
        </p>

        {temClausulaReajuste && (
          <div className="mt-3 grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-slate-50/60 p-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="tipo_reajuste">
                Tipo
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
              <label
                className="mb-1 block text-xs font-medium text-slate-600"
                htmlFor="periodicidade_reajuste_meses"
              >
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
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="indice_reajuste_padrao">
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

      <div className="border-t border-slate-200 pt-3">
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
          Marque só quando o prazo do contrato pode, por lei, ultrapassar 5 anos — ex.: locação de
          imóvel, cujo prazo longo é prática rotineira de mercado (inciso II). Desmarcar limpa a
          justificativa e o documento registrados.
        </p>

        {temExcecaoTeto && (
          <div className="mt-3 space-y-3 rounded-lg border border-amber-200 bg-amber-50/60 p-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="excecao_teto_vigencia">
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
              <label className="mb-1 block text-xs font-medium text-slate-600" htmlFor="excecao_teto_justificativa">
                Justificativa
              </label>
              <textarea
                id="excecao_teto_justificativa"
                className={campoClasse}
                rows={2}
                value={excecaoJustificativa}
                onChange={(e) => setExcecaoJustificativa(e.target.value)}
              />
            </div>
            <div>
              <label
                className="mb-1 block text-xs font-medium text-slate-600"
                htmlFor="excecao_teto_documento_sei"
              >
                Documento que formaliza a exceção (parecer jurídico/SEI)
              </label>
              <input
                id="excecao_teto_documento_sei"
                className={campoClasse}
                value={excecaoDocumentoSei}
                onChange={(e) => setExcecaoDocumentoSei(e.target.value)}
              />
            </div>
          </div>
        )}
      </div>

      {erro && <p className="text-sm text-red-600">{erro}</p>}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={enviar}
          disabled={enviando}
          className="btn-primary"
        >
          {enviando ? "Salvando..." : "Salvar alterações"}
        </button>
        <button
          type="button"
          onClick={aoCancelar}
          className="btn-secondary btn-sm"
        >
          Cancelar
        </button>
      </div>
    </section>
  );
}

/** A ponte visível entre Contratos e Faturamento: as faturas daquele contrato,
 * em que etapa cada uma está e quanto já foi pago. */
function FaturasDoContrato({
  contratoId,
  faturamentoPelaGct,
  setorResponsavel,
}: {
  contratoId: string;
  faturamentoPelaGct: boolean;
  setorResponsavel: string | null;
}) {
  const [faturas, setFaturas] = useState<Fatura[] | null>(null);

  useEffect(() => {
    apiFaturas
      .listar({ contrato_id: contratoId })
      .then(setFaturas)
      .catch(() => setFaturas([]));
  }, [contratoId]);

  const emAndamento = (faturas ?? []).filter(
    (f) => !["paga", "devolvida", "cancelada"].includes(f.status),
  ).length;

  return (
    <section className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">
          Faturas {faturas ? `(${faturas.length})` : ""}
          {emAndamento > 0 && (
            <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
              {emAndamento} em andamento
            </span>
          )}
        </h2>
        {faturamentoPelaGct && (
          <Link to={`/faturas/nova?contrato=${contratoId}`} className="btn-secondary btn-sm">
            + Nova fatura
          </Link>
        )}
      </div>

      {!faturamentoPelaGct && (
        <p className="mb-3 rounded-md bg-amber-50 p-2 text-xs text-amber-800">
          O faturamento deste contrato é feito por {setorResponsavel || "outro setor"}, não pela
          Gerência de Contratos — aqui só a gestão de prazo e renovação. Novas faturas não podem
          ser registradas neste sistema para este contrato.
        </p>
      )}

      {faturas === null && <p className="text-sm text-slate-500">Carregando...</p>}
      {faturas?.length === 0 && (
        <p className="text-sm text-slate-500">Nenhuma fatura registrada para este contrato.</p>
      )}

      <ul className="space-y-2">
        {(faturas ?? []).map((f) => (
          <li key={f.id} className="flex items-center justify-between gap-3 text-sm">
            <div>
              <Link to={`/faturas/${f.id}`} className="font-medium text-slate-900 hover:underline">
                NF {f.numero_nota_fiscal}
              </Link>
              <span className="ml-2 text-xs text-slate-500">{f.competencia}</span>
              {f.numero_processo_sei && (
                <p className="text-xs text-slate-400">{f.numero_processo_sei}</p>
              )}
            </div>
            <div className="flex items-center gap-3">
              <span className="tabular-nums text-slate-700">
                {Number(f.valor_bruto).toLocaleString("pt-BR", {
                  style: "currency",
                  currency: "BRL",
                })}
              </span>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                {ROTULOS_STATUS_FATURA[f.status]}
              </span>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ContratoDetalhe() {
  const { id } = useParams<{ id: string }>();
  const navegar = useNavigate();
  const { usuario } = useAuth();
  const ehAdministrador = usuario?.papel === "administrador";
  const [contrato, setContrato] = useState<ContratoDetalhado | null>(null);
  const [fornecedor, setFornecedor] = useState<Fornecedor | null>(null);
  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [fiscaisDisponiveis, setFiscaisDisponiveis] = useState<Fiscal[]>([]);
  const [mostrarFormInstrumento, setMostrarFormInstrumento] = useState(false);
  const [mostrarFormFiscal, setMostrarFormFiscal] = useState(false);
  const [mostrarFormEditarContrato, setMostrarFormEditarContrato] = useState(false);
  const [mostrarFormGarantia, setMostrarFormGarantia] = useState(false);
  const [mostrarHistoricoGarantia, setMostrarHistoricoGarantia] = useState(false);
  const [mostrarFormNovoProcesso, setMostrarFormNovoProcesso] = useState(false);
  const [processoEmEdicaoId, setProcessoEmEdicaoId] = useState<string | null>(null);
  const [mostrarAuditoria, setMostrarAuditoria] = useState(false);
  const [auditoria, setAuditoria] = useState<LogAuditoria[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const { mostrarToast } = useToast();

  // Pré-carrega do valor_pago_anterior_sistema (a parte manual), não do
  // valor_pago total — que já soma as faturas pagas no sistema.
  const [valorPagoEdicao, setValorPagoEdicao] = useState("");

  function carregar() {
    if (!id) return;
    apiContratos
      .obter(id)
      .then((c) => {
        setContrato(c);
        setValorPagoEdicao(formatarMoedaInicial(c.valor_pago_anterior_sistema));
      })
      .catch(() => setErro("Não foi possível carregar o contrato."));
  }

  useEffect(carregar, [id]);

  useEffect(() => {
    apiFiscais.listar().then(setFiscaisDisponiveis).catch(() => {});
  }, []);

  useEffect(() => {
    apiFornecedores.listar().then(setFornecedores).catch(() => {});
  }, []);

  useEffect(() => {
    if (contrato) {
      setFornecedor(fornecedores.find((f) => f.id === contrato.fornecedor_id) ?? null);
    }
  }, [contrato?.fornecedor_id, fornecedores]);

  async function salvarPagamento() {
    if (!id) return;
    try {
      const atualizado = await apiContratos.atualizarPagamento(id, moedaParaNumero(valorPagoEdicao));
      setContrato(atualizado);
      mostrarToast("Valor pago atualizado com sucesso.");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível atualizar o pagamento.");
    }
  }

  async function alterarSubStatus(instrumentoId: string, subStatus: SubStatusInstrumento) {
    if (!id) return;
    try {
      const atualizado = await apiContratos.atualizarSubStatusInstrumento(id, instrumentoId, subStatus);
      setContrato(atualizado);
      mostrarToast("Sub-status do instrumento atualizado.");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível atualizar o sub-status.");
    }
  }

  async function encerrarVinculo(vinculoId: string) {
    if (!id) return;
    const hoje = new Date().toISOString().slice(0, 10);
    try {
      const atualizado = await apiContratos.encerrarVinculoFiscal(id, vinculoId, hoje);
      setContrato(atualizado);
      mostrarToast("Vínculo do fiscal encerrado.");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível encerrar o vínculo do fiscal.");
    }
  }

  async function excluirVinculo(vinculoId: string, nomeFiscal: string) {
    if (!id) return;
    if (!window.confirm(`Excluir a designação de "${nomeFiscal}" neste contrato? Essa ação não pode ser desfeita.`)) {
      return;
    }
    try {
      const atualizado = await apiContratos.excluirVinculoFiscal(id, vinculoId);
      setContrato(atualizado);
      mostrarToast("Fiscal removido do contrato.");
    } catch (e) {
      const mensagem = e instanceof ErroApi ? e.message : "Não foi possível excluir o vínculo do fiscal.";
      setErro(mensagem);
      mostrarToast(mensagem, "erro");
    }
  }

  async function excluirInstrumento(instrumentoId: string, tipo: string) {
    if (!id) return;
    if (
      !window.confirm(
        `Excluir o instrumento "${tipo}"? Essa ação não pode ser desfeita e pode alterar a vigência calculada do contrato.`,
      )
    ) {
      return;
    }
    try {
      const atualizado = await apiContratos.excluirInstrumento(id, instrumentoId);
      setContrato(atualizado);
      mostrarToast("Instrumento excluído.");
    } catch (e) {
      const mensagem = e instanceof ErroApi ? e.message : "Não foi possível excluir o instrumento.";
      setErro(mensagem);
      mostrarToast(mensagem, "erro");
    }
  }

  async function excluirProcesso(processoId: string, numeroProcesso: string) {
    if (!id) return;
    if (!window.confirm(`Excluir o processo "${numeroProcesso}"? Essa ação não pode ser desfeita.`)) {
      return;
    }
    try {
      const atualizado = await apiContratos.excluirProcesso(id, processoId);
      setContrato(atualizado);
      mostrarToast("Processo excluído.");
    } catch (e) {
      const mensagem = e instanceof ErroApi ? e.message : "Não foi possível excluir o processo.";
      setErro(mensagem);
      mostrarToast(mensagem, "erro");
    }
  }

  async function alternarAuditoria() {
    if (mostrarAuditoria) {
      setMostrarAuditoria(false);
      return;
    }
    setMostrarAuditoria(true);
    if (!auditoria && id) {
      try {
        const logs = await apiContratos.auditoria(id);
        setAuditoria(logs);
      } catch {
        mostrarToast("Não foi possível carregar o histórico de alterações.", "erro");
      }
    }
  }

  async function excluirContrato() {
    if (!id || !contrato) return;
    if (
      !window.confirm(
        `Excluir o contrato "${contrato.numero_contrato}" por completo? Isso apaga também todos os instrumentos, vínculos de fiscal e histórico de garantia. Essa ação não pode ser desfeita.`,
      )
    ) {
      return;
    }
    try {
      await apiContratos.excluir(id);
      mostrarToast("Contrato excluído.");
      navegar("/contratos");
    } catch (e) {
      const mensagem = e instanceof ErroApi ? e.message : "Não foi possível excluir o contrato.";
      setErro(mensagem);
      mostrarToast(mensagem, "erro");
    }
  }

  if (erro && !contrato) {
    return <p className="p-6 text-sm text-red-600">{erro}</p>;
  }
  if (!contrato) {
    return <p className="p-6 text-sm text-slate-600">Carregando...</p>;
  }

  return (
    <div className="page-shell">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Link to="/contratos" className="text-xs text-institucional-600 hover:underline">
              ← Contratos
            </Link>
            <div className="mt-1 flex items-center gap-3">
              <h1 className="text-lg font-semibold text-slate-900">
                Contrato {contrato.numero_contrato}
              </h1>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CORES_STATUS[contrato.status]}`}>
                {ROTULOS_STATUS_CONTRATO[contrato.status]}
              </span>
              {!contrato.faturamento_gerido_pela_gct && (
                <span
                  className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800"
                  title="A GCT só gerencia prazo e renovação deste contrato — o faturamento é de outro setor."
                >
                  Faturamento: {contrato.setor_responsavel_faturamento || "outro setor"}
                </span>
              )}
            </div>
            <p className="text-sm text-slate-600">
              {contrato.tipo_servico} · {processoResumo(contrato.processos)} ·{" "}
              {fornecedor?.razao_social ?? "..."} · {ROTULOS_FORMA_CONTRATACAO[contrato.forma_contratacao]}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setMostrarFormEditarContrato((v) => !v)}
              className="btn-secondary btn-sm"
            >
              {mostrarFormEditarContrato ? "Cancelar edição" : "Editar contrato"}
            </button>
            {ehAdministrador && (
              <button
                onClick={excluirContrato}
                className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                title="Exclusão definitiva — restrita a administrador"
              >
                Excluir contrato
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 p-6">
        {erro && <p className="text-sm text-red-600">{erro}</p>}

        {mostrarFormEditarContrato && (
          <EditarContratoForm
            contrato={contrato}
            fornecedores={fornecedores}
            aoSalvar={(c) => {
              setContrato(c);
              setMostrarFormEditarContrato(false);
              mostrarToast("Contrato atualizado com sucesso.");
            }}
            aoCancelar={() => setMostrarFormEditarContrato(false)}
          />
        )}

        <section className="card p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Objeto</h2>
          <p className="text-sm text-slate-600">{contrato.objeto}</p>
        </section>

        <section className="card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">
              Processos ({contrato.processos.length})
            </h2>
            <button
              onClick={() => {
                setProcessoEmEdicaoId(null);
                setMostrarFormNovoProcesso((v) => !v);
              }}
              className="btn-secondary btn-sm"
            >
              {mostrarFormNovoProcesso ? "Cancelar" : "+ Adicionar processo"}
            </button>
          </div>

          {mostrarFormNovoProcesso && (
            <div className="mb-3">
              <NovoProcessoForm
                contratoId={contrato.id}
                aoAdicionar={(c) => {
                  setContrato(c);
                  setMostrarFormNovoProcesso(false);
                  mostrarToast("Processo adicionado com sucesso.");
                }}
                aoCancelar={() => setMostrarFormNovoProcesso(false)}
              />
            </div>
          )}

          <ul className="space-y-2">
            {contrato.processos.map((p) =>
              processoEmEdicaoId === p.id ? (
                <li key={p.id}>
                  <EditarProcessoForm
                    contratoId={contrato.id}
                    processo={p}
                    aoSalvar={(c) => {
                      setContrato(c);
                      setProcessoEmEdicaoId(null);
                      mostrarToast("Processo atualizado com sucesso.");
                    }}
                    aoCancelar={() => setProcessoEmEdicaoId(null)}
                  />
                </li>
              ) : (
                <li key={p.id} className="flex items-center justify-between text-sm">
                  <div>
                    <span className="font-medium text-slate-900">{p.numero_processo}</span>{" "}
                    <span className="text-xs text-slate-500">
                      ({ROTULOS_SISTEMA_PROCESSO[p.sistema_origem]} ·{" "}
                      {ROTULOS_TIPO_PROCESSO[p.tipo]})
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        setMostrarFormNovoProcesso(false);
                        setProcessoEmEdicaoId(p.id);
                      }}
                      className="btn-secondary btn-sm"
                    >
                      Editar
                    </button>
                    {ehAdministrador && (
                      <button
                        onClick={() => excluirProcesso(p.id, p.numero_processo)}
                        className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                        title="Exclusão definitiva — restrita a administrador"
                      >
                        Excluir
                      </button>
                    )}
                  </div>
                </li>
              ),
            )}
          </ul>
        </section>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="card p-5">
            <h2 className="mb-2 text-sm font-semibold text-slate-900">Vigência atual</h2>
            {contrato.vigencia_inicio && contrato.vigencia_fim ? (
              <p className="text-sm text-slate-600">
                {contrato.vigencia_inicio} até {contrato.vigencia_fim}
              </p>
            ) : (
              <p className="text-sm text-slate-500">Sem instrumento de origem registrado ainda.</p>
            )}
            {contrato.tempo_restante_vigencia && (
              <p
                className={`mt-1 text-sm font-medium ${
                  contrato.tempo_restante_vigencia.vencido ? "text-red-600" : "text-slate-800"
                }`}
              >
                {textoTempoRestante(contrato.tempo_restante_vigencia)}
              </p>
            )}
            {contrato.excecao_teto_vigencia ? (
              <div className="mt-1 rounded-md bg-amber-50 p-2">
                <p className="text-xs font-medium text-amber-800">
                  Sem teto de 5 anos — exceção {ROTULOS_EXCECAO_TETO[contrato.excecao_teto_vigencia]}
                </p>
                {contrato.excecao_teto_justificativa && (
                  <p className="mt-0.5 text-xs text-amber-700">{contrato.excecao_teto_justificativa}</p>
                )}
                {contrato.excecao_teto_documento_sei && (
                  <p className="mt-0.5 text-xs text-amber-700">Doc.: {contrato.excecao_teto_documento_sei}</p>
                )}
              </div>
            ) : (
              <p className="mt-1 text-xs text-slate-500">Teto (5 anos): {contrato.teto_vigencia}</p>
            )}
            <div className="mt-2">
              <BadgeAlerta alerta={contrato.alerta_vigencia} />
            </div>
          </div>

          <div className="card p-5">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-900">Garantia contratual</h2>
              <button
                onClick={() => {
                  setMostrarHistoricoGarantia(false);
                  setMostrarFormGarantia((v) => !v);
                }}
                className="btn-secondary btn-sm"
              >
                {mostrarFormGarantia ? "Cancelar" : "Registrar garantia"}
              </button>
            </div>

            {mostrarFormGarantia ? (
              <RegistrarGarantiaForm
                contratoId={contrato.id}
                aoRegistrar={(c) => {
                  setContrato(c);
                  setMostrarFormGarantia(false);
                  mostrarToast("Garantia registrada com sucesso.");
                }}
                aoCancelar={() => setMostrarFormGarantia(false)}
              />
            ) : (
              <>
                {contrato.garantia_inicio && contrato.garantia_fim ? (
                  <p className="text-sm text-slate-600">
                    {contrato.garantia_inicio} até {contrato.garantia_fim}
                  </p>
                ) : (
                  <p className="text-sm text-slate-500">Nenhuma garantia registrada ainda.</p>
                )}
                <div className="mt-2">
                  <BadgeAlerta alerta={contrato.alerta_garantia} />
                </div>
                {contrato.garantias.length > 0 && (
                  <button
                    onClick={() => setMostrarHistoricoGarantia((v) => !v)}
                    className="mt-2 text-xs text-institucional-600 hover:underline"
                  >
                    {mostrarHistoricoGarantia ? "Ocultar histórico" : `Ver histórico (${contrato.garantias.length})`}
                  </button>
                )}
                {mostrarHistoricoGarantia && (
                  <ul className="mt-2 space-y-1.5 border-t border-slate-200 pt-2">
                    {[...contrato.garantias].reverse().map((g) => (
                      <li key={g.id} className="text-xs text-slate-500">
                        <span className="font-medium text-slate-700">
                          {g.data_inicio_garantia && g.data_fim_garantia
                            ? `${g.data_inicio_garantia} até ${g.data_fim_garantia}`
                            : "Sem datas"}
                        </span>{" "}
                        — registrado por {g.registrado_por_nome} em{" "}
                        {new Date(g.registrado_em).toLocaleString("pt-BR")}
                        {g.observacao && <p className="italic text-slate-500">{g.observacao}</p>}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>

          <div className="card p-5">
            <h2 className="mb-2 text-sm font-semibold text-slate-900">Reajuste</h2>
            {contrato.tipo_reajuste ? (
              <>
                <p className="text-sm text-slate-600">{ROTULOS_TIPO_REAJUSTE[contrato.tipo_reajuste]}</p>
                <p className="text-xs text-slate-500">
                  A cada {contrato.periodicidade_reajuste_meses} meses
                  {contrato.indice_reajuste_padrao ? ` — índice ${contrato.indice_reajuste_padrao}` : ""}
                </p>
                {contrato.proximo_marco_reajuste && (
                  <p className="mt-1 text-sm font-medium text-slate-800">
                    Próximo marco: {contrato.proximo_marco_reajuste}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-500">Sem cláusula de reajuste cadastrada.</p>
            )}
            <div className="mt-2">
              <BadgeAlerta alerta={contrato.alerta_reajuste} rotuloOk="Sem reajuste pendente" />
            </div>
          </div>
        </section>

        <section className="card p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Financeiro</h2>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-slate-500">Valor inicial</p>
              <p className="font-medium text-slate-900">{formatarMoeda(contrato.valor_inicial)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Valor atualizado</p>
              <p className="font-medium text-slate-900">{formatarMoeda(contrato.valor_atualizado)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Valor pago</p>
              <p className="font-medium text-slate-900">{formatarMoeda(contrato.valor_pago)}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Saldo a pagar</p>
              <p className="font-medium text-slate-900">{formatarMoeda(contrato.saldo_a_pagar)}</p>
            </div>
          </div>
          <div className="mt-3">
            <label className="mb-1 block text-xs font-medium text-slate-600">
              Valor pago fora do controle de faturas deste sistema
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                inputMode="numeric"
                placeholder="0,00"
                className={campoClasse}
                value={valorPagoEdicao}
                onChange={(e) => setValorPagoEdicao(mascararMoeda(e.target.value))}
              />
              <button
                onClick={salvarPagamento}
                className="btn-secondary btn-sm"
              >
                Ajustar
              </button>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Total já pago antes de este contrato entrar no controle de faturas do sistema, ou —
              quando o faturamento é de outro setor — o valor total pago, atualizado à mão. Soma-se
              ao que as faturas pagas aqui dentro já cobrem para formar o "Valor pago" acima; nunca
              o substitui.
            </p>
          </div>
        </section>

        <section className="card p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Dados administrativos</h2>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <CampoInfo rotulo="Data de assinatura original" valor={contrato.data_assinatura_original} />
            <CampoInfo rotulo="Nota de reserva" valor={contrato.nota_reserva} />
            <CampoInfo rotulo="Nota de empenho" valor={contrato.nota_empenho} />
            <CampoInfo rotulo="PT" valor={contrato.pt} />
            <CampoInfo rotulo="ND" valor={contrato.nd} />
            <CampoInfo rotulo="FR" valor={contrato.fr} />
            <CampoInfo rotulo="Tipo patrimonial" valor={contrato.tipo_patrimonial} />
            <CampoInfo rotulo="Item patrimonial" valor={contrato.item_patrimonial} />
            <CampoInfo rotulo="Código CCON" valor={contrato.codigo_ccon} />
          </div>
          <div className="mt-3 border-t border-slate-200 pt-3">
            <p className="text-xs text-slate-500">Observações</p>
            <p className={contrato.observacoes ? "text-sm text-slate-700" : "text-sm text-slate-400"}>
              {contrato.observacoes || "Nenhuma observação registrada."}
            </p>
          </div>
        </section>

        <section className="card p-5">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Fiscal(is) do contrato</h2>
            {contrato.status !== "encerrado" && (
              <button
                onClick={() => setMostrarFormFiscal((v) => !v)}
                className="btn-secondary btn-sm"
              >
                {mostrarFormFiscal ? "Cancelar" : "+ Designar fiscal"}
              </button>
            )}
          </div>

          {mostrarFormFiscal && (
            <div className="mb-3">
              <NovoVinculoFiscalForm
                contratoId={contrato.id}
                fiscaisDisponiveis={fiscaisDisponiveis}
                aoVincular={(c) => {
                  setContrato(c);
                  setMostrarFormFiscal(false);
                  mostrarToast("Fiscal designado com sucesso.");
                }}
              />
            </div>
          )}

          <ul className="space-y-2">
            {contrato.fiscais.map((v) => (
              <li key={v.id} className="flex items-center justify-between text-sm">
                <div>
                  <span className="font-medium text-slate-900">{v.nome}</span>{" "}
                  <span className="text-xs text-slate-500">({mascararMatricula(v.matricula)})</span>
                  <p className="text-xs text-slate-500">
                    {v.data_inicio} até {v.data_fim ?? "hoje"}
                  </p>
                </div>
                <div className="flex gap-2">
                  {v.data_fim === null && (
                    <button
                      onClick={() => encerrarVinculo(v.id)}
                      className="btn-secondary btn-sm"
                    >
                      Encerrar vínculo
                    </button>
                  )}
                  {ehAdministrador && (
                    <button
                      onClick={() => excluirVinculo(v.id, v.nome)}
                      className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                      title="Remove por completo — use quando o fiscal foi designado por engano neste contrato. Restrito a administrador."
                    >
                      Excluir
                    </button>
                  )}
                </div>
              </li>
            ))}
            {contrato.fiscais.length === 0 && (
              <p className="text-sm text-slate-500">Nenhum fiscal designado ainda.</p>
            )}
          </ul>
        </section>

        <section className="card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Instrumentos processuais</h2>
            {contrato.status !== "encerrado" && (
              <button
                onClick={() => setMostrarFormInstrumento((v) => !v)}
                className="btn-primary btn-sm"
              >
                {mostrarFormInstrumento ? "Cancelar" : "+ Novo instrumento"}
              </button>
            )}
          </div>

          {mostrarFormInstrumento && (
            <div className="mb-4">
              <NovoInstrumentoForm
                contratoId={contrato.id}
                dataAssinatura={contrato.data_assinatura_original}
                excecaoTetoVigencia={contrato.excecao_teto_vigencia}
                aoCriar={(c) => {
                  setContrato(c);
                  setMostrarFormInstrumento(false);
                  mostrarToast("Instrumento registrado com sucesso.");
                }}
              />
            </div>
          )}

          <div>
            {contrato.instrumentos.length === 0 && (
              <p className="text-sm text-slate-500">Nenhum instrumento registrado ainda.</p>
            )}
            {contrato.instrumentos.map((i, indice) => (
              <div key={i.id} className="relative flex gap-3 pb-4 last:pb-0">
                {indice !== contrato.instrumentos.length - 1 && (
                  <span className="absolute left-[5px] top-4 h-full w-px bg-slate-200" aria-hidden="true" />
                )}
                <span
                  className="relative z-10 mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full border-2 border-institucional-500 bg-white"
                  aria-hidden="true"
                />
                <div className="flex-1 rounded-lg border border-slate-200 p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-medium text-slate-900">{ROTULOS_TIPO_INSTRUMENTO[i.tipo]}</p>
                    <div className="flex items-center gap-2">
                      <select
                        className="rounded-lg border border-slate-300 px-2 py-1 text-xs focus:border-institucional-500 focus:outline-none focus:ring-2 focus:ring-institucional-500/20"
                        value={i.sub_status}
                        onChange={(e) => alterarSubStatus(i.id, e.target.value as SubStatusInstrumento)}
                      >
                        {Object.entries(ROTULOS_SUB_STATUS).map(([valor, rotulo]) => (
                          <option key={valor} value={valor}>
                            {rotulo}
                          </option>
                        ))}
                      </select>
                      {ehAdministrador && (
                        <button
                          onClick={() => excluirInstrumento(i.id, ROTULOS_TIPO_INSTRUMENTO[i.tipo])}
                          className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                          title="Exclusão definitiva — restrita a administrador"
                        >
                          Excluir
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="text-xs text-slate-500">
                    {i.fundamentacao_lei === "lei_13303_16" ? "Lei 13.303/16" : "Lei 14.133/21"}, {i.fundamentacao_artigo}
                  </p>
                  {i.data_inicio_vigencia && i.data_fim_vigencia && (
                    <p className="text-xs text-slate-500">
                      Vigência: {i.data_inicio_vigencia} até {i.data_fim_vigencia}
                    </p>
                  )}
                  {i.valor_delta && (
                    <p className="text-xs text-slate-500">Valor: {formatarMoeda(i.valor_delta)}</p>
                  )}
                  {i.reajuste_data_inicio && (
                    <p className="text-xs text-slate-500">
                      Reajuste{i.reajuste_indice_nome ? ` (${i.reajuste_indice_nome})` : ""}:{" "}
                      {i.reajuste_valor_mensal_antigo && formatarMoeda(i.reajuste_valor_mensal_antigo)} →{" "}
                      {i.reajuste_valor_mensal_novo && formatarMoeda(i.reajuste_valor_mensal_novo)}, de{" "}
                      {i.reajuste_data_inicio} até {i.reajuste_data_fim}
                    </p>
                  )}
                  {i.observacoes && <p className="mt-1 text-xs text-slate-500">{i.observacoes}</p>}
                  <AnexosDoInstrumento
                    contratoId={contrato.id}
                    instrumentoId={i.id}
                    anexos={i.anexos}
                    ehAdministrador={ehAdministrador}
                    aoAtualizar={setContrato}
                    aoRecarregar={carregar}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        <FaturasDoContrato
          contratoId={contrato.id}
          faturamentoPelaGct={contrato.faturamento_gerido_pela_gct}
          setorResponsavel={contrato.setor_responsavel_faturamento}
        />

        <section className="card p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Histórico de alterações</h2>
            <button onClick={alternarAuditoria} className="btn-secondary btn-sm">
              {mostrarAuditoria ? "Ocultar" : "Ver histórico"}
            </button>
          </div>

          {mostrarAuditoria && (
            <ul className="mt-3 space-y-2 border-t border-slate-200 pt-3">
              {auditoria === null && <p className="text-sm text-slate-500">Carregando...</p>}
              {auditoria?.length === 0 && (
                <p className="text-sm text-slate-500">Nenhuma alteração registrada ainda.</p>
              )}
              {auditoria?.map((log) => (
                <li key={log.id} className="text-xs text-slate-500">
                  <span className="font-medium text-slate-700">{ROTULOS_ACAO_AUDITORIA[log.acao] ?? log.acao}</span>{" "}
                  — por {log.usuario_nome ?? "usuário removido"} em {new Date(log.criado_em).toLocaleString("pt-BR")}
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

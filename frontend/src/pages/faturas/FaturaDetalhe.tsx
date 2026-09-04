import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiFaturas, apiModelosChecklist } from "../../lib/apiFaturas";
import { useAuth } from "../../lib/AuthContext";
import { formatarMoedaInicial, mascararMoeda, moedaParaNumero } from "../../lib/mascaras";
import type {
  FaturaDetalhada,
  ItemConferenciaPayload,
  ModeloChecklist,
  RetencaoSugerida,
  SituacaoItemConferencia,
  StatusFatura,
  Tributo,
} from "../../lib/tiposFaturas";
import {
  ROTULOS_SITUACAO_ITEM,
  ROTULOS_STATUS_FATURA,
  ROTULOS_TIPO_EVENTO,
  ROTULOS_TRIBUTO,
} from "../../lib/tiposFaturas";
import { useToast } from "../../lib/ToastContext";
import { competenciaLegivel, formatarMoeda } from "./FaturasKanban";

const CORES_STATUS: Record<StatusFatura, string> = {
  recebida: "bg-slate-200 text-slate-700",
  em_conferencia: "bg-amber-100 text-amber-800",
  conferida: "bg-sky-100 text-sky-800",
  atestada: "bg-institucional-100 text-institucional-800",
  paga: "bg-emerald-100 text-emerald-800",
  devolvida: "bg-red-100 text-red-800",
  cancelada: "bg-slate-200 text-slate-500",
};

function hoje(): string {
  return new Date().toISOString().slice(0, 10);
}

function CampoInfo({ rotulo, valor }: { rotulo: string; valor: string | null }) {
  return (
    <div>
      <p className="text-xs text-slate-500">{rotulo}</p>
      <p className={valor ? "font-medium text-slate-900" : "text-slate-400"}>{valor || "—"}</p>
    </div>
  );
}

/** Ação do fluxo que pede uma data e, em alguns casos, um motivo. */
function AcaoComData({
  titulo,
  rotuloBotao,
  exigeObservacao,
  aoConfirmar,
  aoCancelar,
}: {
  titulo: string;
  rotuloBotao: string;
  exigeObservacao?: boolean;
  aoConfirmar: (dados: { data_evento: string; observacoes: string | null }) => Promise<void>;
  aoCancelar: () => void;
}) {
  const [data, setData] = useState(hoje());
  const [observacoes, setObservacoes] = useState("");
  const [enviando, setEnviando] = useState(false);

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
      <p className="text-sm font-medium text-slate-800">{titulo}</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div>
          <label className="mb-1 block text-xs text-slate-500">Data</label>
          <input type="date" className="field-input py-1.5" value={data} onChange={(e) => setData(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500">
            {exigeObservacao ? "Motivo (obrigatório)" : "Observação"}
          </label>
          <input
            className="field-input py-1.5"
            value={observacoes}
            onChange={(e) => setObservacoes(e.target.value)}
          />
        </div>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={enviando || (exigeObservacao && !observacoes.trim())}
          onClick={async () => {
            setEnviando(true);
            try {
              await aoConfirmar({ data_evento: data, observacoes: observacoes || null });
            } finally {
              setEnviando(false);
            }
          }}
          className="btn-primary btn-sm"
        >
          {enviando ? "Registrando..." : rotuloBotao}
        </button>
        <button type="button" onClick={aoCancelar} className="btn-secondary btn-sm">
          Cancelar
        </button>
      </div>
    </div>
  );
}

export function FaturaDetalhe() {
  const { id } = useParams<{ id: string }>();
  const navegar = useNavigate();
  const { usuario } = useAuth();
  const ehAdministrador = usuario?.papel === "administrador";
  const { mostrarToast } = useToast();

  const [fatura, setFatura] = useState<FaturaDetalhada | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [acao, setAcao] = useState<"atesto" | "pagamento" | "devolucao" | "cancelamento" | null>(null);
  const [mostrarEdicao, setMostrarEdicao] = useState(false);
  const [mostrarConferencia, setMostrarConferencia] = useState(false);
  const [mostrarTributos, setMostrarTributos] = useState(false);
  const [mostrarGlosa, setMostrarGlosa] = useState(false);

  function carregar() {
    if (!id) return;
    apiFaturas
      .obter(id)
      .then(setFatura)
      .catch(() => setErro("Não foi possível carregar a fatura."));
  }

  useEffect(carregar, [id]);

  async function executar(promessa: Promise<FaturaDetalhada>, mensagem: string) {
    try {
      setFatura(await promessa);
      setAcao(null);
      mostrarToast(mensagem);
    } catch (e) {
      const texto = e instanceof ErroApi ? e.message : "Não foi possível concluir a ação.";
      mostrarToast(texto, "erro");
    }
  }

  async function excluirFatura() {
    if (!id || !fatura) return;
    if (
      !window.confirm(
        `Excluir a fatura NF ${fatura.numero_nota_fiscal} por completo? Essa ação não pode ser desfeita.`,
      )
    ) {
      return;
    }
    try {
      await apiFaturas.excluir(id);
      mostrarToast("Fatura excluída.");
      navegar("/faturas");
    } catch (e) {
      mostrarToast(e instanceof ErroApi ? e.message : "Não foi possível excluir a fatura.", "erro");
    }
  }

  if (erro && !fatura) return <p className="p-6 text-sm text-red-600">{erro}</p>;
  if (!fatura) return <p className="p-6 text-sm text-slate-600">Carregando...</p>;

  const emAndamento = !["paga", "devolvida", "cancelada"].includes(fatura.status);

  return (
    <div className="page-shell">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Link to="/faturas" className="text-xs font-medium text-institucional-600 hover:underline">
              ← Faturas
            </Link>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <h1 className="page-title">NF {fatura.numero_nota_fiscal}</h1>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CORES_STATUS[fatura.status]}`}>
                {ROTULOS_STATUS_FATURA[fatura.status]}
              </span>
            </div>
            <p className="text-sm text-slate-600">
              {fatura.fornecedor_nome} · {competenciaLegivel(fatura.competencia)} ·{" "}
              <Link to={`/contratos/${fatura.contrato_id}`} className="hover:underline">
                Contrato {fatura.contrato_numero}
              </Link>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setMostrarEdicao((v) => !v)} className="btn-secondary btn-sm">
              {mostrarEdicao ? "Cancelar edição" : "Editar dados"}
            </button>
            {ehAdministrador && (
              <button
                onClick={excluirFatura}
                className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                title="Exclusão definitiva — restrita a administrador"
              >
                Excluir
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 p-6">
        {mostrarEdicao && (
          <EditarFaturaForm
            fatura={fatura}
            aoSalvar={(f) => {
              setFatura(f);
              setMostrarEdicao(false);
              mostrarToast("Dados da fatura atualizados.");
            }}
            aoCancelar={() => setMostrarEdicao(false)}
          />
        )}

        {/* Ações do fluxo */}
        {emAndamento && (
          <section className="card p-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-900">Andamento</h2>
            <div className="flex flex-wrap gap-2">
              {fatura.status === "conferida" && (
                <button onClick={() => setAcao("atesto")} className="btn-primary btn-sm">
                  Atestar
                </button>
              )}
              {fatura.status === "atestada" && (
                <button onClick={() => setAcao("pagamento")} className="btn-primary btn-sm">
                  Registrar pagamento
                </button>
              )}
              <button onClick={() => setAcao("devolucao")} className="btn-secondary btn-sm">
                Devolver ao fornecedor
              </button>
              <button
                onClick={() => setAcao("cancelamento")}
                className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
              >
                Cancelar fatura
              </button>
            </div>

            {acao === "atesto" && (
              <AcaoComData
                titulo="Atesto do fiscal — confirma que o serviço foi prestado"
                rotuloBotao="Atestar"
                aoCancelar={() => setAcao(null)}
                aoConfirmar={(d) => executar(apiFaturas.atestar(fatura.id, d), "Fatura atestada.")}
              />
            )}
            {acao === "pagamento" && (
              <AcaoComData
                titulo="Registrar pagamento"
                rotuloBotao="Registrar pagamento"
                aoCancelar={() => setAcao(null)}
                aoConfirmar={(d) =>
                  executar(apiFaturas.registrarPagamento(fatura.id, d), "Pagamento registrado.")
                }
              />
            )}
            {acao === "devolucao" && (
              <AcaoComData
                titulo="Devolver ao fornecedor"
                rotuloBotao="Devolver"
                exigeObservacao
                aoCancelar={() => setAcao(null)}
                aoConfirmar={(d) => executar(apiFaturas.devolver(fatura.id, d), "Fatura devolvida.")}
              />
            )}
            {acao === "cancelamento" && (
              <AcaoComData
                titulo="Cancelar fatura"
                rotuloBotao="Cancelar fatura"
                exigeObservacao
                aoCancelar={() => setAcao(null)}
                aoConfirmar={(d) => executar(apiFaturas.cancelar(fatura.id, d), "Fatura cancelada.")}
              />
            )}
          </section>
        )}

        {/* Valores */}
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Valores</h2>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <CampoInfo rotulo="Valor da nota" valor={formatarMoeda(fatura.valor_bruto)} />
            <CampoInfo rotulo="Glosas" valor={formatarMoeda(fatura.valor_glosas)} />
            <CampoInfo rotulo="Retenções" valor={formatarMoeda(fatura.valor_retencoes)} />
            <CampoInfo rotulo="Líquido a receber" valor={formatarMoeda(fatura.valor_liquido)} />
          </div>
        </section>

        {/* Dados */}
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Dados da fatura</h2>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <CampoInfo rotulo="Série" valor={fatura.serie} />
            <CampoInfo rotulo="Processo da fatura" valor={fatura.numero_processo_sei} />
            <CampoInfo rotulo="Emissão" valor={fatura.data_emissao} />
            <CampoInfo rotulo="Recebimento" valor={fatura.data_recebimento} />
            <CampoInfo rotulo="Vencimento" valor={fatura.data_vencimento} />
            <CampoInfo rotulo="Envio à GCO" valor={fatura.data_envio_gco} />
            <CampoInfo rotulo="Liquidação" valor={fatura.data_liquidacao} />
            <CampoInfo rotulo="Pagamento" valor={fatura.data_pagamento} />
          </div>
          {fatura.observacoes && (
            <div className="mt-3 border-t border-slate-200 pt-3">
              <p className="text-xs text-slate-500">Observações</p>
              <p className="text-sm text-slate-700">{fatura.observacoes}</p>
            </div>
          )}
        </section>

        {/* Conferência documental */}
        <section className="card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Conferência documental</h2>
            {emAndamento && (
              <button
                onClick={() => setMostrarConferencia((v) => !v)}
                className="btn-secondary btn-sm"
              >
                {mostrarConferencia ? "Cancelar" : "Nova conferência"}
              </button>
            )}
          </div>

          {mostrarConferencia && (
            <ConferenciaForm
              faturaId={fatura.id}
              aoRegistrar={(f) => {
                setFatura(f);
                setMostrarConferencia(false);
                mostrarToast("Conferência registrada.");
              }}
              aoCancelar={() => setMostrarConferencia(false)}
            />
          )}

          {fatura.conferencias.length === 0 && !mostrarConferencia && (
            <p className="text-sm text-slate-500">Nenhuma conferência registrada ainda.</p>
          )}

          {[...fatura.conferencias].reverse().map((conferencia, indice) => (
            <div
              key={conferencia.id}
              className={`rounded-lg border border-slate-200 p-3 ${indice > 0 ? "mt-2 opacity-70" : "mt-2"}`}
            >
              <p className="text-xs text-slate-500">
                {indice === 0 ? "Conferência mais recente" : "Conferência anterior"} — por{" "}
                {conferencia.conferido_por_nome} em{" "}
                {new Date(conferencia.conferido_em).toLocaleString("pt-BR")}
              </p>
              <ul className="mt-2 space-y-1">
                {conferencia.itens.map((item) => (
                  <li key={item.id} className="flex items-start justify-between gap-3 text-sm">
                    <span className="text-slate-700">
                      {item.descricao}
                      {item.obrigatorio && <span className="text-red-500"> *</span>}
                    </span>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${
                        item.situacao === "conforme"
                          ? "bg-emerald-100 text-emerald-800"
                          : item.situacao === "nao_conforme"
                            ? "bg-red-100 text-red-800"
                            : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {ROTULOS_SITUACAO_ITEM[item.situacao]}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>

        {/* Conferência tributária */}
        <section className="card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Conferência tributária</h2>
            {emAndamento && (
              <button onClick={() => setMostrarTributos((v) => !v)} className="btn-secondary btn-sm">
                {mostrarTributos ? "Cancelar" : "Conferir impostos"}
              </button>
            )}
          </div>

          {mostrarTributos && (
            <TributosForm
              fatura={fatura}
              aoRegistrar={(f) => {
                setFatura(f);
                setMostrarTributos(false);
                mostrarToast("Conferência tributária registrada.");
              }}
              aoCancelar={() => setMostrarTributos(false)}
            />
          )}

          {fatura.retencoes.length === 0 && !mostrarTributos && (
            <p className="text-sm text-slate-500">Nenhum imposto conferido ainda.</p>
          )}

          {fatura.retencoes.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-slate-500">
                    <th className="pb-2">Tributo</th>
                    <th className="pb-2">Base</th>
                    <th className="pb-2">Alíquota</th>
                    <th className="pb-2">Esperado</th>
                    <th className="pb-2">Na nota</th>
                    <th className="pb-2">Situação</th>
                  </tr>
                </thead>
                <tbody>
                  {fatura.retencoes.map((r) => (
                    <tr key={r.id} className="border-t border-slate-200">
                      <td className="py-2 font-medium text-slate-900">{ROTULOS_TRIBUTO[r.tributo]}</td>
                      <td className="py-2 tabular-nums text-slate-600">{formatarMoeda(r.base_calculo)}</td>
                      <td className="py-2 tabular-nums text-slate-600">{Number(r.aliquota)}%</td>
                      <td className="py-2 tabular-nums text-slate-600">{formatarMoeda(r.valor_esperado)}</td>
                      <td className="py-2 tabular-nums text-slate-900">{formatarMoeda(r.valor_informado)}</td>
                      <td className="py-2">
                        {r.divergente ? (
                          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-800">
                            divergência
                          </span>
                        ) : (
                          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">
                            confere
                          </span>
                        )}
                        {r.observacao && <p className="mt-1 text-xs text-slate-500">{r.observacao}</p>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Glosas */}
        <section className="card p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">Glosas</h2>
            {emAndamento && (
              <button onClick={() => setMostrarGlosa((v) => !v)} className="btn-secondary btn-sm">
                {mostrarGlosa ? "Cancelar" : "+ Registrar glosa"}
              </button>
            )}
          </div>

          {mostrarGlosa && (
            <GlosaForm
              faturaId={fatura.id}
              aoRegistrar={(f) => {
                setFatura(f);
                setMostrarGlosa(false);
                mostrarToast("Glosa registrada.");
              }}
              aoCancelar={() => setMostrarGlosa(false)}
            />
          )}

          {fatura.glosas.length === 0 && !mostrarGlosa && (
            <p className="text-sm text-slate-500">Nenhuma glosa nesta fatura.</p>
          )}

          <ul className="space-y-2">
            {fatura.glosas.map((glosa) => (
              <li key={glosa.id} className="flex items-start justify-between gap-3 text-sm">
                <div>
                  <span className="font-medium text-slate-900">{formatarMoeda(glosa.valor)}</span>
                  <p className="text-xs text-slate-600">{glosa.motivo}</p>
                  <p className="text-xs text-slate-400">
                    por {glosa.registrado_por_nome} em{" "}
                    {new Date(glosa.registrado_em).toLocaleString("pt-BR")}
                  </p>
                </div>
                {ehAdministrador && (
                  <button
                    onClick={() =>
                      executar(apiFaturas.excluirGlosa(fatura.id, glosa.id), "Glosa excluída.")
                    }
                    className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                  >
                    Excluir
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>

        {/* Linha do tempo */}
        <section className="card p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">Andamento registrado</h2>
          <div>
            {fatura.eventos.map((evento, indice) => (
              <div key={evento.id} className="relative flex gap-3 pb-4 last:pb-0">
                {indice !== fatura.eventos.length - 1 && (
                  <span className="absolute left-[5px] top-4 h-full w-px bg-slate-200" aria-hidden="true" />
                )}
                <span
                  className="relative z-10 mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full border-2 border-institucional-500 bg-white"
                  aria-hidden="true"
                />
                <div className="flex-1 text-sm">
                  <p className="font-medium text-slate-900">{ROTULOS_TIPO_EVENTO[evento.tipo]}</p>
                  <p className="text-xs text-slate-500">
                    {evento.data_evento} — por {evento.responsavel_nome}
                  </p>
                  {evento.observacoes && (
                    <p className="mt-0.5 text-xs text-slate-500">{evento.observacoes}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

// --------------------------------------------------------------------------
function EditarFaturaForm({
  fatura,
  aoSalvar,
  aoCancelar,
}: {
  fatura: FaturaDetalhada;
  aoSalvar: (f: FaturaDetalhada) => void;
  aoCancelar: () => void;
}) {
  const [numeroNotaFiscal, setNumeroNotaFiscal] = useState(fatura.numero_nota_fiscal);
  const [serie, setSerie] = useState(fatura.serie ?? "");
  const [processo, setProcesso] = useState(fatura.numero_processo_sei ?? "");
  const [valorBruto, setValorBruto] = useState(formatarMoedaInicial(fatura.valor_bruto));
  const [dataVencimento, setDataVencimento] = useState(fatura.data_vencimento ?? "");
  const [dataEnvioGco, setDataEnvioGco] = useState(fatura.data_envio_gco ?? "");
  const [dataLiquidacao, setDataLiquidacao] = useState(fatura.data_liquidacao ?? "");
  const [observacoes, setObservacoes] = useState(fatura.observacoes ?? "");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setErro(null);
    setEnviando(true);
    try {
      aoSalvar(
        await apiFaturas.atualizar(fatura.id, {
          numero_nota_fiscal: numeroNotaFiscal,
          serie: serie || null,
          numero_processo_sei: processo || null,
          valor_bruto: moedaParaNumero(valorBruto),
          data_vencimento: dataVencimento || null,
          data_envio_gco: dataEnvioGco || null,
          data_liquidacao: dataLiquidacao || null,
          observacoes: observacoes || null,
        }),
      );
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível salvar.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="card space-y-3 p-5">
      <h2 className="text-sm font-semibold text-slate-900">Editar dados da fatura</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Nº da nota</label>
          <input className="field-input py-1.5" value={numeroNotaFiscal} onChange={(e) => setNumeroNotaFiscal(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Série</label>
          <input className="field-input py-1.5" value={serie} onChange={(e) => setSerie(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Processo da fatura</label>
          <input className="field-input py-1.5" value={processo} onChange={(e) => setProcesso(e.target.value)} />
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Valor da nota</label>
          <input
            className="field-input py-1.5"
            inputMode="numeric"
            value={valorBruto}
            onChange={(e) => setValorBruto(mascararMoeda(e.target.value))}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Vencimento</label>
          <input type="date" className="field-input py-1.5" value={dataVencimento} onChange={(e) => setDataVencimento(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Envio à GCO</label>
          <input type="date" className="field-input py-1.5" value={dataEnvioGco} onChange={(e) => setDataEnvioGco(e.target.value)} />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Liquidação</label>
          <input type="date" className="field-input py-1.5" value={dataLiquidacao} onChange={(e) => setDataLiquidacao(e.target.value)} />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Observações</label>
        <textarea className="field-input" rows={2} value={observacoes} onChange={(e) => setObservacoes(e.target.value)} />
      </div>
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button type="button" onClick={enviar} disabled={enviando} className="btn-primary btn-sm">
          {enviando ? "Salvando..." : "Salvar alterações"}
        </button>
        <button type="button" onClick={aoCancelar} className="btn-secondary btn-sm">
          Cancelar
        </button>
      </div>
    </section>
  );
}

// --------------------------------------------------------------------------
function ConferenciaForm({
  faturaId,
  aoRegistrar,
  aoCancelar,
}: {
  faturaId: string;
  aoRegistrar: (f: FaturaDetalhada) => void;
  aoCancelar: () => void;
}) {
  const [modelos, setModelos] = useState<ModeloChecklist[]>([]);
  const [modeloId, setModeloId] = useState("");
  const [itens, setItens] = useState<ItemConferenciaPayload[]>([]);
  const [observacoes, setObservacoes] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    apiModelosChecklist
      .listar(true)
      .then(setModelos)
      .catch(() => setModelos([]));
  }, []);

  function aplicarModelo(id: string) {
    setModeloId(id);
    const modelo = modelos.find((m) => m.id === id);
    setItens(
      (modelo?.itens ?? []).map((item, indice) => ({
        descricao: item.descricao,
        obrigatorio: item.obrigatorio,
        situacao: "conforme" as SituacaoItemConferencia,
        observacao: null,
        ordem: item.ordem ?? indice,
      })),
    );
  }

  async function enviar() {
    setErro(null);
    if (itens.length === 0) {
      setErro("Escolha um modelo de checklist para conferir.");
      return;
    }
    setEnviando(true);
    try {
      aoRegistrar(
        await apiFaturas.registrarConferencia(faturaId, {
          modelo_checklist_id: modeloId || null,
          itens,
          observacoes: observacoes || null,
        }),
      );
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível registrar a conferência.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mb-3 space-y-3 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
      <div>
        <label className="mb-1 block text-xs font-medium text-slate-600">Modelo de checklist</label>
        <select className="field-select py-1.5" value={modeloId} onChange={(e) => aplicarModelo(e.target.value)}>
          <option value="">Selecione o modelo...</option>
          {modelos.map((m) => (
            <option key={m.id} value={m.id}>
              {m.nome}
            </option>
          ))}
        </select>
        {modelos.length === 0 && (
          <p className="field-hint">
            Nenhum modelo cadastrado ainda — crie em Configuração → Modelos de checklist.
          </p>
        )}
      </div>

      {itens.map((item, indice) => (
        <div key={indice} className="grid grid-cols-[1fr_150px] items-center gap-2">
          <span className="text-sm text-slate-700">
            {item.descricao}
            {item.obrigatorio && <span className="text-red-500"> *</span>}
          </span>
          <select
            className="field-select py-1"
            value={item.situacao}
            onChange={(e) =>
              setItens((atual) =>
                atual.map((i, idx) =>
                  idx === indice ? { ...i, situacao: e.target.value as SituacaoItemConferencia } : i,
                ),
              )
            }
          >
            {(Object.keys(ROTULOS_SITUACAO_ITEM) as SituacaoItemConferencia[]).map((s) => (
              <option key={s} value={s}>
                {ROTULOS_SITUACAO_ITEM[s]}
              </option>
            ))}
          </select>
        </div>
      ))}

      {itens.length > 0 && (
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Observações</label>
          <input className="field-input py-1.5" value={observacoes} onChange={(e) => setObservacoes(e.target.value)} />
        </div>
      )}

      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button type="button" onClick={enviar} disabled={enviando} className="btn-primary btn-sm">
          {enviando ? "Registrando..." : "Registrar conferência"}
        </button>
        <button type="button" onClick={aoCancelar} className="btn-secondary btn-sm">
          Cancelar
        </button>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
function TributosForm({
  fatura,
  aoRegistrar,
  aoCancelar,
}: {
  fatura: FaturaDetalhada;
  aoRegistrar: (f: FaturaDetalhada) => void;
  aoCancelar: () => void;
}) {
  const [sugestoes, setSugestoes] = useState<RetencaoSugerida[] | null>(null);
  const [valores, setValores] = useState<Record<string, string>>({});
  const [observacoes, setObservacoes] = useState<Record<string, string>>({});
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    apiFaturas
      .sugerirRetencoes(fatura.id)
      .then((s) => {
        setSugestoes(s);
        // Já existe conferência? Traz o que foi informado antes; senão parte do
        // esperado, que é o caso comum quando a nota veio correta.
        const iniciais: Record<string, string> = {};
        const obs: Record<string, string> = {};
        for (const sugestao of s) {
          const anterior = fatura.retencoes.find((r) => r.tributo === sugestao.tributo);
          iniciais[sugestao.tributo] = formatarMoedaInicial(
            anterior ? anterior.valor_informado : sugestao.valor_esperado,
          );
          if (anterior?.observacao) obs[sugestao.tributo] = anterior.observacao;
        }
        setValores(iniciais);
        setObservacoes(obs);
      })
      .catch(() => setErro("Não foi possível calcular os impostos esperados."));
  }, [fatura.id]);

  async function enviar() {
    setErro(null);
    setEnviando(true);
    try {
      aoRegistrar(
        await apiFaturas.registrarRetencoes(
          fatura.id,
          (sugestoes ?? []).map((s) => ({
            tributo: s.tributo,
            valor_informado: moedaParaNumero(valores[s.tributo] ?? "0"),
            observacao: observacoes[s.tributo] || null,
          })),
        ),
      );
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível registrar a conferência.");
    } finally {
      setEnviando(false);
    }
  }

  if (sugestoes === null) return <p className="text-sm text-slate-500">Calculando...</p>;

  if (sugestoes.length === 0) {
    return (
      <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
        Não há regra tributária cadastrada com vigência na data de emissão desta nota. Cadastre em
        Configuração → Regras tributárias para o sistema poder conferir os impostos.
        <div className="mt-2">
          <button type="button" onClick={aoCancelar} className="btn-secondary btn-sm">
            Fechar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-3 space-y-3 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
      <p className="text-xs text-slate-500">
        O esperado é calculado pela regra vigente na data de emissão da nota. Informe o que veio na
        NF — divergência exige justificativa para a fatura seguir para o atesto.
      </p>
      {sugestoes.map((s) => {
        const informado = moedaParaNumero(valores[s.tributo] ?? "0");
        const divergente = Number(informado) !== Number(s.valor_esperado);
        return (
          <div key={s.tributo} className="grid grid-cols-1 gap-2 sm:grid-cols-[90px_1fr_1fr_1.4fr]">
            <span className="self-center text-sm font-medium text-slate-900">
              {ROTULOS_TRIBUTO[s.tributo as Tributo]}
            </span>
            <div>
              <label className="mb-1 block text-xs text-slate-500">
                Esperado ({Number(s.aliquota)}%)
              </label>
              <input className="field-input py-1.5" value={formatarMoeda(s.valor_esperado)} readOnly />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-500">Na nota</label>
              <input
                className="field-input py-1.5"
                inputMode="numeric"
                value={valores[s.tributo] ?? ""}
                onChange={(e) =>
                  setValores((atual) => ({ ...atual, [s.tributo]: mascararMoeda(e.target.value) }))
                }
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-500">
                {divergente ? "Justificativa (obrigatória)" : "Observação"}
              </label>
              <input
                className={`field-input py-1.5 ${divergente ? "border-red-300" : ""}`}
                value={observacoes[s.tributo] ?? ""}
                onChange={(e) =>
                  setObservacoes((atual) => ({ ...atual, [s.tributo]: e.target.value }))
                }
              />
            </div>
          </div>
        );
      })}
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button type="button" onClick={enviar} disabled={enviando} className="btn-primary btn-sm">
          {enviando ? "Salvando..." : "Salvar conferência"}
        </button>
        <button type="button" onClick={aoCancelar} className="btn-secondary btn-sm">
          Cancelar
        </button>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
function GlosaForm({
  faturaId,
  aoRegistrar,
  aoCancelar,
}: {
  faturaId: string;
  aoRegistrar: (f: FaturaDetalhada) => void;
  aoCancelar: () => void;
}) {
  const [valor, setValor] = useState("");
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setErro(null);
    if (!motivo.trim()) {
      setErro("Informe o motivo da glosa.");
      return;
    }
    setEnviando(true);
    try {
      aoRegistrar(
        await apiFaturas.registrarGlosa(faturaId, {
          valor: moedaParaNumero(valor),
          motivo,
        }),
      );
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível registrar a glosa.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mb-3 space-y-2 rounded-lg border border-slate-200 bg-slate-50/60 p-3">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[160px_1fr]">
        <div>
          <label className="mb-1 block text-xs text-slate-500">Valor</label>
          <input
            className="field-input py-1.5"
            inputMode="numeric"
            placeholder="0,00"
            value={valor}
            onChange={(e) => setValor(mascararMoeda(e.target.value))}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-slate-500">Motivo</label>
          <input
            className="field-input py-1.5"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            placeholder="ex.: posto não coberto em 2 dias"
          />
        </div>
      </div>
      {erro && <p className="text-sm text-red-600">{erro}</p>}
      <div className="flex gap-2">
        <button type="button" onClick={enviar} disabled={enviando} className="btn-primary btn-sm">
          {enviando ? "Registrando..." : "Registrar glosa"}
        </button>
        <button type="button" onClick={aoCancelar} className="btn-secondary btn-sm">
          Cancelar
        </button>
      </div>
    </div>
  );
}

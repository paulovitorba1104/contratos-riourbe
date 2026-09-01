import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiContratos, apiFornecedores, apiModelosRipm, apiUsuariosBasico } from "../../lib/apiContratos";
import type {
  ContratoDetalhado,
  Fornecedor,
  FundamentacaoLei,
  ModeloRipm,
  NivelAlerta,
  SubStatusInstrumento,
  TipoInstrumento,
  UsuarioBasico,
} from "../../lib/tiposContratos";
import {
  ROTULOS_FORMA_CONTRATACAO,
  ROTULOS_STATUS_CONTRATO,
  ROTULOS_SUB_STATUS,
  ROTULOS_TIPO_INSTRUMENTO,
  TIPOS_QUE_DEFINEM_VIGENCIA,
} from "../../lib/tiposContratos";

const campoClasse =
  "w-full rounded border border-institucional-200 px-2 py-1.5 text-sm focus:border-institucional-500 focus:outline-none";

function formatarMoeda(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const CORES_ALERTA: Record<NivelAlerta, string> = {
  "6_meses": "bg-amber-100 text-amber-800",
  "3_meses": "bg-orange-100 text-orange-800",
  "1_meses": "bg-red-100 text-red-800",
  vencido: "bg-red-200 text-red-900",
};

const ROTULOS_ALERTA: Record<NivelAlerta, string> = {
  "6_meses": "Vence em até 6 meses",
  "3_meses": "Vence em até 3 meses",
  "1_meses": "Vence em até 1 mês",
  vencido: "Vencido",
};

function BadgeAlerta({ alerta }: { alerta: NivelAlerta | null }) {
  if (!alerta) {
    return <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">Dentro do prazo</span>;
  }
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${CORES_ALERTA[alerta]}`}>{ROTULOS_ALERTA[alerta]}</span>
  );
}

const CORES_STATUS: Record<string, string> = {
  vigente: "bg-institucional-100 text-institucional-800",
  suspenso: "bg-amber-100 text-amber-800",
  encerrado: "bg-slate-200 text-slate-700",
};

function NovoInstrumentoForm({
  contratoId,
  modelos,
  aoCriar,
}: {
  contratoId: string;
  modelos: ModeloRipm[];
  aoCriar: (c: ContratoDetalhado) => void;
}) {
  const [tipo, setTipo] = useState<TipoInstrumento>("apostilamento");
  const [modeloRipmId, setModeloRipmId] = useState("");
  const [fundamentacaoLei, setFundamentacaoLei] = useState<FundamentacaoLei>("lei_13303_16");
  const [fundamentacaoArtigo, setFundamentacaoArtigo] = useState("");
  const [numeroDocumentoSei, setNumeroDocumentoSei] = useState("");
  const [dataInicioVigencia, setDataInicioVigencia] = useState("");
  const [dataFimVigencia, setDataFimVigencia] = useState("");
  const [valorDelta, setValorDelta] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const exigeVigencia = TIPOS_QUE_DEFINEM_VIGENCIA.includes(tipo);
  const exigeValor = tipo === "acrescimo_valor" || tipo === "supressao_valor";

  async function enviar() {
    setErro(null);
    if (!modeloRipmId) {
      setErro("Selecione um modelo RIPM.");
      return;
    }
    setEnviando(true);
    try {
      const contrato = await apiContratos.criarInstrumento(contratoId, {
        tipo,
        modelo_ripm_id: modeloRipmId,
        fundamentacao_lei: fundamentacaoLei,
        fundamentacao_artigo: fundamentacaoArtigo,
        numero_documento_sei: numeroDocumentoSei || null,
        data_inicio_vigencia: exigeVigencia ? dataInicioVigencia : null,
        data_fim_vigencia: exigeVigencia ? dataFimVigencia : null,
        valor_delta: exigeValor ? valorDelta : null,
        observacoes: observacoes || null,
      });
      aoCriar(contrato);
      setFundamentacaoArtigo("");
      setNumeroDocumentoSei("");
      setDataInicioVigencia("");
      setDataFimVigencia("");
      setValorDelta("");
      setObservacoes("");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível criar o instrumento.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="space-y-3 rounded border border-institucional-200 bg-institucional-50 p-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-institucional-800">Tipo</label>
          <select className={campoClasse} value={tipo} onChange={(e) => setTipo(e.target.value as TipoInstrumento)}>
            {Object.entries(ROTULOS_TIPO_INSTRUMENTO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-institucional-800">Modelo RIPM</label>
          <select className={campoClasse} value={modeloRipmId} onChange={(e) => setModeloRipmId(e.target.value)}>
            <option value="">Selecione...</option>
            {modelos.map((m) => (
              <option key={m.id} value={m.id}>
                {m.codigo} — {m.nome}
              </option>
            ))}
          </select>
          {modelos.length === 0 && (
            <p className="mt-1 text-xs text-red-600">
              Nenhum modelo RIPM cadastrado ainda — peça a um administrador para cadastrar em /modelos-ripm.
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-institucional-800">Fundamentação (lei)</label>
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
          <label className="mb-1 block text-xs font-medium text-institucional-800">Artigo</label>
          <input
            className={campoClasse}
            value={fundamentacaoArtigo}
            onChange={(e) => setFundamentacaoArtigo(e.target.value)}
            placeholder="ex.: art. 71"
          />
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-institucional-800">Nº documento SEI (opcional)</label>
        <input className={campoClasse} value={numeroDocumentoSei} onChange={(e) => setNumeroDocumentoSei(e.target.value)} />
      </div>

      {exigeVigencia && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-institucional-800" htmlFor="instrumento_data_inicio">
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
            <label className="mb-1 block text-xs font-medium text-institucional-800" htmlFor="instrumento_data_fim">
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
      )}

      {exigeValor && (
        <div>
          <label className="mb-1 block text-xs font-medium text-institucional-800">
            {tipo === "acrescimo_valor" ? "Valor do acréscimo (positivo)" : "Valor da supressão (negativo)"}
          </label>
          <input
            type="number"
            step="0.01"
            className={campoClasse}
            value={valorDelta}
            onChange={(e) => setValorDelta(e.target.value)}
            placeholder={tipo === "acrescimo_valor" ? "ex.: 10000.00" : "ex.: -5000.00"}
          />
        </div>
      )}

      <div>
        <label className="mb-1 block text-xs font-medium text-institucional-800">Observações</label>
        <textarea className={campoClasse} rows={2} value={observacoes} onChange={(e) => setObservacoes(e.target.value)} />
      </div>

      {erro && <p className="text-sm text-red-600">{erro}</p>}

      <button
        type="button"
        onClick={enviar}
        disabled={enviando}
        className="rounded bg-institucional-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-institucional-700 disabled:opacity-60"
      >
        {enviando ? "Registrando..." : "Registrar instrumento"}
      </button>
    </div>
  );
}

export function ContratoDetalhe() {
  const { id } = useParams<{ id: string }>();
  const [contrato, setContrato] = useState<ContratoDetalhado | null>(null);
  const [fornecedor, setFornecedor] = useState<Fornecedor | null>(null);
  const [usuarios, setUsuarios] = useState<UsuarioBasico[]>([]);
  const [modelos, setModelos] = useState<ModeloRipm[]>([]);
  const [mostrarFormInstrumento, setMostrarFormInstrumento] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const [valorPagoEdicao, setValorPagoEdicao] = useState("");
  const [garantiaInicioEdicao, setGarantiaInicioEdicao] = useState("");
  const [garantiaFimEdicao, setGarantiaFimEdicao] = useState("");

  function carregar() {
    if (!id) return;
    apiContratos
      .obter(id)
      .then((c) => {
        setContrato(c);
        setValorPagoEdicao(c.valor_pago);
        setGarantiaInicioEdicao(c.data_inicio_garantia ?? "");
        setGarantiaFimEdicao(c.data_fim_garantia ?? "");
      })
      .catch(() => setErro("Não foi possível carregar o contrato."));
  }

  useEffect(carregar, [id]);

  useEffect(() => {
    apiUsuariosBasico.listar().then(setUsuarios).catch(() => {});
    apiModelosRipm.listar().then(setModelos).catch(() => {});
  }, []);

  useEffect(() => {
    if (contrato) {
      apiFornecedores
        .listar()
        .then((lista) => setFornecedor(lista.find((f) => f.id === contrato.fornecedor_id) ?? null))
        .catch(() => {});
    }
  }, [contrato?.fornecedor_id]);

  async function salvarPagamento() {
    if (!id) return;
    try {
      const atualizado = await apiContratos.atualizarPagamento(id, valorPagoEdicao);
      setContrato(atualizado);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível atualizar o pagamento.");
    }
  }

  async function salvarGarantia() {
    if (!id) return;
    try {
      const atualizado = await apiContratos.atualizarGarantia(id, {
        data_inicio_garantia: garantiaInicioEdicao || null,
        data_fim_garantia: garantiaFimEdicao || null,
      });
      setContrato(atualizado);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível atualizar a garantia.");
    }
  }

  async function alterarSubStatus(instrumentoId: string, subStatus: SubStatusInstrumento) {
    if (!id) return;
    try {
      const atualizado = await apiContratos.atualizarSubStatusInstrumento(id, instrumentoId, subStatus);
      setContrato(atualizado);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível atualizar o sub-status.");
    }
  }

  function nomeFiscal(usuarioId: string): string {
    return usuarios.find((u) => u.id === usuarioId)?.nome ?? usuarioId;
  }

  if (erro && !contrato) {
    return <p className="p-6 text-sm text-red-600">{erro}</p>;
  }
  if (!contrato) {
    return <p className="p-6 text-sm text-institucional-700">Carregando...</p>;
  }

  return (
    <div className="min-h-screen bg-institucional-50 pb-16">
      <header className="border-b border-institucional-100 bg-white px-6 py-4">
        <Link to="/contratos" className="text-xs text-institucional-600 hover:underline">
          ← Contratos
        </Link>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-lg font-semibold text-institucional-900">{contrato.tipo_servico}</h1>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CORES_STATUS[contrato.status]}`}>
            {ROTULOS_STATUS_CONTRATO[contrato.status]}
          </span>
        </div>
        <p className="text-sm text-institucional-700">
          {contrato.processo_sei} · {fornecedor?.razao_social ?? "..."} ·{" "}
          {ROTULOS_FORMA_CONTRATACAO[contrato.forma_contratacao]}
        </p>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 p-6">
        {erro && <p className="text-sm text-red-600">{erro}</p>}

        <section className="rounded-lg bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-institucional-900">Objeto</h2>
          <p className="text-sm text-institucional-700">{contrato.objeto}</p>
        </section>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-lg bg-white p-5 shadow-sm">
            <h2 className="mb-2 text-sm font-semibold text-institucional-900">Vigência atual</h2>
            {contrato.vigencia_inicio && contrato.vigencia_fim ? (
              <p className="text-sm text-institucional-700">
                {contrato.vigencia_inicio} até {contrato.vigencia_fim}
              </p>
            ) : (
              <p className="text-sm text-institucional-500">Sem instrumento de origem registrado ainda.</p>
            )}
            <p className="mt-1 text-xs text-institucional-600">Teto (5 anos): {contrato.teto_vigencia}</p>
            <div className="mt-2">
              <BadgeAlerta alerta={contrato.alerta_vigencia} />
            </div>
          </div>

          <div className="rounded-lg bg-white p-5 shadow-sm">
            <h2 className="mb-2 text-sm font-semibold text-institucional-900">Garantia contratual</h2>
            <div className="flex gap-2">
              <input
                id="garantia_data_inicio"
                type="date"
                className={campoClasse}
                value={garantiaInicioEdicao}
                onChange={(e) => setGarantiaInicioEdicao(e.target.value)}
              />
              <input
                id="garantia_data_fim"
                type="date"
                className={campoClasse}
                value={garantiaFimEdicao}
                onChange={(e) => setGarantiaFimEdicao(e.target.value)}
              />
            </div>
            <button
              onClick={salvarGarantia}
              className="mt-2 rounded border border-institucional-300 px-2 py-1 text-xs text-institucional-700 hover:bg-institucional-100"
            >
              Salvar garantia
            </button>
            <div className="mt-2">
              <BadgeAlerta alerta={contrato.alerta_garantia} />
            </div>
          </div>
        </section>

        <section className="rounded-lg bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-institucional-900">Financeiro</h2>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <p className="text-xs text-institucional-500">Valor inicial</p>
              <p className="font-medium text-institucional-900">{formatarMoeda(contrato.valor_inicial)}</p>
            </div>
            <div>
              <p className="text-xs text-institucional-500">Valor atualizado</p>
              <p className="font-medium text-institucional-900">{formatarMoeda(contrato.valor_atualizado)}</p>
            </div>
            <div>
              <p className="text-xs text-institucional-500">Valor pago</p>
              <p className="font-medium text-institucional-900">{formatarMoeda(contrato.valor_pago)}</p>
            </div>
            <div>
              <p className="text-xs text-institucional-500">Saldo a pagar</p>
              <p className="font-medium text-institucional-900">{formatarMoeda(contrato.saldo_a_pagar)}</p>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <input
              type="number"
              step="0.01"
              className={campoClasse}
              value={valorPagoEdicao}
              onChange={(e) => setValorPagoEdicao(e.target.value)}
            />
            <button
              onClick={salvarPagamento}
              className="whitespace-nowrap rounded border border-institucional-300 px-2 py-1 text-xs text-institucional-700 hover:bg-institucional-100"
            >
              Atualizar valor pago
            </button>
          </div>
        </section>

        <section className="rounded-lg bg-white p-5 shadow-sm">
          <h2 className="mb-2 text-sm font-semibold text-institucional-900">Fiscal(is) do contrato</h2>
          <ul className="text-sm text-institucional-700">
            {contrato.fiscais_ids.map((fid) => (
              <li key={fid}>{nomeFiscal(fid)}</li>
            ))}
          </ul>
        </section>

        <section className="rounded-lg bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-institucional-900">Instrumentos processuais</h2>
            {contrato.status !== "encerrado" && (
              <button
                onClick={() => setMostrarFormInstrumento((v) => !v)}
                className="rounded bg-institucional-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-institucional-700"
              >
                {mostrarFormInstrumento ? "Cancelar" : "+ Novo instrumento"}
              </button>
            )}
          </div>

          {mostrarFormInstrumento && (
            <div className="mb-4">
              <NovoInstrumentoForm
                contratoId={contrato.id}
                modelos={modelos}
                aoCriar={(c) => {
                  setContrato(c);
                  setMostrarFormInstrumento(false);
                }}
              />
            </div>
          )}

          <div className="space-y-2">
            {contrato.instrumentos.length === 0 && (
              <p className="text-sm text-institucional-500">Nenhum instrumento registrado ainda.</p>
            )}
            {contrato.instrumentos.map((i) => (
              <div key={i.id} className="rounded border border-institucional-100 p-3 text-sm">
                <div className="flex items-center justify-between">
                  <p className="font-medium text-institucional-900">{ROTULOS_TIPO_INSTRUMENTO[i.tipo]}</p>
                  <select
                    className="rounded border border-institucional-200 px-2 py-1 text-xs"
                    value={i.sub_status}
                    onChange={(e) => alterarSubStatus(i.id, e.target.value as SubStatusInstrumento)}
                  >
                    {Object.entries(ROTULOS_SUB_STATUS).map(([valor, rotulo]) => (
                      <option key={valor} value={valor}>
                        {rotulo}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="text-xs text-institucional-600">
                  {i.fundamentacao_lei === "lei_13303_16" ? "Lei 13.303/16" : "Lei 14.133/21"}, {i.fundamentacao_artigo}
                </p>
                {i.data_inicio_vigencia && i.data_fim_vigencia && (
                  <p className="text-xs text-institucional-600">
                    Vigência: {i.data_inicio_vigencia} até {i.data_fim_vigencia}
                  </p>
                )}
                {i.valor_delta && (
                  <p className="text-xs text-institucional-600">Valor: {formatarMoeda(i.valor_delta)}</p>
                )}
                {i.observacoes && <p className="mt-1 text-xs text-institucional-500">{i.observacoes}</p>}
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

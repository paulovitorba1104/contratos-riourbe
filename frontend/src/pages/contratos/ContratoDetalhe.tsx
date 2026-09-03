import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { BadgeAlerta } from "../../components/BadgeAlerta";
import { ErroApi } from "../../lib/api";
import { apiContratos, apiFiscais, apiFornecedores } from "../../lib/apiContratos";
import { useAuth } from "../../lib/AuthContext";
import { formatarMoedaInicial, mascararMatricula, mascararMoeda, moedaParaNumero } from "../../lib/mascaras";
import type {
  ContratoDetalhado,
  Fiscal,
  FormaContratacao,
  Fornecedor,
  FundamentacaoLei,
  Processo,
  SistemaProcesso,
  SubStatusInstrumento,
  TipoInstrumento,
  TipoProcesso,
} from "../../lib/tiposContratos";
import {
  ROTULOS_FORMA_CONTRATACAO,
  ROTULOS_SISTEMA_PROCESSO,
  ROTULOS_STATUS_CONTRATO,
  ROTULOS_SUB_STATUS,
  ROTULOS_TIPO_INSTRUMENTO,
  ROTULOS_TIPO_PROCESSO,
  TIPOS_QUE_DEFINEM_VIGENCIA,
} from "../../lib/tiposContratos";
import { useToast } from "../../lib/ToastContext";

const campoClasse = "field-input py-1.5";

function formatarMoeda(valor: string): string {
  return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
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
  aoCriar,
}: {
  contratoId: string;
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
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const exigeVigencia = TIPOS_QUE_DEFINEM_VIGENCIA.includes(tipo);
  const exigeValor = tipo === "acrescimo_valor" || tipo === "supressao_valor";

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
        valor_delta: exigeValor ? moedaParaNumero(valorDelta) : null,
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
        <div className="grid grid-cols-2 gap-3">
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
      )}

      {exigeValor && (
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
  const [valorPago, setValorPago] = useState(formatarMoedaInicial(contrato.valor_pago));
  const [notaReserva, setNotaReserva] = useState(contrato.nota_reserva ?? "");
  const [notaEmpenho, setNotaEmpenho] = useState(contrato.nota_empenho ?? "");
  const [pt, setPt] = useState(contrato.pt ?? "");
  const [nd, setNd] = useState(contrato.nd ?? "");
  const [fr, setFr] = useState(contrato.fr ?? "");
  const [tipoPatrimonial, setTipoPatrimonial] = useState(contrato.tipo_patrimonial ?? "");
  const [itemPatrimonial, setItemPatrimonial] = useState(contrato.item_patrimonial ?? "");
  const [codigoCcon, setCodigoCcon] = useState(contrato.codigo_ccon ?? "");
  const [observacoes, setObservacoes] = useState(contrato.observacoes ?? "");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    setErro(null);
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
        valor_pago: moedaParaNumero(valorPago),
        nota_reserva: notaReserva || null,
        nota_empenho: notaEmpenho || null,
        pt: pt || null,
        nd: nd || null,
        fr: fr || null,
        tipo_patrimonial: tipoPatrimonial || null,
        item_patrimonial: itemPatrimonial || null,
        codigo_ccon: codigoCcon || null,
        observacoes: observacoes || null,
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

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
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
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600">Valor pago</label>
          <input
            type="text"
            inputMode="numeric"
            placeholder="0,00"
            className={campoClasse}
            value={valorPago}
            onChange={(e) => setValorPago(mascararMoeda(e.target.value))}
          />
        </div>
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
  const [erro, setErro] = useState<string | null>(null);
  const { mostrarToast } = useToast();

  const [valorPagoEdicao, setValorPagoEdicao] = useState("");

  function carregar() {
    if (!id) return;
    apiContratos
      .obter(id)
      .then((c) => {
        setContrato(c);
        setValorPagoEdicao(formatarMoedaInicial(c.valor_pago));
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

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="card p-5">
            <h2 className="mb-2 text-sm font-semibold text-slate-900">Vigência atual</h2>
            {contrato.vigencia_inicio && contrato.vigencia_fim ? (
              <p className="text-sm text-slate-600">
                {contrato.vigencia_inicio} até {contrato.vigencia_fim}
              </p>
            ) : (
              <p className="text-sm text-slate-500">Sem instrumento de origem registrado ainda.</p>
            )}
            <p className="mt-1 text-xs text-slate-500">Teto (5 anos): {contrato.teto_vigencia}</p>
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
          <div className="mt-3 flex gap-2">
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
              Atualizar valor pago
            </button>
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
                aoCriar={(c) => {
                  setContrato(c);
                  setMostrarFormInstrumento(false);
                  mostrarToast("Instrumento registrado com sucesso.");
                }}
              />
            </div>
          )}

          <div className="space-y-2">
            {contrato.instrumentos.length === 0 && (
              <p className="text-sm text-slate-500">Nenhum instrumento registrado ainda.</p>
            )}
            {contrato.instrumentos.map((i) => (
              <div key={i.id} className="rounded-lg border border-slate-200 p-3 text-sm">
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
                {i.observacoes && <p className="mt-1 text-xs text-slate-500">{i.observacoes}</p>}
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

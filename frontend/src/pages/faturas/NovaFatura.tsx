import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiContratos } from "../../lib/apiContratos";
import { apiFaturas, apiMedicoes } from "../../lib/apiFaturas";
import { mascararMoeda, moedaParaNumero } from "../../lib/mascaras";
import type { Contrato } from "../../lib/tiposContratos";
import type { Medicao } from "../../lib/tiposFaturas";
import { useToast } from "../../lib/ToastContext";

export function NovaFatura() {
  const navegar = useNavigate();
  const { mostrarToast } = useToast();
  const [parametros] = useSearchParams();

  const [contratos, setContratos] = useState<Contrato[]>([]);
  const [medicoes, setMedicoes] = useState<Medicao[]>([]);

  const [contratoId, setContratoId] = useState(parametros.get("contrato") ?? "");
  const [medicaoId, setMedicaoId] = useState("");
  const [numeroNotaFiscal, setNumeroNotaFiscal] = useState("");
  const [serie, setSerie] = useState("");
  const [numeroProcessoSei, setNumeroProcessoSei] = useState("");
  const [competencia, setCompetencia] = useState("");
  const [dataEmissao, setDataEmissao] = useState("");
  const [dataRecebimento, setDataRecebimento] = useState("");
  const [valorBruto, setValorBruto] = useState("");
  const [dataVencimento, setDataVencimento] = useState("");
  const [observacoes, setObservacoes] = useState("");

  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    apiContratos
      .listar()
      .then(setContratos)
      .catch(() => setErro("Não foi possível carregar os contratos."));
  }, []);

  // Só as medições aprovadas e ainda não usadas por outra nota entram na lista.
  useEffect(() => {
    if (!contratoId) {
      setMedicoes([]);
      return;
    }
    apiMedicoes
      .listar({ contrato_id: contratoId, apenas_disponiveis: true })
      .then(setMedicoes)
      .catch(() => setMedicoes([]));
  }, [contratoId]);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    if (!contratoId) {
      setErro("Selecione o contrato de origem da fatura.");
      return;
    }
    setEnviando(true);
    try {
      const fatura = await apiFaturas.criar({
        contrato_id: contratoId,
        medicao_id: medicaoId || null,
        numero_nota_fiscal: numeroNotaFiscal,
        serie: serie || null,
        numero_processo_sei: numeroProcessoSei || null,
        competencia,
        data_emissao: dataEmissao,
        data_recebimento: dataRecebimento,
        valor_bruto: moedaParaNumero(valorBruto),
        data_vencimento: dataVencimento || null,
        observacoes: observacoes || null,
      });
      mostrarToast("Fatura registrada com sucesso.");
      navegar(`/faturas/${fatura.id}`);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível registrar a fatura.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <Link to="/faturas" className="text-xs font-medium text-institucional-600 hover:underline">
            ← Faturas
          </Link>
          <h1 className="page-title mt-0.5">Nova fatura</h1>
        </div>
      </header>

      <main className="mx-auto max-w-2xl p-6">
        <form onSubmit={aoEnviar} className="card space-y-5 p-6">
          <div>
            <label className="field-label" htmlFor="contrato">
              Contrato
            </label>
            <select
              id="contrato"
              className="field-select"
              value={contratoId}
              onChange={(e) => {
                setContratoId(e.target.value);
                setMedicaoId("");
              }}
              required
            >
              <option value="">Selecione...</option>
              {contratos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.numero_contrato} — {c.tipo_servico}
                </option>
              ))}
            </select>
          </div>

          {medicoes.length > 0 && (
            <div>
              <label className="field-label" htmlFor="medicao">
                Medição de origem
              </label>
              <select
                id="medicao"
                className="field-select"
                value={medicaoId}
                onChange={(e) => setMedicaoId(e.target.value)}
              >
                <option value="">Sem medição vinculada</option>
                {medicoes.map((m) => (
                  <option key={m.id} value={m.id}>
                    Medição {m.numero_medicao} — {m.competencia} — R${" "}
                    {Number(m.valor_medido).toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                  </option>
                ))}
              </select>
              <p className="field-hint">
                Apenas medições aprovadas e ainda não usadas por outra fatura aparecem aqui.
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="field-label" htmlFor="numero_nota_fiscal">
                Nº da nota fiscal
              </label>
              <input
                id="numero_nota_fiscal"
                className="field-input"
                value={numeroNotaFiscal}
                onChange={(e) => setNumeroNotaFiscal(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="serie">
                Série
              </label>
              <input
                id="serie"
                className="field-input"
                value={serie}
                onChange={(e) => setSerie(e.target.value)}
              />
            </div>
            <div>
              <label className="field-label" htmlFor="competencia">
                Competência
              </label>
              <input
                id="competencia"
                type="month"
                className="field-input"
                value={competencia}
                onChange={(e) => setCompetencia(e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="field-label" htmlFor="numero_processo_sei">
              Nº do processo da fatura
            </label>
            <input
              id="numero_processo_sei"
              className="field-input"
              value={numeroProcessoSei}
              onChange={(e) => setNumeroProcessoSei(e.target.value)}
              placeholder="ex.: 006700.000249/2026-51"
            />
            <p className="field-hint">
              É o processo em que a fatura tramita — não o processo do contrato.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="data_emissao">
                Data de emissão
              </label>
              <input
                id="data_emissao"
                type="date"
                className="field-input"
                value={dataEmissao}
                onChange={(e) => setDataEmissao(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="data_recebimento">
                Data de recebimento
              </label>
              <input
                id="data_recebimento"
                type="date"
                className="field-input"
                value={dataRecebimento}
                onChange={(e) => setDataRecebimento(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="valor_bruto">
                Valor da fatura (R$)
              </label>
              <input
                id="valor_bruto"
                type="text"
                inputMode="numeric"
                placeholder="0,00"
                className="field-input"
                value={valorBruto}
                onChange={(e) => setValorBruto(mascararMoeda(e.target.value))}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="data_vencimento">
                Vencimento
              </label>
              <input
                id="data_vencimento"
                type="date"
                className="field-input"
                value={dataVencimento}
                onChange={(e) => setDataVencimento(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="field-label" htmlFor="observacoes">
              Observações
            </label>
            <textarea
              id="observacoes"
              className="field-input"
              rows={2}
              value={observacoes}
              onChange={(e) => setObservacoes(e.target.value)}
            />
          </div>

          {erro && <p className="text-sm text-red-600">{erro}</p>}

          <button type="submit" disabled={enviando} className="btn-primary w-full py-2.5">
            {enviando ? "Registrando..." : "Registrar fatura"}
          </button>
        </form>
      </main>
    </div>
  );
}

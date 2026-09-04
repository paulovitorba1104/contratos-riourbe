import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiContratos } from "../../lib/apiContratos";
import { apiMedicoes } from "../../lib/apiFaturas";
import { useAuth } from "../../lib/AuthContext";
import { mascararMoeda, moedaParaNumero } from "../../lib/mascaras";
import type { Contrato } from "../../lib/tiposContratos";
import type { Medicao } from "../../lib/tiposFaturas";
import { ROTULOS_STATUS_MEDICAO } from "../../lib/tiposFaturas";
import { useToast } from "../../lib/ToastContext";
import { formatarMoeda } from "./FaturasKanban";

const CORES_STATUS: Record<string, string> = {
  em_elaboracao: "bg-slate-200 text-slate-700",
  aprovada: "bg-emerald-100 text-emerald-800",
  rejeitada: "bg-red-100 text-red-800",
};

export function Medicoes() {
  const { mostrarToast } = useToast();
  const { usuario } = useAuth();
  const ehAdministrador = usuario?.papel === "administrador";

  const [medicoes, setMedicoes] = useState<Medicao[]>([]);
  const [contratos, setContratos] = useState<Contrato[]>([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const [contratoId, setContratoId] = useState("");
  const [numeroMedicao, setNumeroMedicao] = useState("");
  const [competencia, setCompetencia] = useState("");
  const [periodoInicio, setPeriodoInicio] = useState("");
  const [periodoFim, setPeriodoFim] = useState("");
  const [valorMedido, setValorMedido] = useState("");
  const [observacoes, setObservacoes] = useState("");

  function carregar() {
    apiMedicoes
      .listar()
      .then(setMedicoes)
      .catch(() => setErro("Não foi possível carregar as medições."));
  }

  useEffect(() => {
    carregar();
    apiContratos
      .listar()
      .then(setContratos)
      .catch(() => setContratos([]));
  }, []);

  const nomeContrato = (id: string) =>
    contratos.find((c) => c.id === id)?.numero_contrato ?? "—";

  async function criar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await apiMedicoes.criar({
        contrato_id: contratoId,
        numero_medicao: numeroMedicao,
        competencia,
        periodo_inicio: periodoInicio,
        periodo_fim: periodoFim,
        valor_medido: moedaParaNumero(valorMedido),
        observacoes: observacoes || null,
      });
      setMostrarForm(false);
      setNumeroMedicao("");
      setValorMedido("");
      setObservacoes("");
      carregar();
      mostrarToast("Medição registrada.");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível registrar a medição.");
    }
  }

  async function acao(promessa: Promise<unknown>, mensagem: string) {
    try {
      await promessa;
      carregar();
      mostrarToast(mensagem);
    } catch (e) {
      mostrarToast(e instanceof ErroApi ? e.message : "Não foi possível concluir a ação.", "erro");
    }
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <Link to="/faturas" className="text-xs font-medium text-institucional-600 hover:underline">
            ← Faturas
          </Link>
          <h1 className="page-title mt-0.5">Medições</h1>
        </div>
        <button onClick={() => setMostrarForm((v) => !v)} className="btn-primary btn-sm">
          {mostrarForm ? "Cancelar" : "+ Nova medição"}
        </button>
      </header>

      <main className="mx-auto max-w-4xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        <p className="mb-4 text-sm text-slate-500">
          O boletim de medição é a etapa que antecede a nota nas obras e serviços continuados. Só
          medições aprovadas ficam disponíveis para vincular a uma fatura.
        </p>

        {mostrarForm && (
          <form onSubmit={criar} className="card mb-6 space-y-3 p-5">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="field-label">Contrato</label>
                <select
                  className="field-select"
                  value={contratoId}
                  onChange={(e) => setContratoId(e.target.value)}
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
              <div>
                <label className="field-label">Nº da medição</label>
                <input
                  className="field-input"
                  value={numeroMedicao}
                  onChange={(e) => setNumeroMedicao(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
              <div>
                <label className="field-label">Competência</label>
                <input
                  type="month"
                  className="field-input"
                  value={competencia}
                  onChange={(e) => setCompetencia(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="field-label">Início do período</label>
                <input
                  type="date"
                  className="field-input"
                  value={periodoInicio}
                  onChange={(e) => setPeriodoInicio(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="field-label">Fim do período</label>
                <input
                  type="date"
                  className="field-input"
                  value={periodoFim}
                  onChange={(e) => setPeriodoFim(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="field-label">Valor medido</label>
                <input
                  className="field-input"
                  inputMode="numeric"
                  placeholder="0,00"
                  value={valorMedido}
                  onChange={(e) => setValorMedido(mascararMoeda(e.target.value))}
                  required
                />
              </div>
            </div>
            <div>
              <label className="field-label">Observações</label>
              <input
                className="field-input"
                value={observacoes}
                onChange={(e) => setObservacoes(e.target.value)}
              />
            </div>
            <button type="submit" className="btn-primary btn-sm">
              Registrar medição
            </button>
          </form>
        )}

        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs text-slate-500">
              <tr>
                <th className="px-4 py-2">Contrato</th>
                <th className="px-4 py-2">Medição</th>
                <th className="px-4 py-2">Competência</th>
                <th className="px-4 py-2">Período</th>
                <th className="px-4 py-2">Valor</th>
                <th className="px-4 py-2">Situação</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {medicoes.map((m) => (
                <tr key={m.id} className="border-t border-slate-200">
                  <td className="px-4 py-2 text-slate-900">{nomeContrato(m.contrato_id)}</td>
                  <td className="px-4 py-2 text-slate-600">{m.numero_medicao}</td>
                  <td className="px-4 py-2 text-slate-600">{m.competencia}</td>
                  <td className="px-4 py-2 text-xs text-slate-500">
                    {m.periodo_inicio} a {m.periodo_fim}
                  </td>
                  <td className="px-4 py-2 tabular-nums text-slate-900">
                    {formatarMoeda(m.valor_medido)}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${CORES_STATUS[m.status]}`}>
                      {ROTULOS_STATUS_MEDICAO[m.status]}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right">
                    {m.status !== "aprovada" && (
                      <button
                        onClick={() => acao(apiMedicoes.aprovar(m.id), "Medição aprovada.")}
                        className="btn-secondary btn-sm mr-2"
                      >
                        Aprovar
                      </button>
                    )}
                    {m.status === "aprovada" && (
                      <button
                        onClick={() => acao(apiMedicoes.rejeitar(m.id), "Medição rejeitada.")}
                        className="btn-secondary btn-sm mr-2"
                      >
                        Rejeitar
                      </button>
                    )}
                    {ehAdministrador && (
                      <button
                        onClick={() => acao(apiMedicoes.excluir(m.id), "Medição excluída.")}
                        className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                      >
                        Excluir
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {medicoes.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-3 text-center text-slate-500">
                    Nenhuma medição registrada ainda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}

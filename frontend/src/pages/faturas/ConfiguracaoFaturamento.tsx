import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiModelosChecklist, apiRegrasTributarias } from "../../lib/apiFaturas";
import { useAuth } from "../../lib/AuthContext";
import type { ModeloChecklist, RegraTributaria, Tributo } from "../../lib/tiposFaturas";
import { ROTULOS_TRIBUTO } from "../../lib/tiposFaturas";
import { useToast } from "../../lib/ToastContext";

export function ConfiguracaoFaturamento() {
  const { usuario } = useAuth();
  const ehAdministrador = usuario?.papel === "administrador";
  const { mostrarToast } = useToast();

  const [regras, setRegras] = useState<RegraTributaria[]>([]);
  const [modelos, setModelos] = useState<ModeloChecklist[]>([]);
  const [erro, setErro] = useState<string | null>(null);

  const [mostrarFormRegra, setMostrarFormRegra] = useState(false);
  const [tributo, setTributo] = useState<Tributo>("iss");
  const [descricao, setDescricao] = useState("");
  const [baseLegal, setBaseLegal] = useState("");
  const [aliquota, setAliquota] = useState("");
  const [percentualBase, setPercentualBase] = useState("100");
  const [vigenciaInicio, setVigenciaInicio] = useState("");
  const [vigenciaFim, setVigenciaFim] = useState("");

  const [mostrarFormModelo, setMostrarFormModelo] = useState(false);
  const [nomeModelo, setNomeModelo] = useState("");
  const [descricaoModelo, setDescricaoModelo] = useState("");
  const [itens, setItens] = useState([{ descricao: "", obrigatorio: true }]);

  function carregar() {
    apiRegrasTributarias
      .listar()
      .then(setRegras)
      .catch(() => setErro("Não foi possível carregar as regras tributárias."));
    apiModelosChecklist
      .listar(false)
      .then(setModelos)
      .catch(() => setModelos([]));
  }

  useEffect(carregar, []);

  async function criarRegra(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await apiRegrasTributarias.criar({
        tributo,
        descricao,
        base_legal: baseLegal || null,
        aliquota,
        percentual_base: percentualBase,
        vigencia_inicio: vigenciaInicio,
        vigencia_fim: vigenciaFim || null,
      });
      setMostrarFormRegra(false);
      setDescricao("");
      setBaseLegal("");
      setAliquota("");
      carregar();
      mostrarToast("Regra tributária cadastrada.");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível cadastrar a regra.");
    }
  }

  async function criarModelo(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    const validos = itens.filter((i) => i.descricao.trim());
    if (validos.length === 0) {
      setErro("Adicione ao menos um item ao checklist.");
      return;
    }
    try {
      await apiModelosChecklist.criar({
        nome: nomeModelo,
        descricao: descricaoModelo || null,
        itens: validos.map((item, indice) => ({ ...item, ordem: indice })),
      });
      setMostrarFormModelo(false);
      setNomeModelo("");
      setDescricaoModelo("");
      setItens([{ descricao: "", obrigatorio: true }]);
      carregar();
      mostrarToast("Modelo de checklist cadastrado.");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível cadastrar o modelo.");
    }
  }

  async function remover(promessa: Promise<unknown>, mensagem: string) {
    try {
      await promessa;
      carregar();
      mostrarToast(mensagem);
    } catch (e) {
      mostrarToast(e instanceof ErroApi ? e.message : "Não foi possível excluir.", "erro");
    }
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <Link to="/faturas" className="text-xs font-medium text-institucional-600 hover:underline">
            ← Faturas
          </Link>
          <h1 className="page-title mt-0.5">Configuração do faturamento</h1>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-8 p-6">
        {erro && <p className="text-sm text-red-600">{erro}</p>}

        {/* Regras tributárias */}
        <section>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Regras tributárias</h2>
            {ehAdministrador && (
              <button onClick={() => setMostrarFormRegra((v) => !v)} className="btn-primary btn-sm">
                {mostrarFormRegra ? "Cancelar" : "+ Nova regra"}
              </button>
            )}
          </div>
          <p className="mb-4 text-sm text-slate-500">
            São estes parâmetros que a conferência tributária aplica para calcular o valor esperado
            de cada imposto. A vigência garante que uma nota antiga seja conferida pela regra que
            valia na época dela — quando a legislação muda, cadastre uma nova regra em vez de editar
            a antiga.
          </p>

          {mostrarFormRegra && (
            <form onSubmit={criarRegra} className="card mb-4 space-y-3 p-5">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div>
                  <label className="field-label">Tributo</label>
                  <select
                    className="field-select"
                    value={tributo}
                    onChange={(e) => setTributo(e.target.value as Tributo)}
                  >
                    {(Object.keys(ROTULOS_TRIBUTO) as Tributo[]).map((t) => (
                      <option key={t} value={t}>
                        {ROTULOS_TRIBUTO[t]}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="field-label">Alíquota (%)</label>
                  <input
                    className="field-input"
                    inputMode="decimal"
                    placeholder="ex.: 5"
                    value={aliquota}
                    onChange={(e) => setAliquota(e.target.value.replace(",", "."))}
                    required
                  />
                </div>
                <div>
                  <label className="field-label">Base de cálculo (% do bruto)</label>
                  <input
                    className="field-input"
                    inputMode="decimal"
                    value={percentualBase}
                    onChange={(e) => setPercentualBase(e.target.value.replace(",", "."))}
                    required
                  />
                </div>
              </div>
              <div>
                <label className="field-label">Descrição</label>
                <input
                  className="field-input"
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  placeholder="ex.: ISS sobre serviços de limpeza"
                  required
                />
              </div>
              <div>
                <label className="field-label">Base legal</label>
                <input
                  className="field-input"
                  value={baseLegal}
                  onChange={(e) => setBaseLegal(e.target.value)}
                  placeholder="lei, artigo ou instrução normativa que fundamenta"
                />
              </div>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="field-label">Início da vigência</label>
                  <input
                    type="date"
                    className="field-input"
                    value={vigenciaInicio}
                    onChange={(e) => setVigenciaInicio(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className="field-label">Fim da vigência (opcional)</label>
                  <input
                    type="date"
                    className="field-input"
                    value={vigenciaFim}
                    onChange={(e) => setVigenciaFim(e.target.value)}
                  />
                </div>
              </div>
              <button type="submit" className="btn-primary btn-sm">
                Cadastrar regra
              </button>
            </form>
          )}

          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-500">
                <tr>
                  <th className="px-4 py-2">Tributo</th>
                  <th className="px-4 py-2">Descrição</th>
                  <th className="px-4 py-2">Alíquota</th>
                  <th className="px-4 py-2">Base</th>
                  <th className="px-4 py-2">Vigência</th>
                  <th className="px-4 py-2">Base legal</th>
                  <th className="px-4 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {regras.map((r) => (
                  <tr key={r.id} className="border-t border-slate-200">
                    <td className="px-4 py-2 font-medium text-slate-900">{ROTULOS_TRIBUTO[r.tributo]}</td>
                    <td className="px-4 py-2 text-slate-600">{r.descricao}</td>
                    <td className="px-4 py-2 tabular-nums text-slate-900">{Number(r.aliquota)}%</td>
                    <td className="px-4 py-2 tabular-nums text-slate-600">
                      {Number(r.percentual_base)}%
                    </td>
                    <td className="px-4 py-2 text-xs text-slate-500">
                      {r.vigencia_inicio} → {r.vigencia_fim ?? "vigente"}
                    </td>
                    <td className="px-4 py-2 text-xs text-slate-500">{r.base_legal ?? "—"}</td>
                    <td className="px-4 py-2 text-right">
                      {ehAdministrador && (
                        <button
                          onClick={() =>
                            remover(apiRegrasTributarias.excluir(r.id), "Regra excluída.")
                          }
                          className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                        >
                          Excluir
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {regras.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-4 text-center text-slate-500">
                      Nenhuma regra cadastrada. Sem regra, a conferência tributária não tem como
                      calcular o valor esperado.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* Modelos de checklist */}
        <section>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-900">Modelos de checklist</h2>
            {ehAdministrador && (
              <button onClick={() => setMostrarFormModelo((v) => !v)} className="btn-primary btn-sm">
                {mostrarFormModelo ? "Cancelar" : "+ Novo modelo"}
              </button>
            )}
          </div>
          <p className="mb-4 text-sm text-slate-500">
            A lista de documentos e passos a conferir em cada fatura. Item marcado como obrigatório
            trava o atesto enquanto estiver não conforme.
          </p>

          {mostrarFormModelo && (
            <form onSubmit={criarModelo} className="card mb-4 space-y-3 p-5">
              <div>
                <label className="field-label">Nome do modelo</label>
                <input
                  className="field-input"
                  value={nomeModelo}
                  onChange={(e) => setNomeModelo(e.target.value)}
                  placeholder="ex.: Serviço continuado com mão de obra"
                  required
                />
              </div>
              <div>
                <label className="field-label">Descrição</label>
                <input
                  className="field-input"
                  value={descricaoModelo}
                  onChange={(e) => setDescricaoModelo(e.target.value)}
                />
              </div>

              <div>
                <div className="mb-1 flex items-center justify-between">
                  <span className="field-label mb-0">Itens do checklist</span>
                  <button
                    type="button"
                    onClick={() => setItens((a) => [...a, { descricao: "", obrigatorio: true }])}
                    className="btn-ghost btn-sm"
                  >
                    + Adicionar item
                  </button>
                </div>
                <div className="space-y-2">
                  {itens.map((item, indice) => (
                    <div key={indice} className="grid grid-cols-[1fr_auto_auto] items-center gap-2">
                      <input
                        className="field-input py-1.5"
                        placeholder="ex.: Certidão negativa de débitos trabalhistas"
                        value={item.descricao}
                        onChange={(e) =>
                          setItens((a) =>
                            a.map((i, idx) => (idx === indice ? { ...i, descricao: e.target.value } : i)),
                          )
                        }
                      />
                      <label className="flex items-center gap-1.5 whitespace-nowrap text-xs text-slate-600">
                        <input
                          type="checkbox"
                          checked={item.obrigatorio}
                          onChange={(e) =>
                            setItens((a) =>
                              a.map((i, idx) =>
                                idx === indice ? { ...i, obrigatorio: e.target.checked } : i,
                              ),
                            )
                          }
                        />
                        obrigatório
                      </label>
                      <button
                        type="button"
                        onClick={() => setItens((a) => a.filter((_, idx) => idx !== indice))}
                        disabled={itens.length === 1}
                        className="btn-secondary btn-sm"
                      >
                        Remover
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <button type="submit" className="btn-primary btn-sm">
                Cadastrar modelo
              </button>
            </form>
          )}

          <div className="space-y-2">
            {modelos.map((modelo) => (
              <div key={modelo.id} className="card p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">{modelo.nome}</p>
                    {modelo.descricao && <p className="text-sm text-slate-600">{modelo.descricao}</p>}
                  </div>
                  {ehAdministrador && (
                    <button
                      onClick={() =>
                        remover(apiModelosChecklist.excluir(modelo.id), "Modelo excluído.")
                      }
                      className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                    >
                      Excluir
                    </button>
                  )}
                </div>
                <ul className="mt-2 space-y-1">
                  {modelo.itens.map((item) => (
                    <li key={item.id} className="text-sm text-slate-600">
                      • {item.descricao}
                      {item.obrigatorio && <span className="text-red-500"> *</span>}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {modelos.length === 0 && (
              <p className="text-sm text-slate-500">Nenhum modelo cadastrado ainda.</p>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

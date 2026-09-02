import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { ErroApi } from "../../lib/api";
import { apiAtas } from "../../lib/apiContratos";
import { useAuth } from "../../lib/AuthContext";
import type { AtaRegistroPreco } from "../../lib/tiposContratos";
import { useToast } from "../../lib/ToastContext";

const campoClasse = "field-input";

export function Atas() {
  const [atas, setAtas] = useState<AtaRegistroPreco[]>([]);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [orgao, setOrgao] = useState("");
  const [numeroAta, setNumeroAta] = useState("");
  const [objeto, setObjeto] = useState("");
  const [dataValidade, setDataValidade] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const { mostrarToast } = useToast();
  const { usuario } = useAuth();
  const ehAdministrador = usuario?.papel === "administrador";

  function carregar() {
    apiAtas.listar(true).then(setAtas).catch(() => setErro("Não foi possível carregar as atas."));
  }

  useEffect(carregar, []);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setErro(null);
    try {
      await apiAtas.criar({ orgao, numero_ata: numeroAta, objeto, data_validade: dataValidade });
      setOrgao("");
      setNumeroAta("");
      setObjeto("");
      setDataValidade("");
      setMostrarForm(false);
      carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível cadastrar a ata.");
    }
  }

  async function excluir(ata: AtaRegistroPreco) {
    if (!window.confirm(`Excluir a ata "${ata.numero_ata}" definitivamente? Essa ação não pode ser desfeita.`)) {
      return;
    }
    try {
      await apiAtas.excluir(ata.id);
      carregar();
      mostrarToast("Ata excluída.");
    } catch (e) {
      mostrarToast(e instanceof ErroApi ? e.message : "Não foi possível excluir a ata.", "erro");
    }
  }

  return (
    <div className="page-shell">
      <header className="page-header">
        <div>
          <Link to="/contratos" className="text-xs text-institucional-600 hover:underline">
            ← Contratos
          </Link>
          <h1 className="page-title">Atas de registro de preço</h1>
        </div>
        <button
          onClick={() => setMostrarForm((v) => !v)} className="btn-primary">
          {mostrarForm ? "Cancelar" : "+ Nova ata"}
        </button>
      </header>

      <main className="mx-auto max-w-3xl p-6">
        {erro && <p className="mb-4 text-sm text-red-600">{erro}</p>}

        {mostrarForm && (
          <form onSubmit={aoEnviar} className="card mb-6 space-y-3 p-5">
            <input
              className={campoClasse}
              placeholder="Órgão"
              value={orgao}
              onChange={(e) => setOrgao(e.target.value)}
              required
            />
            <input
              className={campoClasse}
              placeholder="Número da ata"
              value={numeroAta}
              onChange={(e) => setNumeroAta(e.target.value)}
              required
            />
            <textarea
              className={campoClasse}
              placeholder="Objeto"
              rows={2}
              value={objeto}
              onChange={(e) => setObjeto(e.target.value)}
              required
            />
            <div>
              <label className="mb-1 block text-xs text-slate-600">Validade</label>
              <input
                type="date"
                className={campoClasse}
                value={dataValidade}
                onChange={(e) => setDataValidade(e.target.value)}
                required
              />
            </div>
            <button
              type="submit" className="btn-primary">
              Cadastrar
            </button>
          </form>
        )}

        <div className="space-y-2">
          {atas.map((ata) => (
            <div key={ata.id} className="card flex items-start justify-between p-4">
              <div>
                <p className="font-medium text-slate-900">
                  {ata.orgao} — {ata.numero_ata}
                </p>
                <p className="text-sm text-slate-600">{ata.objeto}</p>
                <p className="text-xs text-slate-500">Válida até {ata.data_validade}</p>
              </div>
              {ehAdministrador && (
                <button
                  onClick={() => excluir(ata)}
                  className="btn-secondary btn-sm border-red-200 text-red-700 hover:bg-red-50"
                  title="Exclusão definitiva — restrita a administrador"
                >
                  Excluir
                </button>
              )}
            </div>
          ))}
          {atas.length === 0 && <p className="text-sm text-slate-500">Nenhuma ata disponível para adesão.</p>}
        </div>
      </main>
    </div>
  );
}

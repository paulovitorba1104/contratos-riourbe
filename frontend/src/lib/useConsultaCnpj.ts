import { useEffect, useState } from "react";

import { apiFornecedores } from "./apiContratos";
import { normalizarCnpj } from "./mascaras";
import type { ConsultaCnpj } from "./tiposContratos";

/** Consulta a Receita Federal (via BrasilAPI) assim que o CNPJ digitado
 * completa 14 dígitos — usada para autopreencher a razão social e mostrar
 * a situação cadastral antes de salvar. Nunca bloqueia: a verificação que
 * de fato recusa CNPJ inativo é a do backend ao salvar. */
export function useConsultaCnpj(cnpjMascarado: string) {
  const [consulta, setConsulta] = useState<ConsultaCnpj | null>(null);
  const [consultando, setConsultando] = useState(false);

  useEffect(() => {
    const digitos = normalizarCnpj(cnpjMascarado);
    if (digitos.length !== 14) {
      setConsulta(null);
      setConsultando(false);
      return;
    }
    let cancelado = false;
    setConsultando(true);
    apiFornecedores
      .consultarCnpj(digitos)
      .then((resultado) => {
        if (!cancelado) setConsulta(resultado);
      })
      .catch(() => {
        if (!cancelado) setConsulta({ encontrado: false, razao_social: null, situacao_cadastral: null, ativo: null });
      })
      .finally(() => {
        if (!cancelado) setConsultando(false);
      });
    return () => {
      cancelado = true;
    };
  }, [cnpjMascarado]);

  return { consulta, consultando };
}

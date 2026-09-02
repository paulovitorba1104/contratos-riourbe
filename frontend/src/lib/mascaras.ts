function apenasDigitos(valor: string): string {
  return valor.replace(/\D/g, "");
}

/** Formato padrão: 000.000.000-00 (11 dígitos). */
export function mascararCpf(valor: string): string {
  const d = apenasDigitos(valor).slice(0, 11);
  let resultado = d;
  if (d.length > 9) resultado = `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
  else if (d.length > 6) resultado = `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
  else if (d.length > 3) resultado = `${d.slice(0, 3)}.${d.slice(3)}`;
  return resultado;
}

/** Formato padrão: 00/000.000-0 (9 dígitos). */
export function mascararMatricula(valor: string): string {
  const d = apenasDigitos(valor).slice(0, 9);
  let resultado = d;
  if (d.length > 8) resultado = `${d.slice(0, 2)}/${d.slice(2, 5)}.${d.slice(5, 8)}-${d.slice(8)}`;
  else if (d.length > 5) resultado = `${d.slice(0, 2)}/${d.slice(2, 5)}.${d.slice(5)}`;
  else if (d.length > 2) resultado = `${d.slice(0, 2)}/${d.slice(2)}`;
  return resultado;
}

/** Formato padrão: 00.000.000/0000-00 (14 dígitos). */
export function mascararCnpj(valor: string): string {
  const d = apenasDigitos(valor).slice(0, 14);
  let resultado = d;
  if (d.length > 12) resultado = `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
  else if (d.length > 8) resultado = `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`;
  else if (d.length > 5) resultado = `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`;
  else if (d.length > 2) resultado = `${d.slice(0, 2)}.${d.slice(2)}`;
  return resultado;
}

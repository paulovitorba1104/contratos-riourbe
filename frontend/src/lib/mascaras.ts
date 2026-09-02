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

function formatarDigitosComoMoeda(digitos: string, negativo: boolean): string {
  if (digitos === "") return "";
  const semZerosExtras = digitos.replace(/^0+(?=\d)/, "");
  const comZeros = semZerosExtras.padStart(3, "0");
  const centavos = comZeros.slice(-2);
  const inteiroBruto = comZeros.slice(0, -2) || "0";
  const inteiroFormatado = inteiroBruto.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const sinal = negativo && Number(`${inteiroBruto}.${centavos}`) !== 0 ? "-" : "";
  return `${sinal}${inteiroFormatado},${centavos}`;
}

/**
 * Máscara de moeda estilo "calculadora": os dígitos digitados entram pela
 * direita como centavos e o milhar/milhão se formata sozinho (ex.: digitar
 * "1500000" vira "15.000,00") — evita a ambiguidade de "." x "," que quebra
 * um <input type="number"> ao lançar valores grandes.
 */
export function mascararMoeda(valor: string, permitirNegativo = false): string {
  const negativo = permitirNegativo && valor.trim().startsWith("-");
  const digitos = valor.replace(/\D/g, "");
  return formatarDigitosComoMoeda(digitos, negativo);
}

/** Formata um valor decimal vindo da API (ex.: "15000.00") para exibição inicial no campo mascarado. */
export function formatarMoedaInicial(valorDecimal: string | number): string {
  const numero = Number(valorDecimal);
  if (Number.isNaN(numero)) return "";
  const digitos = Math.round(Math.abs(numero) * 100).toString();
  return formatarDigitosComoMoeda(digitos, numero < 0);
}

/** Converte o valor mascarado (ex.: "-15.000,00") de volta para string decimal ("-15000.00") para a API. */
export function moedaParaNumero(valorFormatado: string): string {
  if (valorFormatado.trim() === "") return "0.00";
  const negativo = valorFormatado.trim().startsWith("-");
  const limpo = valorFormatado.replace(/[^\d,]/g, "").replace(",", ".");
  const numero = limpo === "" || limpo === "." ? "0.00" : limpo;
  return negativo ? `-${numero}` : numero;
}

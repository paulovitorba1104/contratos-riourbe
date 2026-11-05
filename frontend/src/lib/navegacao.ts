import { FileText, Gavel, KanbanSquare, LayoutGrid, Receipt, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export type ModuloSistema = "contratos" | "faturas";

/** Módulos que o administrador pode liberar para um operador (mesma lista do
 * backend, `ModuloSistema`). */
export const MODULOS: { valor: ModuloSistema; titulo: string; descricao: string }[] = [
  {
    valor: "contratos",
    titulo: "Contratos",
    descricao: "Contratos, instrumentos, fiscais, fornecedores e atas",
  },
  {
    valor: "faturas",
    titulo: "Faturas",
    descricao: "Faturas, medições e conferências — consulta os contratos, sem alterar",
  },
];

export interface ItemNavegacao {
  titulo: string;
  descricao: string;
  caminho: string | null;
  icone: LucideIcon;
  modulo?: ModuloSistema;
}

export function podeAcessar(
  usuario: { papel: string; modulos: ModuloSistema[] } | null,
  modulo: ModuloSistema,
): boolean {
  if (!usuario) return false;
  return usuario.papel === "administrador" || usuario.modulos.includes(modulo);
}

/** Fonte única dos módulos do sistema — usada pelo menu lateral (sempre
 * visível) e pelo Hub (visão geral). `caminho: null` = módulo ainda não
 * implementado ("Em breve"). */
export const ITENS_NAVEGACAO: ItemNavegacao[] = [
  { titulo: "Início", descricao: "Painel geral do sistema", caminho: "/", icone: LayoutGrid },
  {
    titulo: "Contratos",
    descricao: "Gestão de contratos e instrumentos processuais",
    caminho: "/contratos",
    icone: FileText,
    modulo: "contratos",
  },
  {
    titulo: "Faturas",
    descricao: "Controle de faturas: conferência documental e tributária, atesto e pagamento",
    caminho: "/faturas",
    icone: Receipt,
    modulo: "faturas",
  },
  { titulo: "Licitação", descricao: "Pesquisa de preços, ETP, TR e matriz de risco", caminho: null, icone: Gavel },
  {
    titulo: "Diárias, Passagens e Compras",
    descricao: "Fundo fixo e suprimento de fundos",
    caminho: null,
    icone: Wallet,
  },
  {
    titulo: "Planejador de Tarefas",
    descricao: "Quadros Kanban de tarefas do setor",
    caminho: null,
    icone: KanbanSquare,
  },
];

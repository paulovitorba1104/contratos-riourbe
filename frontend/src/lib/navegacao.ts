import { FileText, Gavel, KanbanSquare, LayoutGrid, Receipt, Wallet } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface ItemNavegacao {
  titulo: string;
  descricao: string;
  caminho: string | null;
  icone: LucideIcon;
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
  },
  {
    titulo: "Faturas",
    descricao: "Controle de faturas: conferência documental e tributária, atesto e pagamento",
    caminho: "/faturas",
    icone: Receipt,
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

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type TipoToast = "sucesso" | "erro";

interface Toast {
  id: number;
  tipo: TipoToast;
  mensagem: string;
}

interface ToastContextValor {
  mostrarToast: (mensagem: string, tipo?: TipoToast) => void;
}

const ToastContext = createContext<ToastContextValor | undefined>(undefined);

const CORES_TOAST: Record<TipoToast, string> = {
  sucesso: "bg-green-600",
  erro: "bg-red-600",
};

let proximoId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const mostrarToast = useCallback((mensagem: string, tipo: TipoToast = "sucesso") => {
    const id = proximoId++;
    setToasts((atual) => [...atual, { id, tipo, mensagem }]);
    setTimeout(() => {
      setToasts((atual) => atual.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  return (
    <ToastContext.Provider value={{ mostrarToast }}>
      {children}
      <div className="fixed right-4 top-4 z-50 space-y-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`rounded px-4 py-2 text-sm text-white shadow-lg ${CORES_TOAST[t.tipo]}`}
          >
            {t.mensagem}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValor {
  const contexto = useContext(ToastContext);
  if (!contexto) {
    throw new Error("useToast deve ser usado dentro de ToastProvider.");
  }
  return contexto;
}

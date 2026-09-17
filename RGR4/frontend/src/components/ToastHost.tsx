import { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react'

export type ToastKind = 'success' | 'error' | 'info'
export type ToastMessage = { id: number; kind: ToastKind; message: string }

export function notify(message: string, kind: ToastKind = 'info') {
  window.dispatchEvent(new CustomEvent('app:toast', { detail: { message, kind } }))
}

export default function ToastHost() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const onToast = (event: Event) => {
      const detail = (event as CustomEvent<{ message: string; kind: ToastKind }>).detail;
      const id = Date.now() + Math.random();
      
      setToasts((current) => [...current, { id, ...detail }]);
      
      window.setTimeout(
        () => setToasts((current) => current.filter((toast) => toast.id !== id)), 
        4500
      );
    };

    window.addEventListener('app:toast', onToast);
    return () => window.removeEventListener('app:toast', onToast);
  }, []);

  return (
    <div className="toast-stack" aria-live="polite">
      {toasts.map((toast) => (
        <div className={`toast toast-${toast.kind}`} key={toast.id}>
          <span>
            {toast.kind === 'error' ? (
              <AlertCircle size={17} />
            ) : toast.kind === 'success' ? (
              <CheckCircle2 size={17} />
            ) : (
              <Info size={17} />
            )}
          </span>
          <span>{toast.message}</span>
          <button 
            className="icon-button" 
            aria-label="Закрыть уведомление" 
            onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}
          >
            <X size={15} />
          </button>
        </div>
      ))}
    </div>
  );
}
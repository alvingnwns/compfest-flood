import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";

export function LoadingState({ label = "Memuat data simulasi…" }: { label?: string }) {
  return <div className="grid min-h-[360px] place-items-center"><div className="text-center"><div className="mx-auto mb-3 h-7 w-7 animate-spin rounded-full border-2 border-outline border-t-primary" /><p className="text-sm text-muted">{label}</p></div></div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div role="alert" className="card mx-auto my-12 max-w-lg p-6 text-center"><AlertTriangle className="mx-auto mb-3 text-danger" /><h2 className="section-title mb-1">Data tidak tersedia</h2><p className="mb-4 text-sm text-muted">{message}</p>{onRetry && <button onClick={onRetry} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary-dark"><RefreshCw size={16} /> Coba Lagi</button>}</div>;
}

export function EmptyState({ title, message }: { title: string; message: string }) {
  return <div className="card mx-auto my-12 max-w-lg p-8 text-center"><Inbox className="mx-auto mb-3 text-muted" /><h2 className="section-title mb-1">{title}</h2><p className="text-sm text-muted">{message}</p></div>;
}

import { ChevronLeft, ChevronRight } from 'lucide-react'

export default function Pagination({ skip, limit, total, onChange }: { skip: number; limit: number; total: number; onChange: (skip: number, limit: number) => void }) {
  const page = Math.floor(skip / limit) + 1
  const pages = Math.max(1, Math.ceil(total / limit))
  return <div className="pagination"><span className="muted">Страница {page} из {pages}</span><label className="page-size">Показывать<select value={limit} onChange={(event) => onChange(0, Number(event.target.value))}><option value="10">10</option><option value="25">25</option><option value="50">50</option></select></label><button className="icon-button" title="Предыдущая страница" disabled={page <= 1} onClick={() => onChange(Math.max(0, skip - limit), limit)}><ChevronLeft size={17} /></button><button className="icon-button" title="Следующая страница" disabled={page >= pages} onClick={() => onChange(skip + limit, limit)}><ChevronRight size={17} /></button></div>
}

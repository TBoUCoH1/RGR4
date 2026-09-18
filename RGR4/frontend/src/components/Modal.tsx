import { X } from 'lucide-react'
import type { ReactNode } from 'react'

export default function Modal({ title, eyebrow, children, onClose }: { title: string; eyebrow?: string; children: ReactNode; onClose: () => void }) {
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}><section className="modal"><button className="icon-button modal-close" onClick={onClose} aria-label="Закрыть"><X size={19} /></button>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2>{children}</section></div>
}

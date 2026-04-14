import type { ReactNode } from 'react'

type PageSectionProps = {
  title: string
  description: string
  children?: ReactNode
}

export function PageSection({ title, description, children }: PageSectionProps) {
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg shadow-slate-950/20">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-slate-300">{description}</p>
      {children ? <div className="mt-6">{children}</div> : null}
    </section>
  )
}

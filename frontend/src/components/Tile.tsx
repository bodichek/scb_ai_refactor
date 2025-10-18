import { PropsWithChildren } from 'react'

type Props = PropsWithChildren<{
  title: string
  subtitle?: string
  actions?: React.ReactNode
}>

export default function Tile({ title, subtitle, actions, children }: Props) {
  return (
    <section className="card tile-hover">
      <header className="card-header">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
          {subtitle && (
            <p className="text-sm text-gray-500">{subtitle}</p>
          )}
        </div>
        {actions}
      </header>
      <div className="card-body">{children}</div>
    </section>
  )
}

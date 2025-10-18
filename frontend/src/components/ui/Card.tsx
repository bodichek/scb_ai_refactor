type CardProps = {
  title?: string
  subtitle?: string
  className?: string
  children: React.ReactNode
  footer?: React.ReactNode
}

export function Card({ title, subtitle, className = '', children, footer }: CardProps) {
  return (
    <section
      className={`bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-800 p-6 space-y-4 ${className}`}
    >
      {(title || subtitle) && (
        <header className="space-y-1">
          {title && <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>}
          {subtitle && <p className="text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </header>
      )}
      <div>{children}</div>
      {footer && <footer className="pt-4 border-t border-slate-200 dark:border-slate-800">{footer}</footer>}
    </section>
  )
}

export default Card

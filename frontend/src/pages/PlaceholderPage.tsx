type PlaceholderPageProps = {
  title: string
  template?: string
  description?: string
}

export function PlaceholderPage({ title, template, description }: PlaceholderPageProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/60 dark:bg-slate-900/60 p-8 text-center">
        <h1 className="text-xl font-semibold text-slate-800 dark:text-slate-100">{title}</h1>
        {template && (
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
            React přepis šablony <code className="font-mono">{template}</code> je připravován.
          </p>
        )}
        {description && <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">{description}</p>}
        <p className="text-sm text-slate-400 dark:text-slate-500 mt-4">
          Tento panel bude přepsán na plně funkční React komponentu v dalších krocích.
        </p>
      </div>
    </div>
  )
}

export default PlaceholderPage

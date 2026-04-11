function Section({ title, open, onToggle, children }) {
  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full px-3 py-2 text-left text-sm font-medium bg-slate-700/40 hover:bg-slate-700/70 transition flex items-center justify-between"
      >
        {title}
        <span className="text-slate-400">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="px-3 py-2 text-sm text-slate-200 whitespace-pre-wrap">{children}</div>}
    </div>
  )
}

export default function ProblemPanel({ problem, expanded, onToggleSection, onCopyExample, onOpenFetch }) {
  return (
    <section className="panel-shell h-full flex flex-col overflow-hidden">
      <header className="sticky top-0 z-10 border-b border-border bg-panel/95 backdrop-blur px-3 py-3">
        <div className="flex items-start justify-between gap-2">
          <h2 className="text-base font-semibold text-slate-100">{problem.title}</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={onOpenFetch}
              className="text-xs px-2 py-1 rounded-lg border border-border bg-slate-700/60 hover:bg-slate-600/80 transition"
            >
              Fetch
            </button>
            <span
              className={`text-xs px-2 py-0.5 rounded-full border ${
                problem.difficulty === 'Easy'
                  ? 'bg-emerald-600/20 text-emerald-300 border-emerald-500/50'
                  : problem.difficulty === 'Medium'
                    ? 'bg-yellow-600/20 text-yellow-300 border-yellow-500/50'
                    : 'bg-red-600/20 text-red-300 border-red-500/50'
              }`}
            >
              {problem.difficulty}
            </span>
          </div>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {problem.tags.map((tag) => (
            <span key={tag} className="text-xs px-2 py-0.5 rounded-full border border-border bg-slate-700/50 text-slate-300">
              {tag}
            </span>
          ))}
        </div>
      </header>

      <div className="flex-1 p-3 overflow-auto scrollbar-thin space-y-3">
        <Section
          title="Description"
          open={expanded.description}
          onToggle={() => onToggleSection('description')}
        >
          {problem.description}
        </Section>
        <Section
          title="Constraints"
          open={expanded.constraints}
          onToggle={() => onToggleSection('constraints')}
        >
          {problem.constraints}
        </Section>
        <div className="border border-border rounded-lg overflow-hidden">
          <div className="px-3 py-2 bg-slate-700/40 flex items-center justify-between">
            <button
              onClick={() => onToggleSection('examples')}
              className="text-sm font-medium hover:text-indigo-300 transition"
            >
              Examples {expanded.examples ? '−' : '+'}
            </button>
            <button
              onClick={onCopyExample}
              className="text-xs px-2 py-1 rounded-lg border border-border bg-slate-700/60 hover:bg-slate-600/80 transition"
            >
              Copy example
            </button>
          </div>
          {expanded.examples && (
            <div className="px-3 py-2 text-sm text-slate-200 whitespace-pre-wrap">{problem.examples}</div>
          )}
        </div>
      </div>
    </section>
  )
}
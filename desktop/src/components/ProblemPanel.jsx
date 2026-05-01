function Section({ title, open, onToggle, children }) {
  return (
    <div className="section">
      <button type="button" onClick={onToggle} className="section-header">
        {title}
        <span>{open ? '-' : '+'}</span>
      </button>
      {open && <div className="section-body">{children}</div>}
    </div>
  )
}

export default function ProblemPanel({ problem, expanded, onToggleSection, onCopyExample, onOpenFetch }) {
  return (
    <section className="panel shell">
      <header className="panel-header sticky">
        <div className="panel-header-left">
          <h2>{problem.title}</h2>
        </div>
        <div className="panel-header-right">
          <button type="button" onClick={onOpenFetch}>
            Fetch
          </button>
          <span className={`badge difficulty ${problem.difficulty?.toLowerCase() || 'medium'}`}>
            {problem.difficulty}
          </span>
        </div>
        <div className="tag-row">
          {problem.tags.map((tag) => (
            <span key={tag} className="tag">
              {tag}
            </span>
          ))}
        </div>
      </header>

      <div className="panel-body scrollable">
        <Section title="Description" open={expanded.description} onToggle={() => onToggleSection('description')}>
          {problem.description}
        </Section>
        <Section title="Constraints" open={expanded.constraints} onToggle={() => onToggleSection('constraints')}>
          {problem.constraints}
        </Section>
        <div className="section">
          <div className="section-header">
            <button type="button" onClick={() => onToggleSection('examples')} className="link-button">
              Examples {expanded.examples ? '-' : '+'}
            </button>
            <button type="button" onClick={onCopyExample}>
              Copy example
            </button>
          </div>
          {expanded.examples && <div className="section-body">{problem.examples}</div>}
        </div>
      </div>
    </section>
  )
}

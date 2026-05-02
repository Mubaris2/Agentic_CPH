function Section({ title, open, onToggle, children, loading }) {
  return (
    <div className="section">
      <button type="button" onClick={onToggle} className="section-header">
        {title}
        {loading && (
          <span className="analysis-badge" title="Agent is analyzing…">
            ✦ analyzing
          </span>
        )}
        <span>{open ? '-' : '+'}</span>
      </button>
      {open && <div className="section-body">{children}</div>}
    </div>
  )
}

/** Renders constraints as bullet-point lines when the string contains "•". */
function ConstraintsBody({ text }) {
  if (!text) return <span className="muted">No constraints available.</span>
  const lines = text.split('\n').filter(Boolean)
  const hasBullets = lines.some((l) => l.trim().startsWith('•'))
  if (hasBullets) {
    return (
      <ul className="constraint-list">
        {lines.map((line, i) => (
          <li key={i}>{line.replace(/^[•\-–—*]\s*/, '')}</li>
        ))}
      </ul>
    )
  }
  return <pre className="pre-wrap">{text}</pre>
}

/** Renders the examples section with a subtle card per example. */
function ExamplesBody({ text }) {
  if (!text) return <span className="muted">No examples available.</span>

  // Split by the delimiter we place in the agent output
  const blocks = text.split(/──\s*Example\s*\d+\s*──/).filter(Boolean)

  if (blocks.length <= 1) {
    // Plain pre-formatted fallback
    return <pre className="pre-wrap">{text}</pre>
  }

  return (
    <div className="example-blocks">
      {blocks.map((block, idx) => {
        const inputMatch = block.match(/Input:\n([\s\S]*?)(?=\nOutput:|$)/i)
        const outputMatch = block.match(/Output:\n([\s\S]*?)(?=\nExplanation:|$)/i)
        const explanationMatch = block.match(/Explanation:\n([\s\S]*?)$/i)

        return (
          <div key={idx} className="example-card">
            <div className="example-label">Example {idx + 1}</div>
            {inputMatch && (
              <div className="example-io">
                <span className="io-label">Input</span>
                <pre className="io-pre">{inputMatch[1].trim()}</pre>
              </div>
            )}
            {outputMatch && (
              <div className="example-io">
                <span className="io-label">Output</span>
                <pre className="io-pre">{outputMatch[1].trim()}</pre>
              </div>
            )}
            {explanationMatch && (
              <div className="example-note">
                <span className="io-label">Explanation</span>
                <p>{explanationMatch[1].trim()}</p>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function ProblemPanel({
  problem,
  expanded,
  onToggleSection,
  onCopyExample,
  onOpenFetch,
  analysisLoading = false,
}) {
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
          {analysisLoading && (
            <span className="tag analyzing-tag" title="Agent is parsing the problem…">
              ✦ analyzing…
            </span>
          )}
        </div>
      </header>

      <div className="panel-body scrollable">
        <Section
          title="Description"
          open={expanded.description}
          onToggle={() => onToggleSection('description')}
          loading={analysisLoading}
        >
          {analysisLoading ? (
            <p className="muted">Analyzing problem statement…</p>
          ) : (
            <p className="description-text">{problem.description}</p>
          )}
        </Section>

        <Section
          title="Constraints"
          open={expanded.constraints}
          onToggle={() => onToggleSection('constraints')}
          loading={analysisLoading}
        >
          {analysisLoading ? (
            <p className="muted">Extracting constraints…</p>
          ) : (
            <ConstraintsBody text={problem.constraints} />
          )}
        </Section>

        <div className="section">
          <div className="section-header">
            <button
              type="button"
              onClick={() => onToggleSection('examples')}
              className="link-button"
            >
              Examples {expanded.examples ? '-' : '+'}
            </button>
            <button type="button" onClick={onCopyExample}>
              Copy example
            </button>
          </div>
          {expanded.examples && (
            <div className="section-body">
              {analysisLoading ? (
                <p className="muted">Formatting examples…</p>
              ) : (
                <ExamplesBody text={problem.examples} />
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

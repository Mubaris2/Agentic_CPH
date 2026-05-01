const tabs = ['Input', 'Output', 'Expected', 'Diff']

function statusTone(status) {
  if (status === 'Passed') return 'status passed'
  if (status === 'Failed') return 'status failed'
  return 'status pending'
}

export default function TestCasePanel({
  testCases,
  activeCaseId,
  onSelectCase,
  onAddCase,
  activeTab,
  setActiveTab,
  onUpdateCase,
  runStatus,
  compileError
}) {
  const activeCase = testCases.find((item) => item.id === activeCaseId)

  const getTabContent = () => {
    if (!activeCase) return ''
    if (activeTab === 'Input') return activeCase.input
    if (activeTab === 'Output') return activeCase.output
    if (activeTab === 'Expected') return activeCase.expected
    return activeCase.status === 'Passed'
      ? 'No differences. Output matches expected.'
      : `Expected:\n${activeCase.expected}\n\nActual:\n${activeCase.output}`
  }

  const showEditable = !!activeCase && (activeTab === 'Input' || activeTab === 'Expected')

  return (
    <section className="panel shell">
      <header className="panel-header">
        <div className="panel-header-left">
          <h3>Test Cases</h3>
          {runStatus && <span className="badge">{runStatus}</span>}
        </div>
        <button type="button" onClick={onAddCase}>
          + Add
        </button>
      </header>

      {testCases.length === 0 ? (
        <div className="panel-empty">No test cases added yet</div>
      ) : (
        <>
          <div className="case-strip">
            {testCases.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectCase(item.id)}
                className={`case-chip ${item.id === activeCaseId ? 'active' : ''}`}
              >
                <span>Case {item.id}</span>
                <span className={statusTone(item.status)}>{item.status}</span>
              </button>
            ))}
          </div>

          <div className="tab-strip">
            {tabs.map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={activeTab === tab ? 'tab active' : 'tab'}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="panel-body">
            {!activeCase ? (
              <div className="panel-empty">Select a test case to edit.</div>
            ) : showEditable ? (
              <textarea
                value={getTabContent()}
                onChange={(event) =>
                  onUpdateCase(activeCase.id, activeTab === 'Input' ? 'input' : 'expected', event.target.value)
                }
                className="code-input"
              />
            ) : (
              <pre className="console">{getTabContent()}</pre>
            )}
          </div>

          {(compileError || activeCase?.error) && (
            <div className="error-panel">
              {compileError && (
                <div>
                  <strong>Compilation:</strong>
                  <pre className="console">{compileError}</pre>
                </div>
              )}
              {activeCase?.error && (
                <div>
                  <strong>Runtime:</strong>
                  <pre className="console">{activeCase.error}</pre>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  )
}

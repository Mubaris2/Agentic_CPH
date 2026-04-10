const tabs = ['Input', 'Output', 'Expected', 'Diff']

function statusTone(status) {
  if (status === 'Passed') return 'bg-emerald-600/20 text-emerald-300 border-emerald-500/50'
  if (status === 'Failed') return 'bg-red-600/20 text-red-300 border-red-500/50'
  return 'bg-yellow-600/20 text-yellow-300 border-yellow-500/50'
}

export default function TestCasePanel({
  testCases,
  activeCaseId,
  onSelectCase,
  onAddCase,
  activeTab,
  setActiveTab,
  runStatus
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

  return (
    <section className="panel-shell h-full flex flex-col overflow-hidden">
      <header className="sticky top-0 z-10 border-b border-border bg-panel/95 backdrop-blur px-3 py-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-slate-100">Test Cases</h3>
          {runStatus && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full border ${
                runStatus.includes('Accepted')
                  ? 'bg-emerald-600/20 text-emerald-300 border-emerald-500/50'
                  : runStatus.includes('Wrong') || runStatus.includes('Error')
                    ? 'bg-red-600/20 text-red-300 border-red-500/50'
                    : 'bg-yellow-600/20 text-yellow-300 border-yellow-500/50'
              }`}
            >
              {runStatus}
            </span>
          )}
        </div>
        <button
          onClick={onAddCase}
          className="text-xs px-2 py-1 rounded-lg border border-border bg-slate-700/60 hover:bg-slate-600/80 transition"
        >
          + Add
        </button>
      </header>

      {testCases.length === 0 ? (
        <div className="flex-1 grid place-items-center text-sm text-slate-400">No test cases added yet</div>
      ) : (
        <>
          <div className="px-3 py-2 border-b border-border flex gap-2 overflow-x-auto scrollbar-thin">
            {testCases.map((item) => (
              <button
                key={item.id}
                onClick={() => onSelectCase(item.id)}
                className={`inline-flex items-center gap-2 px-2 py-1 text-xs rounded-lg border whitespace-nowrap transition ${
                  item.id === activeCaseId ? 'chip-active' : 'chip-idle'
                }`}
              >
                <span>Case {item.id}</span>
                <span className={`px-1.5 py-0.5 rounded border ${statusTone(item.status)}`}>{item.status}</span>
              </button>
            ))}
          </div>

          <div className="px-3 pt-2 border-b border-border flex gap-2">
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-2 py-1 text-xs rounded-t-lg border border-b-0 transition ${
                  activeTab === tab
                    ? 'bg-slate-700/90 border-indigo-500 text-indigo-300'
                    : 'bg-slate-800/70 border-border text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="flex-1 p-3 overflow-auto scrollbar-thin">
            <pre className="m-0 text-sm leading-6 font-mono whitespace-pre-wrap text-slate-200">{getTabContent()}</pre>
          </div>
        </>
      )}
    </section>
  )
}
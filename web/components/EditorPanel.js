import dynamic from 'next/dynamic'

const MonacoEditor = dynamic(() => import('@monaco-editor/react'), { ssr: false })

export default function EditorPanel({
  code,
  onCodeChange,
  fileName,
  language,
  onLanguageChange,
  onRun,
  runLoading,
  minimapEnabled,
  onToggleMinimap,
  wordWrap,
  onToggleWordWrap,
  setEditorInstance,
  onFormatCode,
  onClearTestCases
}) {
  return (
    <section className="panel-shell h-full flex flex-col overflow-hidden">
      <header className="sticky top-0 z-20 border-b border-border bg-panel/95 backdrop-blur px-3 py-2 flex items-center gap-3">
        <span className="text-sm font-medium text-slate-200">{fileName}</span>
        <select
          value={language}
          onChange={(e) => onLanguageChange(e.target.value)}
          className="bg-slate-700/70 border border-border rounded-lg px-2 py-1 text-sm text-slate-200 outline-none focus:border-indigo-500"
        >
          <option value="cpp">C++</option>
          <option value="python">Python</option>
          <option value="java">Java</option>
        </select>
        <button
          onClick={onToggleMinimap}
          className="px-2 py-1 text-xs rounded-lg border border-border bg-slate-700/60 hover:bg-slate-600/80 transition"
        >
          Minimap
        </button>
        <button
          onClick={onToggleWordWrap}
          className="px-2 py-1 text-xs rounded-lg border border-border bg-slate-700/60 hover:bg-slate-600/80 transition"
        >
          Word Wrap
        </button>
        <select
          onChange={(e) => {
            if (e.target.value === 'format') onFormatCode()
            if (e.target.value === 'clear') onClearTestCases()
            e.target.value = ''
          }}
          defaultValue=""
          className="bg-slate-700/70 border border-border rounded-lg px-2 py-1 text-xs text-slate-200 outline-none focus:border-indigo-500"
        >
          <option value="" disabled>
            Actions
          </option>
          <option value="format">Format Code</option>
          <option value="clear">Clear Test Cases</option>
        </select>
        <button
          onClick={onRun}
          disabled={runLoading}
          className="ml-auto inline-flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-70 px-3 py-1.5 text-sm font-semibold transition"
        >
          {runLoading && <span className="h-3 w-3 border-2 border-white/80 border-t-transparent rounded-full animate-spin" />}
          {runLoading ? 'Running...' : 'Run'}
        </button>
      </header>

      <div className="flex-1 overflow-hidden">
        <MonacoEditor
          height="100%"
          language={language}
          value={code}
          theme="vs-dark"
          onChange={(value) => onCodeChange(value ?? '')}
          onMount={(editor) => setEditorInstance(editor)}
          options={{
            minimap: { enabled: minimapEnabled },
            wordWrap: wordWrap ? 'on' : 'off',
            folding: true,
            lineNumbers: 'on',
            renderLineHighlight: 'line',
            fontSize: 14,
            automaticLayout: true,
            scrollBeyondLastLine: false,
            padding: { top: 12, bottom: 12 }
          }}
        />
      </div>
    </section>
  )
}
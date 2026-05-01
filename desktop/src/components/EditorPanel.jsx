import Editor from '@monaco-editor/react'

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
    <section className="panel shell">
      <header className="panel-header">
        <div className="panel-header-left">
          <span className="file-name">{fileName}</span>
          <select value={language} onChange={(event) => onLanguageChange(event.target.value)}>
            <option value="cpp">C++</option>
            <option value="python">Python</option>
            <option value="java">Java</option>
          </select>
          <button type="button" onClick={onToggleMinimap}>
            Minimap
          </button>
          <button type="button" onClick={onToggleWordWrap}>
            Word Wrap
          </button>
          <select
            defaultValue=""
            onChange={(event) => {
              const value = event.target.value
              if (value === 'format') onFormatCode()
              if (value === 'clear') onClearTestCases()
              event.target.value = ''
            }}
          >
            <option value="" disabled>
              Actions
            </option>
            <option value="format">Format Code</option>
            <option value="clear">Clear Test Cases</option>
          </select>
        </div>
        <button type="button" className="primary" onClick={onRun} disabled={runLoading}>
          {runLoading ? 'Running...' : 'Run'}
        </button>
      </header>

      <div className="panel-body editor-body">
        <Editor
          height="100%"
          language={language}
          theme="vs-dark"
          value={code}
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

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
  onClearTestCases,
  onToggleSidebar
}) {
  return (
    <section className="panel shell">
      <header className="panel-header">
        <div className="panel-header-left">
          <button 
            type="button" 
            onClick={onToggleSidebar} 
            title="Toggle Sidebar" 
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '6px', background: 'transparent', border: 'none', color: '#94a3b8' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
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

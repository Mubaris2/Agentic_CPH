import { useEffect, useMemo, useRef, useState } from 'react'
import EditorPanel from '../components/EditorPanel'
import TestCasePanel from '../components/TestCasePanel'
import ProblemPanel from '../components/ProblemPanel'
import ChatPanel from '../components/ChatPanel'

const problemData = {
  title: 'No problem loaded',
  difficulty: 'Medium',
  tags: ['Fetch Required'],
  description: 'Fetch/import a problem first to start solving.',
  constraints: 'No constraints available until a problem is fetched.',
  examples: 'No examples available until a problem is fetched.'
}

const starterCode = {
  cpp: `#include <bits/stdc++.h>\nusing namespace std;\n\nvector<int> twoSum(vector<int>& nums, int target) {\n    unordered_map<int, int> seen;\n    for (int i = 0; i < (int)nums.size(); i++) {\n        int need = target - nums[i];\n        if (seen.count(need)) return {seen[need], i};\n        seen[nums[i]] = i;\n    }\n    return {};\n}\n\nint main() {\n    return 0;\n}`,
  python: `def two_sum(nums, target):\n    seen = {}\n    for i, value in enumerate(nums):\n        need = target - value\n        if need in seen:\n            return [seen[need], i]\n        seen[value] = i\n    return []\n\nif __name__ == '__main__':\n    pass`,
  java: `import java.util.*;\n\npublic class Main {\n    public static int[] twoSum(int[] nums, int target) {\n        Map<Integer, Integer> seen = new HashMap<>();\n        for (int i = 0; i < nums.length; i++) {\n            int need = target - nums[i];\n            if (seen.containsKey(need)) return new int[] {seen.get(need), i};\n            seen.put(nums[i], i);\n        }\n        return new int[] {};\n    }\n}`
}

export default function Home() {
  const editorRef = useRef(null)
  const chatScrollRef = useRef(null)
  const [language, setLanguage] = useState('cpp')
  const [code, setCode] = useState(starterCode.cpp)
  const [minimapEnabled, setMinimapEnabled] = useState(false)
  const [wordWrap, setWordWrap] = useState(false)
  const [leftWidth, setLeftWidth] = useState(70)
  const [leftTopHeight, setLeftTopHeight] = useState(68)
  const [rightTopHeight, setRightTopHeight] = useState(52)
  const [rightPanelOpen, setRightPanelOpen] = useState(true)
  const [runLoading, setRunLoading] = useState(false)
  const [runStatus, setRunStatus] = useState('')
  const [activeTab, setActiveTab] = useState('Input')
  const [testCases, setTestCases] = useState([])
  const [activeCaseId, setActiveCaseId] = useState(null)
  const [expanded, setExpanded] = useState({ description: true, constraints: true, examples: true })
  const [problem, setProblem] = useState(problemData)
  const [messages, setMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isFetchModalOpen, setIsFetchModalOpen] = useState(false)
  const [fetchError, setFetchError] = useState('')
  const [problemUrl, setProblemUrl] = useState('https://codeforces.com/problemset/problem/4/A')
  const [syncLoading, setSyncLoading] = useState(false)
  const [lastSeenImportId, setLastSeenImportId] = useState('')
  const [sessionId, setSessionId] = useState('')

  const layoutLeftWidth = rightPanelOpen ? leftWidth : 100

  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [messages, isTyping])

  useEffect(() => {
    function onKeyDown(event) {
      if (!event.ctrlKey) return
      if (event.key === 'Enter') {
        event.preventDefault()
        runCode()
      }
      if (event.key === '/') {
        event.preventDefault()
        editorRef.current?.trigger('keyboard', 'editor.action.commentLine', null)
      }
      if (event.key.toLowerCase() === 'b') {
        event.preventDefault()
        setRightPanelOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [code, testCases])

  function beginDrag(type) {
    return (event) => {
      event.preventDefault()
      function onMove(moveEvent) {
        const viewportW = window.innerWidth
        const viewportH = window.innerHeight
        if (type === 'main-split') {
          const next = (moveEvent.clientX / viewportW) * 100
          setLeftWidth(Math.max(50, Math.min(85, next)))
          return
        }
        if (type === 'left-split') {
          const next = (moveEvent.clientY / viewportH) * 100
          setLeftTopHeight(Math.max(40, Math.min(82, next)))
          return
        }
        const next = (moveEvent.clientY / viewportH) * 100
        setRightTopHeight(Math.max(30, Math.min(75, next)))
      }

      function stopMove() {
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', stopMove)
      }

      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', stopMove)
    }
  }

  async function runCode() {
    setRunLoading(true)
    setRunStatus('Running...')
    try {
      if (testCases.length === 0) {
        setRunStatus('Error: No test cases')
        return
      }
      const res = await fetch('http://localhost:8000/api/code/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language,
          code,
          test_cases: testCases.map((item) => ({ id: item.id, input: item.input, expected: item.expected })),
          timeout_seconds: 3
        })
      })
      if (!res.ok) throw new Error('Failed to run code')
      const data = await res.json()
      const byId = new Map((data.cases || []).map((item) => [item.id, item]))
      const next = testCases.map((item) => {
        const result = byId.get(item.id)
        if (!result) return item
        return {
          ...item,
          output: result.output || '',
          status: result.status || 'Failed'
        }
      })
      setTestCases(next)
      setRunStatus(data.error ? `Error: ${data.error}` : (data.status || 'Completed'))
      setActiveTab('Diff')
    } catch (error) {
      setRunStatus(`Error: ${String(error)}`)
    } finally {
      setRunLoading(false)
    }
  }

  function formatCode() {
    editorRef.current?.getAction('editor.action.formatDocument')?.run()
  }

  function clearTestCases() {
    setTestCases([])
    setActiveCaseId(null)
    setRunStatus('')
  }

  function addCase() {
    const nextId = testCases.length ? testCases[testCases.length - 1].id + 1 : 1
    const nextCase = { id: nextId, input: '', expected: '', output: '', status: 'Pending' }
    setTestCases((prev) => [...prev, nextCase])
    setActiveCaseId(nextId)
  }

  function toggleSection(name) {
    setExpanded((prev) => ({ ...prev, [name]: !prev[name] }))
  }

  async function copyExample() {
    try {
      await navigator.clipboard.writeText(problem.examples)
    } catch {
      return
    }
  }

  function openCodeforcesLogin() {
    window.open('https://codeforces.com/enter', '_blank')
  }

  function openCodeforcesProblem() {
    setFetchError('')
    const url = problemUrl.trim()
    const pattern = /^https:\/\/(www\.)?codeforces\.com\/(contest|problemset\/problem)\/\d+\/(problem\/)?[A-Za-z][A-Za-z0-9]*/
    if (!pattern.test(url)) {
      setFetchError('Enter a valid Codeforces problem URL.')
      return
    }
    window.open(url, '_blank')
  }

  function problemIdFromUrl(url) {
    const match = url.match(/https:\/\/(?:www\.)?codeforces\.com\/(?:contest|problemset\/problem)\/(\d+)\/(?:problem\/)?([A-Za-z][A-Za-z0-9]*)/)
    if (!match) return ''
    return `${match[1]}_${match[2].toUpperCase()}`
  }

  function applyImportedProblem(imported) {
    if (!imported) return
    const importedExamples = (imported.examples || []).map((example, index) => ({
      id: index + 1,
      input: example.input || '',
      expected: example.output || '',
      output: '',
      status: 'Pending'
    }))
    const next = {
      title: imported.title || imported.id || 'Imported Problem',
      difficulty: imported.rating ? (imported.rating <= 1200 ? 'Easy' : imported.rating <= 1700 ? 'Medium' : 'Hard') : 'Medium',
      tags: imported.tags?.length ? imported.tags : ['Codeforces'],
      description: imported.statement || 'Statement not available',
      constraints: imported.constraints || 'Constraints not explicitly listed in statement.',
      examples: (imported.examples || [])
        .map((example, index) => `Example ${index + 1}\nInput:\n${example.input || ''}\nOutput:\n${example.output || ''}`)
        .join('\n\n') || imported.source_url || 'N/A'
    }
    setProblem(next)
    setTestCases(importedExamples)
    setActiveCaseId(importedExamples.length ? importedExamples[0].id : null)
    setRunStatus('')
    setActiveTab('Input')
    setExpanded({ description: true, constraints: true, examples: true })
  }

  async function syncLatestImportedProblem(options = { silent: false, closeOnSuccess: false }) {
    const { silent, closeOnSuccess } = options
    if (!silent) setSyncLoading(true)
    try {
      const expectedId = problemIdFromUrl(problemUrl.trim())
      let imported = null

      if (expectedId) {
        const byIdRes = await fetch(`http://localhost:8000/api/problems/import/${encodeURIComponent(expectedId)}`)
        if (!byIdRes.ok) throw new Error('Unable to read imported problem by id')
        const byIdData = await byIdRes.json()
        imported = byIdData?.item
      }

      if (!imported) {
        const res = await fetch('http://localhost:8000/api/problems/import/latest')
        if (!res.ok) throw new Error('Unable to read latest imported problem')
        const data = await res.json()
        imported = data?.item
      }

      if (!imported?.id) {
        if (!silent) setFetchError('No imported problem found yet.')
        return
      }
      if (imported.id === lastSeenImportId) {
        if (!silent) setFetchError('No new imported problem yet. Import from extension then retry.')
        return
      }
      applyImportedProblem(imported)
      setLastSeenImportId(imported.id)
      setFetchError('')
      if (closeOnSuccess) setIsFetchModalOpen(false)
    } catch (error) {
      if (!silent) setFetchError(String(error))
    } finally {
      if (!silent) setSyncLoading(false)
    }
  }

  useEffect(() => {
    if (!isFetchModalOpen) return

    const poll = window.setInterval(() => {
      syncLatestImportedProblem({ silent: true, closeOnSuccess: true })
    }, 2500)

    return () => window.clearInterval(poll)
  }, [isFetchModalOpen, lastSeenImportId, problemUrl])

  async function sendChat(text) {
    const prompt = text.trim()
    if (!prompt) return
    const userMessage = { id: Date.now(), role: 'user', content: prompt }
    setMessages((prev) => [...prev, userMessage])
    setChatInput('')
    setIsTyping(true)
    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: prompt,
          code,
          session_id: sessionId || undefined,
          user_data: {
            problem_context: {
              title: problem.title,
              statement: problem.description,
              constraints: problem.constraints
            }
          }
        })
      })
      if (!res.ok) throw new Error('Chat request failed')
      const data = await res.json()
      if (data.session_id) setSessionId(data.session_id)
      const content = data.final_response || 'No response generated.'
      setMessages((prev) => [...prev, { id: Date.now() + 1, role: 'assistant', content }])
    } catch (error) {
      setMessages((prev) => [...prev, { id: Date.now() + 1, role: 'assistant', content: `Error: ${String(error)}` }])
    } finally {
      setIsTyping(false)
    }
  }

  function quickAction(label) {
    sendChat(label)
  }

  const fileName = useMemo(() => {
    if (language === 'python') return 'main.py'
    if (language === 'java') return 'Main.java'
    return 'main.cpp'
  }, [language])

  return (
    <main className="h-full p-3">
      <div className="h-full flex gap-2">
        <div className="h-full" style={{ width: `${layoutLeftWidth}%` }}>
          <div className="h-full flex flex-col gap-2">
            <div className="min-h-0" style={{ height: `${leftTopHeight}%` }}>
              <EditorPanel
                code={code}
                onCodeChange={setCode}
                fileName={fileName}
                language={language}
                onLanguageChange={(nextLanguage) => {
                  setLanguage(nextLanguage)
                  setCode(starterCode[nextLanguage])
                }}
                onRun={runCode}
                runLoading={runLoading}
                minimapEnabled={minimapEnabled}
                onToggleMinimap={() => setMinimapEnabled((prev) => !prev)}
                wordWrap={wordWrap}
                onToggleWordWrap={() => setWordWrap((prev) => !prev)}
                setEditorInstance={(editor) => {
                  editorRef.current = editor
                }}
                onFormatCode={formatCode}
                onClearTestCases={clearTestCases}
              />
            </div>

            <div className="drag-handle h-1.5 rounded cursor-row-resize" onMouseDown={beginDrag('left-split')} />

            <div className="min-h-0" style={{ height: `${100 - leftTopHeight}%` }}>
              <TestCasePanel
                testCases={testCases}
                activeCaseId={activeCaseId}
                onSelectCase={setActiveCaseId}
                onAddCase={addCase}
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                runStatus={runStatus}
              />
            </div>
          </div>
        </div>

        {rightPanelOpen && (
          <>
            <div className="drag-handle w-1.5 rounded cursor-col-resize" onMouseDown={beginDrag('main-split')} />
            <div className="h-full" style={{ width: `${100 - leftWidth}%` }}>
              <div className="h-full flex flex-col gap-2">
                <div className="min-h-0" style={{ height: `${rightTopHeight}%` }}>
                  <ProblemPanel
                    problem={problem}
                    expanded={expanded}
                    onToggleSection={toggleSection}
                    onCopyExample={copyExample}
                    onOpenFetch={() => {
                      setFetchError('')
                      setIsFetchModalOpen(true)
                    }}
                  />
                </div>

                <div className="drag-handle h-1.5 rounded cursor-row-resize" onMouseDown={beginDrag('right-split')} />

                <div className="min-h-0" style={{ height: `${100 - rightTopHeight}%` }}>
                  <ChatPanel
                    messages={messages}
                    chatInput={chatInput}
                    setChatInput={setChatInput}
                    onSend={sendChat}
                    onQuickAction={quickAction}
                    isTyping={isTyping}
                    chatScrollRef={chatScrollRef}
                  />
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {isFetchModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/70 backdrop-blur-sm grid place-items-center p-4">
          <div className="panel-shell w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="border-b border-border px-4 py-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-100">Fetch Codeforces Problem</h3>
              <button
                onClick={() => setIsFetchModalOpen(false)}
                className="text-xs px-2 py-1 rounded-lg border border-border bg-slate-700/60 hover:bg-slate-600/80 transition"
              >
                Close
              </button>
            </div>

            <div className="p-4 overflow-auto scrollbar-thin space-y-4">
              <div className="border border-border rounded-lg p-3 bg-slate-800/60 space-y-3">
                <p className="text-xs text-slate-300 font-medium">Step 1: Open Codeforces Problem</p>
                <p className="text-xs text-slate-400">
                  Paste a Codeforces problem URL and open it. This is click one.
                </p>
                <div className="flex flex-col md:flex-row gap-2">
                  <input
                    value={problemUrl}
                    onChange={(e) => setProblemUrl(e.target.value)}
                    placeholder="https://codeforces.com/problemset/problem/4/A"
                    className="flex-1 rounded-lg bg-slate-700/60 border border-border px-2 py-1.5 text-xs outline-none focus:border-indigo-500"
                  />
                  <button
                    type="button"
                    onClick={openCodeforcesProblem}
                    className="text-xs px-3 py-1.5 rounded-lg border border-border bg-indigo-600 hover:bg-indigo-500 transition"
                  >
                    Open Problem
                  </button>
                </div>
              </div>

              {fetchError && <p className="text-xs text-red-300">{fetchError}</p>}

              <div className="border border-emerald-500/30 bg-emerald-500/10 rounded-lg p-3 space-y-2">
                <p className="text-xs text-emerald-200 font-medium">Step 2: Use Browser Extension</p>
                <p className="text-xs text-emerald-100/90">
                  On the opened Codeforces tab, click the CPH extension icon and press Import Current Problem.
                </p>
                <p className="text-xs text-slate-300">
                  Extension folder: <span className="font-mono">extension/codeforces-importer</span>
                </p>
                <button
                  type="button"
                  onClick={() => syncLatestImportedProblem({ silent: false, closeOnSuccess: true })}
                  disabled={syncLoading}
                  className="text-xs px-2 py-1 rounded-lg border border-border bg-emerald-700/40 hover:bg-emerald-700/60 disabled:opacity-60 transition"
                >
                  {syncLoading ? 'Syncing...' : 'Sync Imported Problem'}
                </button>
              </div>

              <div className="border border-border rounded-lg p-3 bg-slate-800/60 space-y-2">
                <p className="text-xs text-slate-300 font-medium">First-time setup (once)</p>
                <p className="text-xs text-slate-400">1) Open Chrome Extensions page and enable Developer mode.</p>
                <p className="text-xs text-slate-400">2) Load unpacked extension from extension/codeforces-importer.</p>
                <p className="text-xs text-slate-400">3) Optional: login to Codeforces in browser if needed.</p>
                <button
                  type="button"
                  onClick={openCodeforcesLogin}
                  className="text-xs px-2 py-1 rounded-lg border border-border bg-slate-700/60 hover:bg-slate-600/80 transition"
                >
                  Open Codeforces Login
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}

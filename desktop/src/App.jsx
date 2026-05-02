import { useEffect, useMemo, useRef, useState } from 'react'
import ChatPanel from './components/ChatPanel.jsx'
import EditorPanel from './components/EditorPanel.jsx'
import FetchModal from './components/FetchModal.jsx'
import ProblemPanel from './components/ProblemPanel.jsx'
import TestCasePanel from './components/TestCasePanel.jsx'

// In Electron packaged builds, VITE_API_BASE is not baked in via import.meta.env.
// We resolve it at runtime from the main process via IPC (window.cpAPI.getApiBase).
// In the web app (Next.js / Vite dev), we use the env variable directly.
let API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8001'
if (window.cpAPI?.getApiBase) {
  window.cpAPI.getApiBase().then((base) => {
    if (base) API_BASE = base
  })
}

const problemData = {
  id: '',
  title: 'No problem loaded',
  difficulty: 'Medium',
  tags: ['Fetch Required'],
  description: 'Fetch/import a problem first to start solving.',
  constraints: 'No constraints available until a problem is fetched.',
  examples: 'No examples available until a problem is fetched.'
}

const starterCode = {
  cpp: `#include <bits/stdc++.h>
using namespace std;

int main() {
    return 0;
}`,
  python: `def main():
    pass

if __name__ == '__main__':
    main()`,
  java: `import java.util.*;

public class Main {
    public static void main(String[] args) {
    }
}`
}

function openExternal(url) {
  if (window.cpAPI?.openExternal) {
    window.cpAPI.openExternal(url)
  } else {
    window.open(url, '_blank', 'noopener,noreferrer')
  }
}

export default function App() {
  const editorRef = useRef(null)
  const chatScrollRef = useRef(null)
  const [language, setLanguage] = useState('cpp')
  const [code, setCode] = useState(starterCode.cpp)
  const [minimapEnabled, setMinimapEnabled] = useState(false)
  const [wordWrap, setWordWrap] = useState(false)
  const [leftWidth, setLeftWidth] = useState(50)
  const [leftTopHeight, setLeftTopHeight] = useState(68)
  const [rightTopHeight, setRightTopHeight] = useState(52)
  const [rightPanelOpen, setRightPanelOpen] = useState(true)
  const [runLoading, setRunLoading] = useState(false)
  const [runStatus, setRunStatus] = useState('')
  const [compileError, setCompileError] = useState('')
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
  const [workingDir, setWorkingDir] = useState('')
  const [saveStatus, setSaveStatus] = useState('')
  const [fetchTab, setFetchTab] = useState('search')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [topicsInput, setTopicsInput] = useState('dp, graphs')
  const [topicsLimit, setTopicsLimit] = useState('20')
  const [topicsMinRating, setTopicsMinRating] = useState('')
  const [topicsMaxRating, setTopicsMaxRating] = useState('')
  const [topicsResults, setTopicsResults] = useState([])
  const [topicsLoading, setTopicsLoading] = useState(false)
  const [randomTopicsInput, setRandomTopicsInput] = useState('')
  const [randomMinRating, setRandomMinRating] = useState('')
  const [randomMaxRating, setRandomMaxRating] = useState('')
  const [randomResult, setRandomResult] = useState(null)
  const [randomLoading, setRandomLoading] = useState(false)
  const [fetcherError, setFetcherError] = useState('')
  const [selectedProblem, setSelectedProblem] = useState(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)

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
    setCompileError('')
    setSaveStatus('')

    try {
      if (workingDir) {
        const folderName = problem.id || 'untitled_problem'
        const saveResult = await window.cpAPI?.saveProblemFiles?.({
          baseDir: workingDir,
          folderName,
          language,
          code,
          problem: {
            ...problem,
            source_url: problemUrl
          },
          testCases
        })
        if (saveResult?.error) {
          setSaveStatus(`Save error: ${saveResult.error}`)
        } else if (saveResult?.folderPath) {
          setSaveStatus(`Saved to ${saveResult.folderPath}`)
        }
      }

      if (testCases.length === 0) {
        setRunStatus('Error: No test cases')
        return
      }
      const res = await fetch(`${API_BASE}/api/code/run`, {
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
      setCompileError(data.compile_error || '')
      setTestCases((prev) =>
        prev.map((item) => {
          const result = byId.get(item.id)
          if (!result) return item
          return {
            ...item,
            output: result.output || '',
            status: result.status || 'Failed',
            error: result.error || ''
          }
        })
      )
      setRunStatus(data.error ? `Error: ${data.error}` : data.status || 'Completed')
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
    setCompileError('')
  }

  function addCase() {
    const nextId = testCases.length ? testCases[testCases.length - 1].id + 1 : 1
    const nextCase = { id: nextId, input: '', expected: '', output: '', error: '', status: 'Pending' }
    setTestCases((prev) => [...prev, nextCase])
    setActiveCaseId(nextId)
  }

  function updateCaseValue(id, field, value) {
    setTestCases((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item
        return { ...item, [field]: value }
      })
    )
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
    openExternal('https://codeforces.com/enter')
  }

  function openCodeforcesProblem() {
    setFetchError('')
    const url = problemUrl.trim()
    const pattern =
      /^https:\/\/(www\.)?codeforces\.com\/(contest|problemset\/problem)\/\d+\/(problem\/)?[A-Za-z][A-Za-z0-9]*/
    if (!pattern.test(url)) {
      setFetchError('Enter a valid Codeforces problem URL.')
      return
    }
    openExternal(url)
  }

  function problemIdFromUrl(url) {
    const match = url.match(
      /https:\/\/(?:www\.)?codeforces\.com\/(?:contest|problemset\/problem)\/(\d+)\/(?:problem\/)?([A-Za-z][A-Za-z0-9]*)/
    )
    if (!match) return ''
    return `${match[1]}_${match[2].toUpperCase()}`
  }

  function parseContestIndex(text) {
    const urlMatch = text.match(/codeforces\.com\/(?:contest|problemset\/problem)\/(\d+)\/(\w+)/i)
    if (urlMatch) return { contestId: Number(urlMatch[1]), index: urlMatch[2].toUpperCase() }
    const shortMatch = text.match(/\b(\d{3,5})([A-Za-z]\d?)\b/)
    if (shortMatch) return { contestId: Number(shortMatch[1]), index: shortMatch[2].toUpperCase() }
    return null
  }

  function buildProblemUrl(contestId, index) {
    return `https://codeforces.com/contest/${contestId}/problem/${String(index).toUpperCase()}`
  }

  function formatExamples(examples) {
    return (examples || [])
      .map(
        (example, idx) =>
          `Example ${idx + 1}\nInput:\n${example.input || ''}\nOutput:\n${example.output || ''}`
      )
      .join('\n\n')
  }

  async function saveProblemSnapshot(problemData, cases) {
    if (!workingDir) return
    const folderName = problemData.id || 'untitled_problem'
    const saveResult = await window.cpAPI?.saveProblemFiles?.({
      baseDir: workingDir,
      folderName,
      language,
      code,
      problem: {
        ...problemData,
        source_url: problemUrl
      },
      testCases: cases
    })
    if (saveResult?.error) {
      setSaveStatus(`Save error: ${saveResult.error}`)
    } else if (saveResult?.folderPath) {
      setSaveStatus(`Saved to ${saveResult.folderPath}`)
    }
  }

  async function fetchProblemDetail(contestId, index) {
    const res = await fetch(`${API_BASE}/api/problems/detail`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contest_id: contestId, index })
    })
    if (!res.ok) throw new Error('Unable to fetch problem detail')
    const data = await res.json()
    return data?.item
  }

  function applyProblemData(problemData, cases) {
    setProblem(problemData)
    setTestCases(cases)
    setActiveCaseId(cases.length ? cases[0].id : null)
    setRunStatus('')
    setCompileError('')
    setActiveTab('Input')
    setExpanded({ description: true, constraints: true, examples: true })
  }

  async function analyzeProblemStatement(problemData) {
    setAnalysisLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/problems/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: problemData.title || '',
          statement: problemData.description || '',
          constraints: problemData.constraints || '',
          examples: problemData.examples || ''
        })
      })
      if (!res.ok) return
      const data = await res.json()
      const parsed = data?.parsed
      if (!parsed) return
      setProblem((prev) => ({
        ...prev,
        description: parsed.description || prev.description,
        constraints: parsed.constraints || prev.constraints,
        examples: parsed.examples || prev.examples
      }))
    } catch {
      // silently ignore – the raw data is already loaded
    } finally {
      setAnalysisLoading(false)
    }
  }

  function applyImportedProblem(imported) {
    if (!imported) return
    const importedExamples = (imported.examples || []).map((example, index) => ({
      id: index + 1,
      input: example.input || '',
      expected: example.output || '',
      output: '',
      error: '',
      status: 'Pending'
    }))
    const next = {
      id: imported.id || '',
      title: imported.title || imported.id || 'Imported Problem',
      difficulty: imported.rating
        ? imported.rating <= 1200
          ? 'Easy'
          : imported.rating <= 1700
            ? 'Medium'
            : 'Hard'
        : 'Medium',
      tags: imported.tags?.length ? imported.tags : ['Codeforces'],
      description: imported.statement || 'Statement not available',
      constraints: imported.constraints || 'Constraints not explicitly listed in statement.',
      examples:
        (imported.examples || [])
          .map(
            (example, index) =>
              `Example ${index + 1}\nInput:\n${example.input || ''}\nOutput:\n${example.output || ''}`
          )
          .join('\n\n') || imported.source_url || 'N/A'
    }
    applyProblemData(next, importedExamples)
    saveProblemSnapshot(next, importedExamples)
    analyzeProblemStatement(next)
  }

  async function syncLatestImportedProblem(options = { silent: false, closeOnSuccess: false }) {
    const { silent, closeOnSuccess } = options
    if (!silent) setSyncLoading(true)
    try {
      const expectedId = problemIdFromUrl(problemUrl.trim())
      let imported = null

      if (expectedId) {
        const byIdRes = await fetch(`${API_BASE}/api/problems/import/${encodeURIComponent(expectedId)}`)
        if (!byIdRes.ok) throw new Error('Unable to read imported problem by id')
        const byIdData = await byIdRes.json()
        imported = byIdData?.item
      }

      if (!imported) {
        const res = await fetch(`${API_BASE}/api/problems/import/latest`)
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
      const res = await fetch(`${API_BASE}/api/chat`, {
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

  async function selectWorkingDirectory() {
    const selected = await window.cpAPI?.selectWorkingDirectory?.()
    if (selected) setWorkingDir(selected)
  }

  function normalizeTopics(input) {
    return input
      .split(/[\n,]/)
      .map((value) => value.trim())
      .filter(Boolean)
  }

  async function handleSearch() {
    const query = searchQuery.trim()
    if (!query) return
    setSearchLoading(true)
    setFetcherError('')
    try {
      const parsed = parseContestIndex(query)
      if (parsed) {
        const detail = await fetchProblemDetail(parsed.contestId, parsed.index)
        const item = {
          code: `${parsed.contestId}${parsed.index}`,
          contest_id: parsed.contestId,
          index: parsed.index,
          name: detail?.title || query,
          tags: detail?.tags || [],
          rating: detail?.rating,
          url: buildProblemUrl(parsed.contestId, parsed.index)
        }
        setSearchResults([item])
        return
      }

      const res = await fetch(`${API_BASE}/api/problems/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 12 })
      })
      if (!res.ok) throw new Error('Search failed')
      const data = await res.json()
      setSearchResults(data.items || [])
    } catch (error) {
      setFetcherError(String(error))
    } finally {
      setSearchLoading(false)
    }
  }

  async function handleTopicsSearch() {
    const topics = normalizeTopics(topicsInput)
    if (!topics.length) return
    setTopicsLoading(true)
    setFetcherError('')
    try {
      const res = await fetch(`${API_BASE}/api/problems/topics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topics,
          limit: Number(topicsLimit) || 20,
          min_rating: topicsMinRating ? Number(topicsMinRating) : null,
          max_rating: topicsMaxRating ? Number(topicsMaxRating) : null
        })
      })
      if (!res.ok) throw new Error('Topic search failed')
      const data = await res.json()
      setTopicsResults(data.items || [])
    } catch (error) {
      setFetcherError(String(error))
    } finally {
      setTopicsLoading(false)
    }
  }

  async function handleRandom() {
    setRandomLoading(true)
    setFetcherError('')
    try {
      const res = await fetch(`${API_BASE}/api/problems/random`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topics: normalizeTopics(randomTopicsInput),
          min_rating: randomMinRating ? Number(randomMinRating) : null,
          max_rating: randomMaxRating ? Number(randomMaxRating) : null,
          user_data: null
        })
      })
      if (!res.ok) throw new Error('Random fetch failed')
      const data = await res.json()
      setRandomResult(data.item || null)
    } catch (error) {
      setFetcherError(String(error))
    } finally {
      setRandomLoading(false)
    }
  }

  async function handleSelectProblem(item) {
    if (!item) return
    setFetcherError('')
    setSelectedProblem(item)
    const contestId = item.contest_id
    const index = item.index
    const url = item.url || (contestId && index ? buildProblemUrl(contestId, index) : '')
    if (url) {
      setProblemUrl(url)
      openExternal(url)
    }
    if (contestId && index) {
      try {
        const detail = await fetchProblemDetail(contestId, index)
        if (detail) {
          const description = detail.statement || 'Statement not available.'
          const constraints = [detail.time_limit, detail.memory_limit]
            .filter(Boolean)
            .join(' | ') ||
            (detail.rating ? `rating=${detail.rating}` : '')
          const examplesText = formatExamples(detail.examples)
          const cases = (detail.examples || []).map((example, idx) => ({
            id: idx + 1,
            input: example.input || '',
            expected: example.output || '',
            output: '',
            error: '',
            status: 'Pending'
          }))
          const problemData = {
            id: `${contestId}_${String(index).toUpperCase()}`,
            title: detail.title || item.name || 'Codeforces Problem',
            difficulty: detail.rating
              ? detail.rating <= 1200
                ? 'Easy'
                : detail.rating <= 1700
                  ? 'Medium'
                  : 'Hard'
              : 'Medium',
            tags: detail.tags || item.tags || ['Codeforces'],
            description,
            constraints: constraints || 'Constraints not explicitly listed in statement.',
            examples: examplesText || 'No examples available.'
          }
          applyProblemData(problemData, cases)
          saveProblemSnapshot(problemData, cases)
          analyzeProblemStatement(problemData)
        }
      } catch (error) {
        setFetcherError(String(error))
      }
    }
  }

  const fileName = useMemo(() => {
    if (language === 'python') return 'main.py'
    if (language === 'java') return 'Main.java'
    return 'main.cpp'
  }, [language])

  return (
    <main className="app-root">
      <div className="layout">
        <div className="pane" style={{ width: `${layoutLeftWidth}%` }}>
          <div className="stack">
            <div className="stack-item" style={{ height: `${leftTopHeight}%` }}>
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

            <div className="drag-handle horizontal" onMouseDown={beginDrag('left-split')} />

            <div className="stack-item" style={{ height: `${100 - leftTopHeight}%` }}>
              <TestCasePanel
                testCases={testCases}
                activeCaseId={activeCaseId}
                onSelectCase={setActiveCaseId}
                onAddCase={addCase}
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                onUpdateCase={updateCaseValue}
                runStatus={runStatus}
                compileError={compileError}
              />
            </div>
          </div>
        </div>

        {rightPanelOpen && (
          <>
            <div className="drag-handle vertical" onMouseDown={beginDrag('main-split')} />
            <div className="pane" style={{ width: `${100 - leftWidth}%` }}>
              <div className="stack">
                <div className="stack-item" style={{ height: `${rightTopHeight}%` }}>
                  {workingDir ? (
                    <ProblemPanel
                      problem={problem}
                      expanded={expanded}
                      onToggleSection={toggleSection}
                      onCopyExample={copyExample}
                      onOpenFetch={() => {
                        setFetchError('')
                        setIsFetchModalOpen(true)
                      }}
                      analysisLoading={analysisLoading}
                    />
                  ) : (
                    <section className="panel shell">
                      <header className="panel-header sticky">
                        <div className="panel-header-left">
                          <h2>CP Assistant</h2>
                        </div>
                      </header>
                      <div className="panel-body scrollable">
                        <div className="welcome">
                          <p className="welcome-title">Select a working folder to begin.</p>
                          <p className="welcome-text">
                            Your problem details, test cases, and code will be saved into a folder per question.
                          </p>
                          <button type="button" className="primary" onClick={selectWorkingDirectory}>
                            Open Folder
                          </button>
                        </div>
                      </div>
                    </section>
                  )}
                </div>

                <div className="drag-handle horizontal" onMouseDown={beginDrag('right-split')} />

                <div className="stack-item" style={{ height: `${100 - rightTopHeight}%` }}>
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

      <FetchModal
        isOpen={isFetchModalOpen}
        onClose={() => setIsFetchModalOpen(false)}
        activeTab={fetchTab}
        onChangeTab={setFetchTab}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        searchResults={searchResults}
        searchLoading={searchLoading}
        onSearch={handleSearch}
        topicsInput={topicsInput}
        setTopicsInput={setTopicsInput}
        topicsLimit={topicsLimit}
        setTopicsLimit={setTopicsLimit}
        topicsMinRating={topicsMinRating}
        setTopicsMinRating={setTopicsMinRating}
        topicsMaxRating={topicsMaxRating}
        setTopicsMaxRating={setTopicsMaxRating}
        topicsResults={topicsResults}
        topicsLoading={topicsLoading}
        onTopicsSearch={handleTopicsSearch}
        randomTopicsInput={randomTopicsInput}
        setRandomTopicsInput={setRandomTopicsInput}
        randomMinRating={randomMinRating}
        setRandomMinRating={setRandomMinRating}
        randomMaxRating={randomMaxRating}
        setRandomMaxRating={setRandomMaxRating}
        randomResult={randomResult}
        randomLoading={randomLoading}
        onRandom={handleRandom}
        onSelectProblem={handleSelectProblem}
        problemUrl={problemUrl}
        setProblemUrl={setProblemUrl}
        onOpenProblem={openCodeforcesProblem}
        onSync={() => syncLatestImportedProblem({ silent: false, closeOnSuccess: true })}
        onOpenLogin={openCodeforcesLogin}
        syncLoading={syncLoading}
        fetchError={fetchError}
        fetcherError={fetcherError}
        selectedProblem={selectedProblem}
      />
    </main>
  )
}

import { useEffect, useMemo, useRef, useState } from 'react'
import EditorPanel from '../components/EditorPanel'
import TestCasePanel from '../components/TestCasePanel'
import ProblemPanel from '../components/ProblemPanel'
import ChatPanel from '../components/ChatPanel'

const problemData = {
  title: 'Two Sum',
  difficulty: 'Easy',
  tags: ['Arrays', 'Hash Map'],
  description:
    'Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume each input would have exactly one solution, and you may not use the same element twice.',
  constraints: '2 ≤ nums.length ≤ 10^4\n-10^9 ≤ nums[i] ≤ 10^9\n-10^9 ≤ target ≤ 10^9\nOnly one valid answer exists.',
  examples:
    'Input: nums = [2,7,11,15], target = 9\nOutput: [0,1]\n\nInput: nums = [3,2,4], target = 6\nOutput: [1,2]'
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
  const [testCases, setTestCases] = useState([
    { id: 1, input: '2 7 11 15\n9', expected: '[0,1]', output: '', status: 'Pending' },
    { id: 2, input: '3 2 4\n6', expected: '[1,2]', output: '', status: 'Pending' }
  ])
  const [activeCaseId, setActiveCaseId] = useState(1)
  const [expanded, setExpanded] = useState({ description: true, constraints: true, examples: true })
  const [messages, setMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)

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

  function runCode() {
    setRunLoading(true)
    setRunStatus('Running...')
    window.setTimeout(() => {
      if (testCases.length === 0) {
        setRunLoading(false)
        setRunStatus('Error: No test cases')
        return
      }
      const solvedLikely = /(hash|map|dict|unordered_map|return\s*\[)/i.test(code)
      const next = testCases.map((item) => {
        const passed = solvedLikely || item.id % 2 === 0
        const output = passed ? item.expected : '[-1,-1]'
        return { ...item, status: passed ? 'Passed' : 'Failed', output }
      })
      const allPassed = next.every((item) => item.status === 'Passed')
      setTestCases(next)
      setRunLoading(false)
      setRunStatus(allPassed ? 'Accepted' : 'Wrong Answer')
      setActiveTab('Diff')
    }, 1200)
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
      await navigator.clipboard.writeText(problemData.examples)
    } catch {
      return
    }
  }

  function streamAssistantResponse(prompt) {
    setIsTyping(true)
    const answer = `Here is a focused direction for: ${prompt}\n\n1. Use a hash map to track visited values.\n2. For each value x, check if target - x exists.\n3. Return indices immediately once found.\n\n\`\`\`python\ndef two_sum(nums, target):\n    seen = {}\n    for i, x in enumerate(nums):\n        if target - x in seen:\n            return [seen[target - x], i]\n        seen[x] = i\n\`\`\``

    const id = Date.now() + 1
    setMessages((prev) => [...prev, { id, role: 'assistant', content: '' }])
    let index = 0
    const timer = window.setInterval(() => {
      index += 3
      setMessages((prev) =>
        prev.map((item) => (item.id === id ? { ...item, content: answer.slice(0, index) } : item))
      )
      if (index >= answer.length) {
        window.clearInterval(timer)
        setIsTyping(false)
      }
    }, 20)
  }

  function sendChat(text) {
    const prompt = text.trim()
    if (!prompt) return
    const userMessage = { id: Date.now(), role: 'user', content: prompt }
    setMessages((prev) => [...prev, userMessage])
    setChatInput('')
    streamAssistantResponse(prompt)
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
                    problem={problemData}
                    expanded={expanded}
                    onToggleSection={toggleSection}
                    onCopyExample={copyExample}
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
    </main>
  )
}

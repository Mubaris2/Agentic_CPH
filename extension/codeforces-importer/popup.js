const apiBaseInput = document.getElementById('apiBase')
const importBtn = document.getElementById('importBtn')
const statusEl = document.getElementById('status')

function setStatus(message, color = '#cbd5e1') {
  statusEl.textContent = message
  statusEl.style.color = color
}

function isProblemUrl(url) {
  return /https:\/\/(www\.)?codeforces\.com\/(contest|problemset\/problem)\/\d+\/(problem\/)?[A-Za-z][A-Za-z0-9]*/.test(url)
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true })
  return tabs[0]
}

async function extractFromContentScript(tabId) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, { type: 'CPH_EXTRACT_PROBLEM' }, (response) => {
      const runtimeError = chrome.runtime.lastError
      if (runtimeError) {
        reject(new Error(runtimeError.message))
        return
      }
      if (!response?.ok) {
        reject(new Error(response?.error || 'Failed to extract problem content'))
        return
      }
      resolve(response.payload)
    })
  })
}

async function extractViaScripting(tabId) {
  const [result] = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      const normalizeText = (value) => (value || '')
        .replace(/\u00a0/g, ' ')
        .replace(/\r/g, '')
        .replace(/[ \t]+\n/g, '\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim()

      const textFromNode = (node) => {
        if (!node) return ''
        return normalizeText(node.innerText || node.textContent || '')
      }

      const getText = (selectors) => {
        for (const selector of selectors) {
          const node = document.querySelector(selector)
          if (node) return textFromNode(node)
        }
        return ''
      }

      const match = window.location.pathname.match(/\/(contest|problemset\/problem)\/(\d+)\/(?:problem\/)?([A-Za-z][A-Za-z0-9]*)/)
      if (!match) {
        throw new Error('Not on a supported Codeforces problem URL.')
      }

      const examples = []
      const sampleTests = document.querySelectorAll('.sample-tests .sample-test')
      sampleTests.forEach((test) => {
        const inputNodes = test.querySelectorAll('.input pre')
        const outputNodes = test.querySelectorAll('.output pre')
        const pairCount = Math.max(inputNodes.length, outputNodes.length)
        for (let index = 0; index < pairCount; index += 1) {
          examples.push({
            input: textFromNode(inputNodes[index]),
            output: textFromNode(outputNodes[index]),
          })
        }
      })

      const extractDescriptionAndConstraints = () => {
        const root = document.querySelector('.problem-statement')
        if (!root) {
          return { statement: '', constraints: '' }
        }

        const clone = root.cloneNode(true)
        clone.querySelectorAll('.header, .input-specification, .input-spec, .output-specification, .output-spec, .sample-tests').forEach((node) => node.remove())

        const constraintsNodes = Array.from(clone.querySelectorAll('p, div')).filter((node) => {
          const t = textFromNode(node).toLowerCase()
          return t.startsWith('constraints') || t.includes('constraints:')
        })

        const constraintsText = constraintsNodes.map((node) => textFromNode(node)).filter(Boolean).join('\n')
        constraintsNodes.forEach((node) => node.remove())

        return {
          statement: textFromNode(clone),
          constraints: constraintsText,
        }
      }

      const tagNodes = document.querySelectorAll('.tag-box')
      const tags = Array.from(tagNodes)
        .map((node) => (node.textContent || '').replace(/\s+/g, ' ').trim())
        .filter(Boolean)

      const contestId = match[2]
      const index = match[3].toUpperCase()
      const extracted = extractDescriptionAndConstraints()

      return {
        id: `${contestId}_${index}`,
        platform: 'codeforces',
        title: getText(['.problem-statement .header .title', '.title']) || `${contestId}_${index}`,
        time_limit: getText(['.problem-statement .header .time-limit', '.time-limit']),
        memory_limit: getText(['.problem-statement .header .memory-limit', '.memory-limit']),
        statement: extracted.statement,
        constraints: extracted.constraints,
        input: getText(['.problem-statement .input-specification', '.input-specification', '.input-spec']),
        output: getText(['.problem-statement .output-specification', '.output-specification', '.output-spec']),
        examples,
        source_url: window.location.href,
        tags,
        rating: null,
        created_at: new Date().toISOString(),
      }
    },
  })

  if (!result) {
    throw new Error('Could not execute scraper on this tab.')
  }

  return result.result
}

async function extractFromTab(tabId) {
  try {
    return await extractFromContentScript(tabId)
  } catch (error) {
    const message = String(error)
    if (!message.includes('Receiving end does not exist')) {
      throw error
    }
    return extractViaScripting(tabId)
  }
}

async function importProblem(apiBase, payload) {
  const res = await fetch(`${apiBase}/api/problems/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (res.status === 409) {
    return { already: true }
  }

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`Import failed (${res.status}): ${body}`)
  }

  return { already: false }
}

async function init() {
  const stored = await chrome.storage.sync.get(['cph_api_base'])
  apiBaseInput.value = stored.cph_api_base || 'http://localhost:8000'
}

apiBaseInput.addEventListener('change', async () => {
  await chrome.storage.sync.set({ cph_api_base: apiBaseInput.value.trim() })
})

importBtn.addEventListener('click', async () => {
  const apiBase = apiBaseInput.value.trim()
  if (!apiBase) {
    setStatus('Set backend URL first.', '#fca5a5')
    return
  }

  importBtn.disabled = true
  setStatus('Importing...', '#93c5fd')

  try {
    const tab = await getActiveTab()
    if (!tab?.id || !tab.url) {
      throw new Error('No active tab found.')
    }

    if (!isProblemUrl(tab.url)) {
      throw new Error('Open a Codeforces problem page first.')
    }

    const payload = await extractFromTab(tab.id)
    const result = await importProblem(apiBase, payload)

    if (result.already) {
      setStatus('Already imported.', '#fcd34d')
      return
    }

    setStatus('Imported successfully.', '#86efac')
  } catch (error) {
    setStatus(String(error), '#fca5a5')
  } finally {
    importBtn.disabled = false
  }
})

init().catch((error) => setStatus(String(error), '#fca5a5'))

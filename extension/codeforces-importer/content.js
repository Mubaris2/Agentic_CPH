function normalizeText(value) {
  return (value || '')
    .replace(/\u00a0/g, ' ')
    .replace(/\r/g, '')
    .replace(/[ \t]+\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function textFromNode(node) {
  if (!node) return ''
  return normalizeText(node.innerText || node.textContent || '')
}

function getText(selectors) {
  for (const selector of selectors) {
    const node = document.querySelector(selector)
    if (node) {
      return textFromNode(node)
    }
  }
  return ''
}

function parseProblemPath(pathname) {
  const match = pathname.match(/\/(contest|problemset\/problem)\/(\d+)\/(?:problem\/)?([A-Za-z][A-Za-z0-9]*)/)
  if (!match) return null
  return {
    contestId: match[2],
    index: match[3].toUpperCase(),
  }
}

function extractExamples() {
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
  return examples
}

function extractDescriptionAndConstraints() {
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

function extractProblemPayload() {
  const parsed = parseProblemPath(window.location.pathname)
  if (!parsed) {
    throw new Error('Not on a supported Codeforces problem URL.')
  }

  const title = getText(['.problem-statement .header .title', '.title'])
  const timeLimit = getText(['.problem-statement .header .time-limit', '.time-limit'])
  const memoryLimit = getText(['.problem-statement .header .memory-limit', '.memory-limit'])
  const { statement, constraints } = extractDescriptionAndConstraints()
  const inputSpec = getText(['.problem-statement .input-specification', '.input-specification', '.input-spec'])
  const outputSpec = getText(['.problem-statement .output-specification', '.output-specification', '.output-spec'])

  const tagNodes = document.querySelectorAll('.tag-box')
  const tags = Array.from(tagNodes)
    .map((node) => (node.textContent || '').replace(/\s+/g, ' ').trim())
    .filter(Boolean)

  const id = `${parsed.contestId}_${parsed.index}`

  return {
    id,
    platform: 'codeforces',
    title: title || id,
    time_limit: timeLimit,
    memory_limit: memoryLimit,
    statement,
    constraints,
    input: inputSpec,
    output: outputSpec,
    examples: extractExamples(),
    source_url: window.location.href,
    tags,
    rating: null,
    created_at: new Date().toISOString(),
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'CPH_EXTRACT_PROBLEM') return

  try {
    const payload = extractProblemPayload()
    sendResponse({ ok: true, payload })
  } catch (error) {
    sendResponse({ ok: false, error: String(error) })
  }

  return true
})

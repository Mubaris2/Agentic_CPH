const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron')
const path = require('path')
const fs = require('fs/promises')
const os = require('os')
const { exec } = require('child_process')

const API_BASE = process.env.VITE_API_BASE || 'http://localhost:8001'

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173'

function quotePath(value) {
  return `"${value.replace(/"/g, '\\"')}"`
}

function execCommand(command, options, stdin) {
  return new Promise((resolve) => {
    const child = exec(command, options, (error, stdout, stderr) => {
      resolve({ error, stdout, stderr })
    })

    if (stdin) {
      child.stdin?.end(stdin)
    } else {
      child.stdin?.end()
    }
  })
}

function sanitizeFolderName(name) {
  const safe = String(name || '')
    .trim()
    .replace(/[\\/]/g, '_')
    .replace(/[^a-zA-Z0-9._-]/g, '_')
    .slice(0, 80)
  return safe || 'untitled_problem'
}

async function runCpp(code, stdin) {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'cp-assistant-'))
  const sourcePath = path.join(tempDir, 'main.cpp')
  const outputPath = path.join(tempDir, 'main.out')

  try {
    await fs.writeFile(sourcePath, code, 'utf8')
    const compile = await execCommand(
      `g++ -std=c++17 -O2 -pipe -o ${quotePath(outputPath)} ${quotePath(sourcePath)}`,
      { timeout: 10000, maxBuffer: 1024 * 1024 },
      ''
    )

    if (compile.error) {
      return {
        stdout: '',
        stderr: compile.stderr || '',
        compileError: compile.stderr || 'Compilation failed.'
      }
    }

    const run = await execCommand(quotePath(outputPath), { timeout: 5000, maxBuffer: 1024 * 1024 }, stdin)
    return {
      stdout: run.stdout || '',
      stderr: run.stderr || '',
      compileError: ''
    }
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true })
  }
}

async function runPython(code, stdin) {
  const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'cp-assistant-'))
  const sourcePath = path.join(tempDir, 'main.py')

  try {
    await fs.writeFile(sourcePath, code, 'utf8')
    const run = await execCommand(
      `python ${quotePath(sourcePath)}`,
      { timeout: 5000, maxBuffer: 1024 * 1024 },
      stdin
    )

    return {
      stdout: run.stdout || '',
      stderr: run.stderr || '',
      compileError: ''
    }
  } finally {
    await fs.rm(tempDir, { recursive: true, force: true })
  }
}

ipcMain.handle('run-code', async (_event, payload) => {
  try {
    const { code, language, stdin = '' } = payload || {}
    if (!code || !language) {
      return { stdout: '', stderr: 'Missing code or language.', compileError: '' }
    }

    if (language === 'cpp') {
      return await runCpp(code, stdin)
    }

    if (language === 'python') {
      return await runPython(code, stdin)
    }

    return { stdout: '', stderr: `Unsupported language: ${language}`, compileError: '' }
  } catch (error) {
    return { stdout: '', stderr: String(error), compileError: '' }
  }
})

ipcMain.handle('open-external', async (_event, payload) => {
  const url = payload?.url
  if (typeof url === 'string' && url.startsWith('http')) {
    await shell.openExternal(url)
  }
})

ipcMain.handle('get-api-base', () => API_BASE)

ipcMain.handle('select-working-directory', async () => {
  const result = await dialog.showOpenDialog({ properties: ['openDirectory'] })
  if (result.canceled || !result.filePaths?.length) return null
  return result.filePaths[0]
})

ipcMain.handle('save-problem-files', async (_event, payload) => {
  try {
    const baseDir = payload?.baseDir
    if (!baseDir) return { error: 'Working directory is not set.' }

    const folderName = sanitizeFolderName(payload?.folderName)
    const targetDir = path.join(baseDir, folderName)
    await fs.mkdir(targetDir, { recursive: true })

    const language = payload?.language || 'cpp'
    const codeFile = language === 'python' ? 'main.py' : language === 'java' ? 'Main.java' : 'main.cpp'
    const problemFile = path.join(targetDir, 'problem.json')
    const testcasesFile = path.join(targetDir, 'testcases.json')
    const codePath = path.join(targetDir, codeFile)

    await Promise.all([
      fs.writeFile(problemFile, JSON.stringify(payload?.problem || {}, null, 2), 'utf8'),
      fs.writeFile(testcasesFile, JSON.stringify(payload?.testCases || [], null, 2), 'utf8'),
      fs.writeFile(codePath, String(payload?.code || ''), 'utf8')
    ])

    return { folderPath: targetDir }
  } catch (error) {
    return { error: String(error) }
  }
})

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    backgroundColor: '#0f1115',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      // Allow file:// pages to fetch http://localhost:* without CORS errors.
      // Safe because this app only talks to the local FastAPI backend.
      webSecurity: false
    }
  })

  if (app.isPackaged) {
    win.loadFile(path.join(__dirname, 'dist', 'index.html'))
  } else {
    win.loadURL(DEV_SERVER_URL)
    win.webContents.openDevTools({ mode: 'detach' })
  }
}

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

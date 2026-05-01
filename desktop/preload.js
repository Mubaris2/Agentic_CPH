const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('cpAPI', {
  runCode: (code, language, stdin = '') => ipcRenderer.invoke('run-code', { code, language, stdin }),
  openExternal: (url) => ipcRenderer.invoke('open-external', { url }),
  selectWorkingDirectory: () => ipcRenderer.invoke('select-working-directory'),
  saveProblemFiles: (payload) => ipcRenderer.invoke('save-problem-files', payload)
})

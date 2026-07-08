// Smart Scribe - Electron preload script
// Exposes a minimal API to the renderer for theme + desktop detection.

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("smartScribe", {
  version: "0.1.0",
  platform: process.platform,
  isDesktop: true,
  setTheme: (isDark) => ipcRenderer.send("set-theme", isDark),
  onStartupStatus: (callback) => {
    ipcRenderer.on("startup-status", (_event, payload) => callback(payload));
  },
  getStartupStatus: () => ipcRenderer.invoke("get-startup-status"),
  onCloseRequest: (callback) => {
    const handler = () => callback();
    ipcRenderer.on("desktop-close-request", handler);
    return () => ipcRenderer.removeListener("desktop-close-request", handler);
  },
  chooseCloseAction: (action, options = {}) => ipcRenderer.send("desktop-close-action", { action, ...options }),
});

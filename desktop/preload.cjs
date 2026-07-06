// Smart Scribe - Electron preload script
// Exposes a minimal API to the renderer for theme + desktop detection.

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("smartScribe", {
  version: "0.1.0",
  platform: process.platform,
  isDesktop: true,
  setTheme: (isDark) => ipcRenderer.send("set-theme", isDark),
});

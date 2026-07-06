// Smart Scribe - Electron preload script
// contextBridge exposes a minimal API to the renderer (currently empty,
// but kept for future use such as file drag-drop or native dialogs).

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("smartScribe", {
  version: "0.1.0",
  platform: process.platform,
});

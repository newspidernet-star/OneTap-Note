// Smart Scribe - Electron main process
//
// Responsibilities:
//   1. Ensure backend dependencies are installed (first run).
//   2. Launch the FastAPI backend via PowerShell with SMART_SCRIBE_NO_BROWSER=1.
//   3. Poll /api/health until the backend is ready.
//   4. Create a BrowserWindow loading http://127.0.0.1:8000.
//   5. Kill the backend subprocess when the window closes.

const { app, BrowserWindow, dialog } = require("electron");
const { spawn, exec } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const http = require("node:http");

let backendProcess = null;
let mainWindow = null;
let healthPollTimer = null;

const BACKEND_URL = "http://127.0.0.1:8000";
const HEALTH_TIMEOUT_MS = 120_000;
const HEALTH_POLL_INTERVAL_MS = 1000;

function getProjectRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "app");
  }
  return path.resolve(__dirname, "..");
}

function isBackendInstalled(root) {
  const pyExe = path.join(root, "backend", ".venv", "Scripts", "python.exe");
  const distIndex = path.join(root, "frontend", "dist", "index.html");
  return fs.existsSync(pyExe) && fs.existsSync(distIndex);
}

function runSetupScript(root) {
  return new Promise((resolve, reject) => {
    const setupScript = path.join(root, "scripts", "setup-windows.ps1");
    const child = spawn(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", setupScript],
      { cwd: root, stdio: ["ignore", "pipe", "pipe"], windowsHide: true }
    );
    child.stdout.on("data", (data) => console.log("[setup] " + data.toString().trim()));
    child.stderr.on("data", (data) => console.error("[setup:error] " + data.toString().trim()));
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error("Setup script exited with code " + code));
    });
    child.on("error", (err) => reject(err));
  });
}

async function ensureInstalled(root) {
  if (isBackendInstalled(root)) return;
  const choice = dialog.showMessageBoxSync({
    type: "info",
    title: "Smart Scribe",
    message: "首次启动需要安装依赖，可能需要几分钟。",
    detail: "如果网络较慢，请确保代理 127.0.0.1:7897 可用，或稍后重试。",
    buttons: ["开始安装", "退出"],
    defaultId: 0,
    cancelId: 1,
  });
  if (choice === 1) { app.quit(); return; }
  try {
    await runSetupScript(root);
  } catch (err) {
    dialog.showErrorBox("Smart Scribe - 安装失败",
      "依赖安装失败：\n" + err.message + "\n\n请尝试手动运行 scripts\\setup-windows.ps1");
    app.quit();
  }
}

function startBackend(root) {
  const startScript = path.join(root, "scripts", "start-windows.ps1");
  backendProcess = spawn(
    "powershell.exe",
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", startScript],
    {
      cwd: root,
      env: { ...process.env, SMART_SCRIBE_NO_BROWSER: "1" },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: false,
    }
  );
  backendProcess.stdout.on("data", (data) => console.log("[backend] " + data.toString().trim()));
  backendProcess.stderr.on("data", (data) => console.error("[backend:error] " + data.toString().trim()));
  backendProcess.on("close", (code) => {
    console.log("[backend] process exited with code " + code);
    backendProcess = null;
  });
}

function checkHealth() {
  return new Promise((resolve) => {
    const req = http.get(BACKEND_URL + "/api/health", (res) => {
      resolve(res.statusCode === 200);
      res.resume();
    });
    req.on("error", () => resolve(false));
    req.setTimeout(3000, () => { req.destroy(); resolve(false); });
  });
}

function waitForHealth(timeoutMs) {
  timeoutMs = timeoutMs || HEALTH_TIMEOUT_MS;
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    healthPollTimer = setInterval(async () => {
      const ok = await checkHealth();
      if (ok) { clearInterval(healthPollTimer); healthPollTimer = null; resolve(); }
      else if (Date.now() > deadline) {
        clearInterval(healthPollTimer); healthPollTimer = null;
        reject(new Error("Backend did not become healthy in time"));
      }
    }, HEALTH_POLL_INTERVAL_MS);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 860, minWidth: 980, minHeight: 640,
    title: "Smart Scribe",
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.loadURL(BACKEND_URL);
  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.on("closed", () => { mainWindow = null; });
}

function killBackend() {
  if (healthPollTimer) { clearInterval(healthPollTimer); healthPollTimer = null; }
  if (backendProcess && !backendProcess.killed) {
    try {
      exec("taskkill /PID " + backendProcess.pid + " /T /F", () => {});
    } catch {
      try { backendProcess.kill(); } catch (e) {}
    }
    backendProcess = null;
  }
}

app.whenReady().then(async () => {
  const root = getProjectRoot();
  await ensureInstalled(root);
  startBackend(root);
  try {
    await waitForHealth();
  } catch (err) {
    dialog.showErrorBox("Smart Scribe - 启动失败",
      "后端服务未能启动：\n" + err.message + "\n\n请尝试双击 start-windows.bat 启动，或检查日志。");
    killBackend();
    app.quit();
    return;
  }
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  killBackend();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => { killBackend(); });
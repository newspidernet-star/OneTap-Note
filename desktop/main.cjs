// Smart Scribe - Electron main process

const { app, BrowserWindow, dialog, ipcMain, Menu, nativeImage, Tray } = require("electron");
const { spawn, exec } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const http = require("node:http");

let backendProcess = null;
let mainWindow = null;
let tray = null;
let healthPollTimer = null;
let isQuiting = false;
let lastStartupStatus = null;

const BACKEND_URL = "http://127.0.0.1:8000";
const HEALTH_TIMEOUT_MS = 120_000;
const HEALTH_POLL_INTERVAL_MS = 300;
const MIN_SPLASH_MS = 900;

// Use hex colors here. Windows titleBarOverlay may fall back to white with
// some CSS color syntaxes, which makes the caption buttons look detached.
const THEME = {
  dark:  { bg: "#1B2220", symbol: "#E2EAE5" },
  light: { bg: "#FAFAFA", symbol: "#1B2724" },
};

const gotSingleInstanceLock = app.requestSingleInstanceLock();
if (!gotSingleInstanceLock) {
  app.exit(0);
}

const SETUP_STEPS = [
  { pattern: /Proxy detected|No proxy detected/i, title: "检测网络代理", progress: 8 },
  { pattern: /Python|Python\.Python/i, title: "检查 Python 运行环境", progress: 18 },
  { pattern: /NodeJS|Node\.js|OpenJS/i, title: "检查 Node.js", progress: 28 },
  { pattern: /FFmpeg|ffmpeg/i, title: "检查 ffmpeg", progress: 38 },
  { pattern: /cloudflared/i, title: "检查 cloudflared", progress: 48 },
  { pattern: /Creating venv|backend\\\.venv/i, title: "创建后端虚拟环境", progress: 58 },
  { pattern: /Installing backend deps|pip install/i, title: "安装后端依赖", progress: 68 },
  { pattern: /Playwright/i, title: "安装浏览器内核", progress: 78 },
  { pattern: /npm install/i, title: "安装前端依赖", progress: 86 },
  { pattern: /Building frontend|npm run build/i, title: "构建前端页面", progress: 94 },
  { pattern: /Setup Complete/i, title: "安装完成", progress: 100 },
];

function sendStartupStatus(payload) {
  lastStartupStatus = payload;
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send("startup-status", payload);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function setupStatusFromLine(line) {
  const text = line.trim();
  if (!text) return null;
  const step = SETUP_STEPS.find((item) => item.pattern.test(text));
  if (step) {
    return { mode: "install", title: step.title, detail: text, progress: step.progress };
  }
  return { mode: "install", detail: text };
}

function getProjectRoot() {
  if (app.isPackaged) {
    const exeDir = path.dirname(app.getPath("exe"));
    const localRoot = path.resolve(exeDir, "..", "..", "..");
    if (fs.existsSync(path.join(localRoot, "backend", ".venv", "Scripts", "python.exe"))) {
      return localRoot;
    }
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
    sendStartupStatus({
      mode: "install",
      title: "准备安装",
      detail: "正在检查 Smart Scribe 运行环境",
      progress: 3,
    });
    const child = spawn(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", setupScript],
      { cwd: root, stdio: ["ignore", "pipe", "pipe"], windowsHide: true }
    );
    child.stdout.on("data", (data) => {
      const text = data.toString().trim();
      console.log("[setup] " + text);
      for (const line of text.split(/\r?\n/)) {
        const status = setupStatusFromLine(line);
        if (status) sendStartupStatus(status);
      }
    });
    child.stderr.on("data", (data) => {
      const text = data.toString().trim();
      console.error("[setup:error] " + text);
      if (text) sendStartupStatus({ mode: "install", detail: text });
    });
    child.on("close", (code) => {
      if (code === 0) {
        sendStartupStatus({ mode: "install", title: "安装完成", detail: "正在启动应用服务", progress: 100 });
        resolve();
      }
      else reject(new Error("Setup script exited with code " + code));
    });
    child.on("error", (err) => reject(err));
  });
}

async function ensureInstalled(root) {
  if (isBackendInstalled(root)) return;
  sendStartupStatus({
    mode: "install",
    title: "首次安装",
    detail: "正在为 Smart Scribe 准备运行环境，可能需要几分钟",
    progress: 0,
  });
  try {
    await runSetupScript(root);
  } catch (err) {
    dialog.showErrorBox("Smart Scribe - 安装失败",
      "依赖安装失败：\n" + err.message + "\n\n请尝试手动运行 scripts\\setup-windows.ps1");
    app.quit();
  }
}

function startBackend(root) {
  sendStartupStatus({
    mode: "launch",
    title: "正在启动服务",
    detail: "正在启动本地后端，请稍等",
  });
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
  backendProcess.stdout.on("data", (data) => {
    const text = data.toString().trim();
    console.log("[backend] " + text);
    if (/Uvicorn running|Application startup complete/i.test(text)) {
      sendStartupStatus({ mode: "launch", title: "服务已启动", detail: "正在打开工作台" });
    }
  });
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
    req.setTimeout(2000, () => { req.destroy(); resolve(false); });
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

function applyTitleBarTheme(isDark) {
  const t = isDark ? THEME.dark : THEME.light;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.setTitleBarOverlay({ color: t.bg, symbolColor: t.symbol, height: 48 });
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 860, minWidth: 980, minHeight: 640,
    title: "Smart Scribe",
    show: false,
    autoHideMenuBar: true,
    backgroundColor: THEME.dark.bg,
    titleBarStyle: "hidden",
    titleBarOverlay: {
      color: THEME.dark.bg,
      symbolColor: THEME.dark.symbol,
      height: 48,
    },
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.once("ready-to-show", () => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.show();
  });
  mainWindow.loadFile(path.join(__dirname, "loading.html")).catch((err) => {
    console.error("[desktop] loading screen failed:", err);
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.show();
  });

  mainWindow.on("close", (event) => {
    if (isQuiting) return;
    event.preventDefault();
    const choice = dialog.showMessageBoxSync(mainWindow, {
      type: "question",
      title: "Smart Scribe",
      message: "要关闭 Smart Scribe 吗？",
      detail: "隐藏到系统托盘会保留后台服务，下次打开更快；直接退出会关闭本地后端。",
      buttons: ["隐藏到系统托盘", "直接退出", "取消"],
      defaultId: 0,
      cancelId: 2,
    });
    if (choice === 0) {
      createTray();
      mainWindow.hide();
    } else if (choice === 1) {
      isQuiting = true;
      app.quit();
    }
  });

  mainWindow.on("closed", () => { mainWindow = null; });
}

function createTrayIcon() {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
      <rect width="32" height="32" rx="8" fill="#1B2220"/>
      <path d="M16 5l2.1 6.9L25 14l-6.9 2.1L16 23l-2.1-6.9L7 14l6.9-2.1L16 5z" fill="#E2EAE5"/>
      <path d="M23 21l.9 2.9L27 25l-3.1.9L23 29l-.9-3.1L19 25l3.1-1.1L23 21z" fill="#91B8A7"/>
    </svg>`;
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}`);
}

function createTray() {
  if (tray) return;
  tray = new Tray(createTrayIcon());
  tray.setToolTip("Smart Scribe");
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "显示 Smart Scribe", click: () => showMainWindow() },
    { type: "separator" },
    { label: "退出", click: () => { isQuiting = true; app.quit(); } },
  ]));
  tray.on("click", () => showMainWindow());
}

function showMainWindow() {
  if (!mainWindow) {
    createWindow();
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.loadURL(BACKEND_URL);
    }
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
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

// IPC: receive theme changes from renderer
ipcMain.on("set-theme", (_event, isDark) => {
  applyTitleBarTheme(isDark);
});

ipcMain.handle("get-startup-status", () => lastStartupStatus);

app.whenReady().then(async () => {
  const root = getProjectRoot();
  const splashStartedAt = Date.now();

  // Step 1: check if backend is already running
  const alreadyRunning = await checkHealth();
  console.log("[startup] backend already running:", alreadyRunning);

  createWindow();
  sendStartupStatus({
    mode: "launch",
    title: alreadyRunning ? "正在打开工作台" : "正在启动服务",
    detail: alreadyRunning ? "本地服务已在运行，正在进入应用" : "正在准备本地工作台，请稍等",
  });

  if (alreadyRunning) {
    // Backend is alive — go straight to the app
    await sleep(Math.max(0, MIN_SPLASH_MS - (Date.now() - splashStartedAt)));
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.loadURL(BACKEND_URL);
    }
  } else {
    // Need to start backend
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
    if (mainWindow && !mainWindow.isDestroyed()) {
      await sleep(Math.max(0, MIN_SPLASH_MS - (Date.now() - splashStartedAt)));
      mainWindow.loadURL(BACKEND_URL);
    }
  }

  app.on("activate", () => {
    showMainWindow();
  });
});

app.on("second-instance", () => {
  showMainWindow();
});

app.on("window-all-closed", () => {
  isQuiting = true;
  killBackend();
  app.quit();
});

app.on("before-quit", () => {
  isQuiting = true;
  killBackend();
});

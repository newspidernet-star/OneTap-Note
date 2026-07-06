# Smart Scribe 桌面 exe 化 PRD 与开发文档

> 目标：把现有 Windows 一键启动体验包装成更像正式桌面软件的 `Smart Scribe.exe`。  
> 当前阶段不追求完全免安装，不把 Python、Node、ffmpeg、OCR 依赖全部塞进 exe。  
> 第一版重点是：双击 exe 后自动复用现有安装/启动逻辑，并打开一个独立应用窗口。

---

## 1. 背景

Smart Scribe 现在已经有可用的 Web 工作台和 Windows 一键启动脚本：

- `start-windows.bat`
- `scripts/setup-windows.ps1`
- `scripts/start-windows.ps1`

现有脚本已经负责：

- 检查/安装 Python 3.11
- 检查/安装 Node.js
- 检查/安装 ffmpeg
- 检查/安装 cloudflared
- 创建后端虚拟环境
- 安装后端依赖
- 安装 Playwright Chromium
- 安装前端依赖并构建前端
- 生成基础 `.env`
- 启动 FastAPI 后端
- 打开 `http://localhost:8000`

所以桌面化的第一版不要重写这一套逻辑。  
正确方向是：**复用现有脚本，把用户入口从 bat/浏览器变成 exe/独立窗口。**

---

## 2. 产品目标

用户双击 `Smart Scribe.exe` 后，看到的是一个自己的桌面应用窗口，而不是普通浏览器标签页。

窗口需要具备：

- 最小化
- 最大化/还原
- 关闭
- 应用标题：`Smart Scribe`
- 后续可加应用图标

用户体验应接近：

```text
双击 Smart Scribe.exe
-> 如果首次运行，自动走现有安装流程
-> 如果已安装，直接启动后端
-> 打开 Smart Scribe 独立窗口
-> 用户在窗口里使用现有 Web 工作台
-> 关闭窗口时，后端服务也一起关闭
```

---

## 3. 非目标

第一版不做这些事情：

- 不做完全免安装版。
- 不把 Python 运行时打进 exe。
- 不把 `backend/.venv` 打进 exe。
- 不把 ffmpeg/cloudflared 内置进 exe。
- 不重写后端。
- 不重写前端。
- 不改现有 API。
- 不改变 Docker 路线。

这些可以作为后续阶段：

```text
第一阶段：桌面壳 + 复用现有脚本
第二阶段：打包安装器
第三阶段：内置运行环境，接近完全免安装
```

---

## 4. 推荐技术方案

推荐使用 Electron。

原因：

- 项目前端已经是 React/Vite，Electron 与 Web 前端天然匹配。
- Electron 可以创建真正的桌面窗口。
- Electron 可以控制窗口关闭、最大化、最小化。
- Electron 可以启动子进程，用来运行现有 PowerShell 脚本。
- 后续可以用 `electron-builder` 打包为 Windows exe。

第一版结构建议：

```text
smart-scribe/
  desktop/
    package.json
    main.cjs
    preload.cjs
  backend/
  frontend/
  scripts/
    setup-windows.ps1
    start-windows.ps1
  start-windows.bat
```

---

## 5. 核心实现思路

### 5.1 不直接调用 `start-windows.bat`

不建议 Electron 直接调用 `start-windows.bat`。

原因：

- bat 最后有 `pause`，不适合作为后台子进程。
- `scripts/start-windows.ps1` 目前会自己打开 Edge/Chrome 的 `--app` 窗口。Electron 版不应该再额外打开浏览器窗口。

所以第一版需要对启动脚本做一个很小的增强：

### 5.2 给 `scripts/start-windows.ps1` 增加无浏览器模式

新增环境变量：

```text
SMART_SCRIBE_NO_BROWSER=1
```

当该变量存在时：

- 只启动 FastAPI 后端。
- 不打开 Edge/Chrome。
- 不注册浏览器关闭事件。

现有 bat 入口仍保持原样：

- 普通用户双击 `start-windows.bat`：继续自动打开 Edge/Chrome app 窗口。
- Electron 启动：设置 `SMART_SCRIBE_NO_BROWSER=1`，只启动后端，由 Electron 自己打开窗口。

这是兼容性最好的做法。

### 5.3 Electron 负责三件事

Electron 主进程负责：

1. 检查是否需要首次安装。
2. 启动后端服务。
3. 创建窗口加载 `http://127.0.0.1:8000`。

伪流程：

```text
app ready
-> resolve project root
-> if backend/.venv/Scripts/python.exe 不存在，先运行 scripts/setup-windows.ps1
-> if frontend/dist/index.html 不存在，先运行 scripts/setup-windows.ps1
-> 启动 scripts/start-windows.ps1，设置 SMART_SCRIBE_NO_BROWSER=1
-> 轮询 http://127.0.0.1:8000/api/health
-> health 成功后 create BrowserWindow
-> loadURL("http://127.0.0.1:8000")
-> 用户关闭窗口时 kill 后端子进程
```

---

## 6. 具体开发任务

### 任务 1：新增桌面目录

新增：

```text
desktop/package.json
desktop/main.cjs
desktop/preload.cjs
```

`desktop/package.json` 建议：

```json
{
  "name": "smart-scribe-desktop",
  "version": "0.1.0",
  "private": true,
  "main": "main.cjs",
  "scripts": {
    "dev": "electron .",
    "pack": "electron-builder --dir",
    "dist": "electron-builder"
  },
  "devDependencies": {
    "electron": "^31.0.0",
    "electron-builder": "^24.13.3"
  },
  "build": {
    "appId": "com.smartscribe.app",
    "productName": "Smart Scribe",
    "directories": {
      "output": "dist"
    },
    "files": [
      "main.cjs",
      "preload.cjs"
    ],
    "extraResources": [
      {
        "from": "../",
        "to": "app",
        "filter": [
          "backend/**",
          "frontend/**",
          "scripts/**",
          "start-windows.bat",
          "README.md",
          "!backend/.venv/**",
          "!backend/storage/**",
          "!frontend/node_modules/**",
          "!frontend/dist/**",
          "!**/__pycache__/**",
          "!**/.pytest_cache/**"
        ]
      }
    ],
    "win": {
      "target": "nsis"
    }
  }
}
```

说明：

- 第一版可以先不打安装包，只跑 `npm run dev` 验证窗口。
- `extraResources` 是为后续安装包准备。
- 不要把 `backend/.venv`、`frontend/node_modules`、`backend/storage` 打进去。

### 任务 2：修改 `scripts/start-windows.ps1`

增加：

```powershell
$NoBrowser = $env:SMART_SCRIBE_NO_BROWSER -eq '1'
```

将“打开 Edge/Chrome app 窗口”的逻辑包起来：

```powershell
if (-not $NoBrowser) {
    # 原来的浏览器打开逻辑
}
```

退出时关闭浏览器的逻辑也要判断：

```powershell
if (-not $NoBrowser -and $procId -gt 0) {
    Stop-Process ...
}
```

最后 uvicorn 启动逻辑不变：

```powershell
& $pyExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

验收：

```powershell
$env:SMART_SCRIBE_NO_BROWSER='1'
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\start-windows.ps1
```

应该只启动后端，不打开浏览器。

### 任务 3：Electron 启动后端

`desktop/main.cjs` 需要实现：

- 找到项目根目录。
- 判断 dev 模式和打包模式。
- 使用 `child_process.spawn` 启动 PowerShell。
- 给子进程传入 `SMART_SCRIBE_NO_BROWSER=1`。
- 监听 stdout/stderr，把日志打印到 Electron 控制台。
- 轮询健康检查。
- 健康检查成功后打开窗口。

伪代码结构：

```js
const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");
const http = require("node:http");

let backendProcess = null;
let mainWindow = null;

function getProjectRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "app");
  }
  return path.resolve(__dirname, "..");
}

function runPowerShell(scriptPath, root) {
  return spawn("powershell.exe", [
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    scriptPath
  ], {
    cwd: root,
    env: {
      ...process.env,
      SMART_SCRIBE_NO_BROWSER: "1"
    },
    windowsHide: true
  });
}

function waitForHealth(timeoutMs = 120000) {
  // poll http://127.0.0.1:8000/api/health
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 980,
    minHeight: 640,
    title: "Smart Scribe",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadURL("http://127.0.0.1:8000");
  mainWindow.once("ready-to-show", () => mainWindow.show());
}
```

### 任务 4：首次安装流程

Electron 启动时判断：

```text
backend/.venv/Scripts/python.exe 是否存在
frontend/dist/index.html 是否存在
```

如果缺失，先运行：

```powershell
scripts/setup-windows.ps1
```

注意：

- setup 可能需要很久。
- 第一版可以先用系统弹窗提示：`首次启动需要安装依赖，请稍等。`
- 更好的版本再做漂亮的安装进度窗口。

实现建议：

```js
async function ensureInstalled(root) {
  const pyExe = path.join(root, "backend", ".venv", "Scripts", "python.exe");
  const distIndex = path.join(root, "frontend", "dist", "index.html");
  if (existsSync(pyExe) && existsSync(distIndex)) return;

  dialog.showMessageBoxSync({
    type: "info",
    title: "Smart Scribe",
    message: "首次启动需要安装依赖，可能需要几分钟。",
    detail: "如果网络较慢，请确保代理 7897 可用，或稍后重试。"
  });

  await runSetupScript(root);
}
```

### 任务 5：窗口关闭时清理后端

当用户关闭窗口：

- 杀掉 Electron 启动的后端子进程。
- 不要杀掉用户电脑上其他 Python 进程。

实现：

```js
app.on("before-quit", () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
});
```

注意：

- `scripts/start-windows.ps1` 当前会自动清理 8000 端口旧进程。
- Electron 关闭时只应清理自己启动的子进程。
- 不要额外写“杀所有 8000 端口”的逻辑，避免误伤。

---

## 7. 验收标准

### 基础验收

1. 双击或运行 Electron 后，出现 `Smart Scribe` 桌面窗口。
2. 窗口不是浏览器标签页。
3. 窗口有最小化、最大化、关闭按钮。
4. 页面能正常访问 `http://127.0.0.1:8000`。
5. 上传/链接/总结等现有功能不被破坏。
6. 关闭窗口后，Electron 启动的后端进程退出。

### 首次运行验收

在没有 `backend/.venv` 或没有 `frontend/dist` 的情况下：

1. Electron 提示首次安装。
2. 自动运行 `scripts/setup-windows.ps1`。
3. 安装完成后自动启动后端。
4. 打开 Smart Scribe 窗口。

### 已安装运行验收

在已有依赖的情况下：

1. Electron 不重复安装依赖。
2. 直接启动后端。
3. 打开窗口。
4. 启动时间明显短于首次运行。

### 回归验收

原有方式必须还能用：

```powershell
start-windows.bat
```

也就是说：

- bat 仍然自动打开 Edge/Chrome app 窗口。
- Electron 的修改不能破坏 bat。

---

## 8. 常见坑

### 坑 1：Electron 启动后又打开了 Edge/Chrome

原因：没有设置 `SMART_SCRIBE_NO_BROWSER=1`，或者 `start-windows.ps1` 没有正确判断该变量。

解决：确保 Electron 启动 PowerShell 时传入：

```js
env: {
  ...process.env,
  SMART_SCRIBE_NO_BROWSER: "1"
}
```

### 坑 2：关闭 Electron 后后端还在跑

原因：没有保存 `backendProcess` 引用，或者 PowerShell 子进程没有被杀掉。

解决：

- 保存 `spawn` 返回的进程。
- `before-quit` 里调用 `backendProcess.kill()`。

### 坑 3：第一次启动黑屏

原因：Electron 窗口加载页面时后端还没起来。

解决：

- 必须先轮询 `/api/health`。
- health 成功后再 `loadURL` 或显示窗口。

### 坑 4：打包后找不到项目文件

原因：dev 模式和 packaged 模式路径不同。

解决：

```js
if (app.isPackaged) {
  root = path.join(process.resourcesPath, "app");
} else {
  root = path.resolve(__dirname, "..");
}
```

### 坑 5：依赖安装失败

原因：

- 网络问题。
- 代理没开。
- winget 不可用。
- 用户权限不足。

解决：

- 第一版直接展示错误弹窗。
- 错误信息要告诉用户可尝试开启 `127.0.0.1:7897` 代理。
- 不要静默失败。

---

## 9. 建议提交顺序

不要一次性做完。建议分 4 个 commit：

### Commit 1

```text
feat(desktop): add electron shell skeleton
```

内容：

- 新增 `desktop/package.json`
- 新增 `desktop/main.cjs`
- 新增 `desktop/preload.cjs`
- Electron 能打开空窗口或加载现有 URL

### Commit 2

```text
feat(windows): allow backend start without browser
```

内容：

- 修改 `scripts/start-windows.ps1`
- 支持 `SMART_SCRIBE_NO_BROWSER=1`
- 确认 `start-windows.bat` 仍然可用

### Commit 3

```text
feat(desktop): launch backend from electron
```

内容：

- Electron 调用 PowerShell 启动后端
- 轮询 `/api/health`
- 后端就绪后打开窗口
- 关闭窗口清理子进程

### Commit 4

```text
docs(desktop): document exe workflow
```

内容：

- README 或 docs 增加桌面版启动说明
- 说明第一版不是完全免安装

---

## 10. 推荐给智能体的执行提示词

可以把下面这段直接发给后续智能体：

```text
请按照 docs/desktop-exe-prd.md 实现 Smart Scribe 第一版桌面 exe。

重要边界：
1. 不要重写后端。
2. 不要重写前端。
3. 不要追求完全免安装。
4. 必须复用 scripts/setup-windows.ps1 和 scripts/start-windows.ps1。
5. start-windows.bat 原有行为不能被破坏。
6. Electron 启动时要设置 SMART_SCRIBE_NO_BROWSER=1，避免额外打开 Edge/Chrome。
7. 必须等待 /api/health 成功后再显示主窗口。
8. 关闭 Electron 窗口时要清理它启动的后端子进程。
9. 每完成一个阶段都要 git commit。

请按文档里的 4 个 commit 顺序开发。
```

---

## 11. 最小可行版本定义

如果时间不够，最小可行版本只需要做到：

- `desktop/` Electron 项目存在。
- `npm install` 后能 `npm run dev`。
- Electron 能启动现有后端。
- Electron 能打开独立窗口。
- 关闭窗口后后端退出。
- 原来的 `start-windows.bat` 不受影响。

暂时可以不做：

- 安装包。
- 图标。
- 托盘。
- 自动更新。
- 漂亮安装进度页。
- 完全免安装。

---

## 12. 最终判断

这个任务可以做，而且适合当前项目。

但它不是“简单把 bat 转 exe”。  
更准确的第一版目标是：

```text
Electron 桌面壳
+ 复用现有 Windows 安装/启动脚本
+ 独立 Smart Scribe 窗口
+ 关闭时清理后端
```

这样既能获得“像软件一样”的体验，又不会把项目拖进复杂的完整安装包工程里。

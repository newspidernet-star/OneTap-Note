# Smart Scribe Setup.exe 设计与开发文档

## 1. 文档目的

将当前 `Smart-Scribe-Windows.zip` 便携版升级为符合普通 Windows 用户习惯的安装程序：

```text
Smart-Scribe-Setup-0.x.x.exe
```

用户体验目标：

1. 双击 Setup.exe。
2. 选择安装位置并完成安装。
3. 自动创建桌面快捷方式和开始菜单入口。
4. 安装完成后可直接启动 Smart Scribe。
5. 第一次启动继续使用现有安装动画，联网准备 Python、FFmpeg、cloudflared 和后端依赖。
6. 后续启动不重复安装依赖。
7. 可在 Windows“已安装的应用”中正常卸载。
8. 覆盖安装新版本时保留历史会话、API 设置和用户素材。

这不是完全离线安装器。第一版 Setup.exe 允许首次启动时联网下载缺失依赖，重点是提供正式 Windows 软件的安装、快捷方式、升级与卸载体验。

## 2. 当前项目状态

当前已有：

- Electron 桌面窗口；
- `Smart Scribe.exe` 便携程序；
- 首次启动加载/安装动画；
- `scripts/setup-windows.ps1` 依赖检查与安装脚本；
- `scripts/start-windows.ps1` 后端启动脚本；
- `electron-builder` 依赖；
- Windows Release ZIP 打包脚本；
- 托盘、单实例、退出后端等桌面能力。

当前 Electron 配置只生成目录版：

```json
"win": {
  "target": "dir"
}
```

Setup.exe 不能只把 `target` 改成 `nsis` 就结束。Smart Scribe 运行时还需要后端源码、前端构建产物、PowerShell 脚本和首次安装流程。

## 3. 第一版范围

### 必须完成

- NSIS 引导式安装器；
- 每用户安装，不强制管理员权限安装应用本体；
- 可选择安装目录；
- 桌面快捷方式可选；
- 开始菜单快捷方式；
- 安装完成后可勾选“运行 Smart Scribe”；
- Windows 应用列表中的卸载入口；
- 覆盖安装升级；
- 保留用户数据；
- GitHub Release 输出 Setup.exe；
- 干净 Windows 环境验收。

### 第一版不做

- 完全离线依赖包；
- 应用内自动更新；
- 增量更新；
- 微软商店；
- 强制代码签名；
- 自动删除用户笔记和 API 配置。

## 4. 推荐技术方案

使用项目已有的：

```text
Electron + electron-builder + NSIS
```

不引入 Inno Setup、WiX 或第二套打包工具。

安装模式：

```text
per-user assisted installer
```

建议默认安装目录：

```text
%LOCALAPPDATA%\Programs\Smart Scribe
```

选择每用户安装的原因：

- 通常不需要管理员权限安装应用本体；
- 当前首次启动会创建运行环境，需要目录可写；
- 避免安装到 `Program Files` 后创建 `.venv`、写配置时被权限拦截。

## 5. 目录设计

### 5.1 安装目录

安装目录只保存可替换的程序文件：

```text
%LOCALAPPDATA%\Programs\Smart Scribe\
├── Smart Scribe.exe
├── resources\
├── backend\
│   ├── app\
│   └── requirements-windows.txt
├── frontend\
│   └── dist\
├── scripts\
│   ├── setup-windows.ps1
│   └── start-windows.ps1
├── LICENSE
└── README.md
```

不要打包以下内容：

```text
.git
node_modules
frontend/src
backend/.venv
backend/storage
__pycache__
.pytest_cache
开发日志
本地 .env
数据库
用户上传素材
Smart Scribe.lnk
```

前端必须在发布前构建完成。用户电脑不再安装 Node.js，也不在首次启动时运行 `npm install` 或 `npm run build`。

### 5.2 用户数据目录

所有不可丢失的数据必须移出安装目录：

```text
%LOCALAPPDATA%\Smart Scribe\data\
├── smart_scribe.db
├── secret.key
├── storage\
└── .env
```

运行时缓存和 Python 环境：

```text
%LOCALAPPDATA%\Smart Scribe\runtime\
└── .venv\
```

日志：

```text
%LOCALAPPDATA%\Smart Scribe\logs\
├── backend.log
└── desktop.log
```

必须保证：

- 更新安装目录不会覆盖 `data`；
- 卸载默认保留 `data`；
- `.venv` 损坏后可以删除并自动重建；
- API Key 所在数据库和 `secret.key` 必须同时保留。

## 6. 后端数据目录改造

当前后端默认使用相对路径：

```text
storage/
storage/smart_scribe.db
storage/secret.key
```

Setup 版本启动后端时必须显式设置：

```powershell
$DataRoot = Join-Path $env:LOCALAPPDATA 'Smart Scribe\data'
$Storage = Join-Path $DataRoot 'storage'

$env:SMART_SCRIBE_STORAGE_DIR = $Storage
$env:SMART_SCRIBE_DB_URL = 'sqlite:///' + (($DataRoot + '\smart_scribe.db') -replace '\\','/')
$env:SMART_SCRIBE_SECRET_KEY_FILE = Join-Path $DataRoot 'secret.key'
$env:SMART_SCRIBE_FRONTEND_DIST_DIR = Join-Path $InstallRoot 'frontend\dist'
```

在启动前创建目录：

```powershell
New-Item -ItemType Directory -Path $DataRoot -Force | Out-Null
New-Item -ItemType Directory -Path $Storage -Force | Out-Null
```

不得把 API Key 明文写入安装器、仓库或 `.env`。

## 7. 首次依赖安装改造

### 7.1 保留的联网安装项

第一版继续安装或检查：

- Python 3.11；
- FFmpeg；
- cloudflared；
- Python requirements；
- Playwright Chromium（如果图片/图文链接处理仍需要）。

### 7.2 删除的用户端安装项

Setup 版用户不需要：

- Node.js；
- frontend `npm install`；
- frontend `npm run build`。

这些属于发布机器的构建工作，不应让普通用户承担。

### 7.3 虚拟环境位置

当前脚本将虚拟环境创建在：

```text
backend\.venv
```

Setup 版应改为：

```text
%LOCALAPPDATA%\Smart Scribe\runtime\.venv
```

Electron 中的 `isBackendInstalled()`、`setup-windows.ps1` 和 `start-windows.ps1` 必须使用同一个路径约定，禁止各自推导不同位置。

推荐由 Electron 向脚本传入环境变量：

```text
SMART_SCRIBE_INSTALL_ROOT
SMART_SCRIBE_RUNTIME_ROOT
SMART_SCRIBE_DATA_ROOT
```

### 7.4 安装失败体验

首次依赖安装失败时：

- 不关闭窗口后什么都不说；
- 显示失败阶段；
- 显示简短中文原因；
- 提供“重试”按钮；
- 提供“打开日志目录”按钮；
- 不向普通用户展示整段 Python 堆栈。

## 8. electron-builder 配置

修改 `desktop/package.json`。

示例结构：

```json
{
  "name": "smart-scribe-desktop",
  "version": "0.3.0",
  "main": "main.cjs",
  "scripts": {
    "dev": "electron .",
    "pack": "electron-builder --dir",
    "dist": "electron-builder --win nsis"
  },
  "build": {
    "appId": "com.smartscribe.app",
    "productName": "Smart Scribe",
    "artifactName": "Smart-Scribe-Setup-${version}.${ext}",
    "directories": {
      "output": "dist-installer"
    },
    "files": [
      "main.cjs",
      "preload.cjs",
      "loading.html",
      "assets/**"
    ],
    "extraFiles": [
      {
        "from": "../backend",
        "to": "backend",
        "filter": [
          "app/**",
          "requirements-windows.txt"
        ]
      },
      {
        "from": "../frontend/dist",
        "to": "frontend/dist"
      },
      {
        "from": "../scripts",
        "to": "scripts",
        "filter": [
          "setup-windows.ps1",
          "start-windows.ps1"
        ]
      },
      {
        "from": "../LICENSE",
        "to": "LICENSE"
      },
      {
        "from": "../README.md",
        "to": "README.md"
      }
    ],
    "win": {
      "target": ["nsis"],
      "icon": "assets/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "perMachine": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "shortcutName": "Smart Scribe",
      "runAfterFinish": true,
      "deleteAppDataOnUninstall": false,
      "installerLanguages": ["zh_CN"]
    }
  }
}
```

实施时必须按 electron-builder 当前版本校验字段，不要盲目复制示例后跳过构建验证。

## 9. 图标与安装器视觉

必须准备：

```text
desktop/assets/icon.ico
desktop/assets/icon.png
```

`icon.ico` 至少包含：

```text
16×16
24×24
32×32
48×48
64×64
128×128
256×256
```

要求：

- 安装器显示 Smart Scribe 图标；
- 桌面快捷方式显示相同图标；
- 开始菜单和任务栏图标一致；
- 系统托盘图标继续使用现有资源；
- 不重新生成品牌图，不替换用户已经确认的图标。

安装器文字使用简单中文：

```text
安装 Smart Scribe
选择安装位置
创建桌面快捷方式
正在安装
安装完成
运行 Smart Scribe
```

## 10. 安装、升级与卸载行为

### 首次安装

```text
运行 Setup.exe
→ 安装 Electron 与项目文件
→ 创建快捷方式和卸载入口
→ 启动 Smart Scribe
→ 首次启动动画检查并安装依赖
→ 打开工作台
```

### 覆盖升级

同一 `appId` 下运行新版本 Setup：

```text
关闭旧程序
→ 覆盖安装目录中的程序文件
→ 保留 %LOCALAPPDATA%\Smart Scribe\data
→ 必要时更新 Python requirements
→ 启动新版本
```

依赖是否需要更新，不能只判断 `.venv` 是否存在。建议发布时生成 requirements 指纹：

```text
runtime\requirements.sha256
```

启动时比较当前 `requirements-windows.txt` 哈希；不一致才重新执行 pip install。

### 卸载

默认删除：

- 安装目录；
- 桌面快捷方式；
- 开始菜单快捷方式；
- 注册的卸载信息。

默认保留：

- 数据库；
- API 设置；
- secret.key；
- 用户素材和导出记录。

第一版可保留 runtime 缓存。后续再增加“彻底删除所有数据”的卸载选项。不要默认清除用户知识库数据。

## 11. 构建脚本

新增：

```text
scripts/package-windows-setup.ps1
```

脚本职责：

1. 检查 Git 工作区状态并打印当前 commit；
2. 构建前端；
3. 检查 `frontend/dist/index.html`；
4. 检查后端必需文件；
5. 检查图标；
6. 安装 desktop npm 依赖；
7. 执行 `npm run dist`；
8. 检查 Setup.exe 是否生成；
9. 输出 SHA256；
10. 不自动上传 GitHub，不自动修改版本号。

伪代码：

```powershell
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent

Push-Location "$Root\frontend"
npm ci
npm run build
Pop-Location

Push-Location "$Root\desktop"
npm ci
npm run dist
Pop-Location

$Setup = Get-ChildItem "$Root\desktop\dist-installer\Smart-Scribe-Setup-*.exe"
Get-FileHash $Setup.FullName -Algorithm SHA256
```

保留现有 ZIP 打包脚本，两种发布形式并存：

```text
Smart-Scribe-Windows.zip
Smart-Scribe-Setup-0.x.x.exe
```

## 12. GitHub Release

每次正式发布建议上传：

```text
Smart-Scribe-Setup-0.x.x.exe
Smart-Scribe-Windows.zip
SHA256SUMS.txt
```

Release 描述说明：

- Setup.exe：推荐普通 Windows 用户；
- ZIP：适合便携使用和开发者排错；
- 首次启动需要联网准备运行环境；
- Windows 10/11 64 位；
- 未签名版本可能出现 SmartScreen 提示。

不要把 API Key、`.env`、数据库、测试视频或本机路径打进 Release。

## 13. 代码签名

第一版可以暂时不签名，但必须接受以下现实：

- Windows SmartScreen 可能显示“未知发布者”；
- 下载量较少时提示更明显；
- 用户需要点击“更多信息 → 仍要运行”。

后续正式分发时再购买 Windows 代码签名证书，并通过环境变量注入证书，不得提交到仓库。

## 14. 安全要求

构建完成后扫描安装器和解包内容，确认不存在：

- API Key；
- GitHub Token；
- Cookie；
- 用户名、绝对路径；
- `.env`；
- `smart_scribe.db`；
- `secret.key`；
- storage 中的用户媒体；
- 调试日志；
- `.git` 历史。

安装脚本执行 winget 和 pip 时必须：

- 使用 HTTPS 官方源；
- 记录失败阶段；
- 不执行远程下载后直接拼接命令；
- 不关闭系统安全软件；
- 不修改无关注册表项。

## 15. 验收标准

必须在没有项目源码的干净 Windows 10/11 虚拟机测试。

### 安装体验

- Setup.exe 能启动；
- 图标与名称正确；
- 可修改安装目录；
- 可选择桌面快捷方式；
- 安装后出现在“已安装的应用”；
- 安装完成可直接启动。

### 首次启动

- 显示现有安装进度页面；
- 缺少依赖时自动安装；
- 已存在依赖时跳过；
- 不要求用户打开终端；
- 安装失败有可理解提示和日志入口；
- 完成后进入工作台。

### 核心功能

- 上传本地视频；
- 粘贴抖音/B站链接；
- 语音转写；
- 生成知识笔记；
- 手动选帧；
- 复制笔记、原文和时间戳；
- 托盘隐藏与完全退出。

### 数据安全

1. 创建会话并配置 API Key。
2. 安装更高版本覆盖旧版本。
3. 确认会话和设置仍存在。
4. 卸载应用。
5. 确认用户 data 目录仍存在。
6. 重新安装后确认数据可继续读取。

### 边界情况

- 安装目录含空格；
- Windows 用户名含中文；
- 7897 代理开启和关闭；
- 端口 8000 被占用；
- 首次安装中途断网；
- Python 安装失败；
- 重复运行 Setup.exe；
- 应用运行时执行覆盖安装；
- 重启电脑后从快捷方式启动。

## 16. 推荐实施顺序

1. 将数据、runtime 和日志迁移到 `%LOCALAPPDATA%\Smart Scribe`。
2. 修改 Electron 与两个 PowerShell 脚本，共用统一路径变量。
3. 让 Setup 版跳过 Node 和前端现场构建。
4. 配置 electron-builder NSIS。
5. 增加 Setup 构建脚本。
6. 构建并检查安装器内容。
7. 在干净虚拟机完整安装测试。
8. 测试覆盖升级与卸载保留数据。
9. 更新 README 快速开始和 Release 说明。
10. Git 提交并打版本标签。

## 17. Git 要求

建议拆成独立提交：

```text
refactor: move desktop data to local app data
build: add NSIS Windows installer
docs: document Setup.exe installation flow
```

不要把所有修改塞进一个无法审查的大提交。

每一步完成后检查：

```text
git status
git diff --check
npm run build
node --check desktop/main.cjs
node --check desktop/preload.cjs
```

最终必须由实际生成的 Setup.exe 在干净 Windows 环境通过验收，不能只以 `electron-builder` 命令退出码为成功标准。

## 18. 完成定义

只有同时满足以下条件才算完成：

- GitHub Release 可下载 Setup.exe；
- 普通用户不需要解压 ZIP；
- 安装后有正式快捷方式和卸载入口；
- 首次依赖准备过程可见、可重试；
- 更新和卸载不会误删用户笔记；
- 干净 Windows 机器能够从安装到生成第一篇笔记完整跑通。

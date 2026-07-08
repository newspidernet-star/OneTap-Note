# Smart Scribe Setup.exe 交接执行文档

本文档用于继续完成 Windows 安装器版本发布。当前目标不是便携版 zip，而是生成类似正式 Windows 软件的安装包：

```text
Smart-Scribe-Setup-0.2.1.exe
```

安装器应提供：

- 双击安装；
- 可选择安装目录；
- 桌面快捷方式；
- 开始菜单入口；
- 安装完成后可直接运行 Smart Scribe；
- 首次启动时由应用自己的加载页检查并安装缺失依赖；
- 后续启动走桌面端窗口，不再像普通浏览器页面。

## 1. 当前主目录

请只操作主开发目录：

```text
D:\Edge Download\test\smart-scribe
```

不要操作旧测试副本或其他复制目录。这个目录才是主仓库。

## 2. 当前 Git 状态说明

在本文档创建时，已经为 Setup.exe 做了以下源码准备：

### 2.1 已修改文件

```text
.gitignore
desktop/main.cjs
desktop/package.json
desktop/package-lock.json
scripts/package-windows-setup.ps1
docs/Setup-EXE-交接执行文档.md
```

### 2.2 不要提交的本地文件

以下是本地构建产物或快捷方式，不要提交：

```text
.cache/
desktop/dist-installer/
Smart Scribe.lnk
```

`.gitignore` 已经补充：

```text
/.cache/
desktop/dist/
desktop/dist-installer/
```

`Smart Scribe.lnk` 是用户本机快捷方式，也不要提交。

## 3. 已完成的 Setup 配置

### 3.1 desktop/package.json

已把桌面端版本改为：

```json
"version": "0.2.1"
```

已把构建目标改为 NSIS 安装器：

```json
"dist": "electron-builder --win nsis"
```

已增加安装器输出命名：

```json
"artifactName": "Smart-Scribe-Setup-${version}.${ext}"
```

所以成功后应生成：

```text
desktop\dist-installer\Smart-Scribe-Setup-0.2.1.exe
```

已把这些运行所需资源打进安装器：

```text
backend/
frontend/
scripts/
docs/
README.md
PRODUCT.md
docker-compose.yml
start-windows.bat
start-desktop.bat
```

注意：安装器版本不是完全离线包。它会把项目文件安装进去，但首次启动时仍然会通过 `scripts\setup-windows.ps1` 检查并安装 Python、Node、ffmpeg、cloudflared、后端依赖等。

### 3.2 desktop/main.cjs

已修正安装版资源定位。

现在 `getProjectRoot()` 会优先判断：

```js
process.resourcesPath\scripts\setup-windows.ps1
```

这对 Setup.exe 很关键。因为 electron-builder 的 `extraResources` 会把项目文件放到 Electron 的 resources 目录，桌面端必须从那里找到 backend、frontend 和 scripts。

### 3.3 scripts/package-windows-setup.ps1

已新增专门的 Setup 构建脚本。

它负责：

1. 打印当前 commit；
2. 检查必要文件是否存在；
3. 构建前端；
4. 检查 `frontend\dist\index.html`；
5. 检查桌面端依赖；
6. 设置 electron-builder 缓存目录；
7. 设置 7897 代理；
8. 执行 `npm run dist`；
9. 找到 `Smart-Scribe-Setup-*.exe`；
10. 输出 SHA256。

以后构建安装器只需要在主目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package-windows-setup.ps1
```

## 4. 当前卡住的问题

Codex 当前环境中，构建已经走到 electron-builder 阶段，但失败在 `winCodeSign` 工具解压。

关键日志如下：

```text
downloaded url=https://github.com/electron-userland/electron-builder-binaries/releases/download/winCodeSign-2.6.0/winCodeSign-2.6.0.7z

ERROR: Cannot create symbolic link
D:\Edge Download\test\smart-scribe\.cache\electron-builder\winCodeSign\...\darwin\10.12\lib\libcrypto.dylib

ERROR: Cannot create symbolic link
D:\Edge Download\test\smart-scribe\.cache\electron-builder\winCodeSign\...\darwin\10.12\lib\libssl.dylib
```

这说明：

- 7897 代理已经生效；
- `winCodeSign-2.6.0.7z` 已经下载成功；
- 失败点不是网络；
- 失败点是当前执行环境没有创建符号链接的权限；
- 这是 Codex 沙箱 / 当前 Windows 权限问题，不是 Smart Scribe 业务代码问题。

## 5. 推荐继续方案

### 方案 A：在普通 Windows PowerShell 里构建

最推荐。

用用户自己的 Windows PowerShell，不要在受限 Codex 沙箱里跑。

步骤：

1. 关闭正在运行的 Smart Scribe。
2. 打开 PowerShell。
3. 进入项目目录：

```powershell
cd "D:\Edge Download\test\smart-scribe"
```

4. 设置代理：

```powershell
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
$env:HTTP_PROXY = "http://127.0.0.1:7897"
$env:NO_PROXY = "localhost,127.0.0.1,::1"
```

5. 运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package-windows-setup.ps1
```

### 方案 B：管理员 PowerShell

如果方案 A 仍然报：

```text
Cannot create symbolic link
```

就用“管理员身份运行 PowerShell”，再执行同样命令。

### 方案 C：开启 Windows 开发者模式

如果不想每次用管理员权限，可开启：

```text
Windows 设置 -> 系统 -> 开发者选项 -> 开发人员模式
```

开启后普通用户通常也能创建符号链接。

然后重新执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package-windows-setup.ps1
```

## 6. 成功标准

构建成功后，应出现：

```text
Setup.exe created:
  D:\Edge Download\test\smart-scribe\desktop\dist-installer\Smart-Scribe-Setup-0.2.1.exe
SHA256:
  xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

并且目录里有：

```text
desktop\dist-installer\Smart-Scribe-Setup-0.2.1.exe
desktop\dist-installer\win-unpacked\
```

真正发布 Release 时，只需要上传：

```text
desktop\dist-installer\Smart-Scribe-Setup-0.2.1.exe
```

`win-unpacked` 不需要上传。

## 7. 安装后验收

请实际双击 `Smart-Scribe-Setup-0.2.1.exe` 测试。

至少检查以下内容：

1. 安装器能打开；
2. 可以选择安装目录；
3. 能创建桌面快捷方式；
4. 安装完成能启动 Smart Scribe；
5. 首次启动显示加载 / 安装流程，而不是白屏；
6. 如果依赖没装，会触发 `scripts\setup-windows.ps1`；
7. 启动后能打开工作台；
8. 右上角最小化、最大化、关闭按钮正常；
9. 关闭时“不再提醒 / 默认使用本次选择”仍然有效；
10. 从托盘重新打开正常；
11. 上传一个小视频或音频，能进入处理流程。

## 8. Release 发布建议

如果这是第四个小版本，建议版本号使用：

```text
v0.2.1
```

Release 标题：

```text
Smart Scribe v0.2.1 - Windows Setup Installer
```

Release 说明可以写：

```markdown
## 这是什么

这是 Smart Scribe 的第 4 个小版本，首次提供 Windows Setup.exe 安装器。

## 新增

- 新增 Windows 安装器：`Smart-Scribe-Setup-0.2.1.exe`
- 支持安装目录选择、桌面快捷方式、开始菜单入口
- 安装版启动时会自动寻找内置项目资源
- 保留原来的便携 zip / BAT 启动方式

## 注意

- 这不是完全离线安装器。
- 首次启动仍可能联网安装 Python、Node、ffmpeg、cloudflared 和后端依赖。
- 如果下载慢，请在系统代理或应用设置中使用 `127.0.0.1:7897`。
```

## 9. GitHub CLI 发布命令

如果本地已经登录 GitHub CLI：

```powershell
gh auth status
```

创建 Release：

```powershell
gh release create v0.2.1 `
  "desktop\dist-installer\Smart-Scribe-Setup-0.2.1.exe" `
  --title "Smart Scribe v0.2.1 - Windows Setup Installer" `
  --notes-file "docs\release-v0.2.1.md"
```

如果不想单独建 `docs\release-v0.2.1.md`，也可以直接在 GitHub 网页 Release 页面粘贴说明。

## 10. 提交建议

安装器配置通过后，建议提交：

```text
build: add Windows Setup installer packaging
```

提交内容应包含：

```text
.gitignore
desktop/main.cjs
desktop/package.json
desktop/package-lock.json
scripts/package-windows-setup.ps1
docs/Setup-EXE-交接执行文档.md
```

不要提交：

```text
.cache/
desktop/dist-installer/
Smart Scribe.lnk
```

如果生成了 Release notes 文档，例如：

```text
docs/release-v0.2.1.md
```

也可以一起提交。

## 11. 如果仍然失败

按失败信息判断：

### 11.1 网络失败

如果看到：

```text
connectex
timeout
ECONNRESET
```

优先确认代理：

```powershell
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
$env:HTTP_PROXY = "http://127.0.0.1:7897"
```

然后重跑。

### 11.2 符号链接失败

如果看到：

```text
Cannot create symbolic link
```

优先使用管理员 PowerShell，或开启 Windows 开发者模式。

### 11.3 找不到 frontend/dist

说明前端没构建成功。

单独运行：

```powershell
cd frontend
npm run build
```

修复 TypeScript / Vite 错误后再回根目录跑 Setup 脚本。

### 11.4 安装后白屏

重点检查：

```text
desktop/main.cjs -> getProjectRoot()
process.resourcesPath\scripts\setup-windows.ps1 是否存在
```

安装版的项目资源应该在：

```text
安装目录\resources\
```

里面应该能看到：

```text
backend\
frontend\
scripts\
docs\
README.md
```

如果没有，说明 `desktop/package.json` 的 `extraResources` 没打进去。

## 12. 重要提醒

Setup.exe 是“正式 Windows 软件体验”的一步，但它现在还不是最终形态。

当前版本重点是：

- 用户看到的是安装器；
- 安装后像普通应用；
- 代码和资源能被正确打包；
- 首次启动可以继续复用现有依赖安装流程。

以后可以再做更完整的离线安装器，把 Python、ffmpeg、cloudflared、后端依赖都预打包进去。那会让安装包更大，但体验更接近真正商业软件。

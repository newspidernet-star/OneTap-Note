# Replit 前端集成报告

## 概述
把 Replit 设计的 Smart Scribe 前端（`artifacts/smart-scribe`）移植到 `frontend/`，去除 Replit 专属依赖，对接 FastAPI 后端（`/api`），并实施 4 项改造需求。

## 改动文件清单（frontend/）
- **新建/重写**
  - `src/App.tsx` — 移除 wouter 路由与 Replit dark-only 硬编码；改用 `next-themes` ThemeProvider + `@tanstack/react-query` Provider + sonner Toaster 直接渲染 `<Workstation/>`
  - `src/main.tsx` — StrictMode + index.css 引入
  - `src/index.css` — shadcn dual-theme token 系统全量搬入并改主题色（见改造 1）
  - `src/pages/Workstation.tsx` — 完全重写：三栏布局对接后端、上传/处理流程、加载动画、主题切换、设置弹窗
  - `src/api/client.ts` — 原生 fetch 封装（替换 `@workspace/api-client-react`）
  - `src/api/hooks.ts` — react-query hooks：sessions(localStorage 兜底)、materials、upload、process、evidence、summary(generate/result/verify/match)、transcribe、settings(list/save/test)
  - `src/components/ui/*` — 55 个标准 shadcn 组件全量从 Replit 搬过来
  - `src/lib/utils.ts`、`src/hooks/use-toast.ts`、`src/hooks/use-mobile.tsx`、`components.json`
  - `public/favicon.svg`
  - `vite.config.ts` — 去掉 Replit cartographer/dev-banner/runtime-error-modal 插件；保留 `@vitejs/vite-plugin-react`、`@tailwindcss/vite`；加 `@` 路径别名；加 `/api`→`localhost:8000` 与 `/ws` 代理；固定 5173
  - `vitest.config.ts` — 重写为 vitest config（移除 react 插件以消除 vite 版本类型冲突）
  - `index.html`、`tsconfig.app.json`、`tsconfig.node.json`、`package.json`
  - `src/test/setup.ts` — 补 `window.matchMedia` mock（next-themes 依赖）
- **删除**
  - 旧自定义组件：`Sidebar/StatusBar/UploadZone/TopBar/Timeline/SummaryPanel/CitationTag/Workspace/MediaPreview/SettingsModal.tsx`
  - 旧 `api/client.ts`、`context/SessionContext.tsx`、`types/index.ts`、`hooks/useWebSocket.ts`、`tailwind.config.ts`
  - 过时测试：`test/Sidebar.test.tsx`、`test/client.test.tsx`
  - `node_modules`、`package-lock.json`（重新安装）
- **保留**
  - `src/test/App.test.tsx`（renders Smart Scribe 标题，通过）

## 去掉的 Replit 依赖 / 替换方案
| Replit 依赖 | 处理 |
|---|---|
| `@workspace/api-client-react` | 用原生 fetch 封装 `src/api/client.ts` + react-query hooks `src/api/hooks.ts` |
| `@replit/vite-plugin-cartographer` | 删除 |
| `@replit/vite-plugin-dev-banner` | 删除 |
| `@replit/vite-plugin-runtime-error-modal` | 删除 |
| `wouter`（路由） | 删除；直接渲染 Workstation（单页） |
| `next-themes` | 保留，用于明暗切换 |
| `@tanstack/react-query` | 保留 |
| `catalog:` 版本标记 | 全部替换为具体版本号（见 package.json） |
| `@tailwindcss/vite`、`tailwindcss`、`tw-animate-css`、`framer-motion`、`lucide-react` | 保留（去掉 Replit 专属后为标准 npm 包） |
| 强制 `document.classList.add('dark')` | 改为 `ThemeProvider attribute="class" defaultTheme="dark" enableSystem` |

> sessions 列表：后端无 `GET /api/sessions` 列表端点，于是用 localStorage 持久化前端创建过的会话（`smart-scribe.sessions`），创建时调 `POST /api/sessions` 并写回本地缓存。

## 4 项改造需求实现说明

### 改造 1：黑白主题 + 明暗切换
- `index.css` 中 `--primary` token 改为：
  - light：`0 0% 9%`（黑）+ `--primary-foreground: 0 0% 100%`（白）
  - dark：`0 0% 98%`（白）+ `--primary-foreground: 0 0% 9%`（黑）
  - 同时改 `--ring`/`--accent`/`--sidebar-*`/`--chart-1` 一致使用黑白
- 语义色保留：`--destructive` 保留红（light `0 84% 60%` / dark `0 72% 56%`），绿色/蓝色/橙色继续在 Workstation 内联类里使用（`bg-green-500`、`bg-blue-500`、`bg-orange-500`、`border-l-blue-500`、`border-l-orange-500`）
- 去除了原 Replit 珊瑚红 `350 79% 59%` 全部引用
- 顶栏新增主题切换按钮（`Sun`/`Moon` lucide 图标），`onClick={() => setTheme(theme === "dark" ? "light" : "dark")}`

### 改造 2：媒体预览加载动画
- `isBusy` 聚合 `uploadMaterial.isPending || processSession.isPending || generateSummary.isPending || session.status==="processing"`
- `PreviewLoading` 组件：framer-motion 旋转环 + 渐隐文字「正在上传 / 正在处理」+ 动态省略号 `<AnimatedDots/>`（`opacity:[0.2,1,0.2]` 无限循环）+ 三个跳动小圆点
- `PreviewSkeleton` 组件：分行骨架块 + 底部进度条（`width: ["0%","85%","100%"]` 循环）
- 4:3 预览区在 busy 时叠加 skeleton；上传中显示「正在上传」，处理中显示「正在处理」；右上角有「分析中」徽章
- AI 总结生成中右侧也显示 skeleton，按钮显示「生成中...」

### 改造 3：API 设置项扩展
- `SettingsModal` 从 `GET /api/settings` 动态读取配置项列表（后端实际返回 5 项：`volcano_app_id`、`volcano_access_token`、`deepseek_api_key`、`paddleocr_cloud_key`、`ytdlp_cookie_path`）
- 每项渲染：中文 label（`fieldMeta` 映射）、必填/可选徽章、「已配置」状态徽章、密码输入框、单独「测试」按钮
- 保存：`POST /api/settings`（只提交已修改字段）
- 测试：若该字段有改动先 `saveSettings` 再 `POST /api/settings/{key}/test`，结果带 ✓/✗ 显示并 toast
- 前端 `fieldMeta` 同时给齐用户要求的 4 项（3 必填 + 1 可选 paddleocr）与后端额外项 `ytdlp_cookie_path`

### 改造 4：布局以 Replit 版为准
- 右栏：`w-[520px] shrink-0`（固定像素，非百分比）
- 中栏媒体预览：`aspectRatio: "4/3"` + `maxHeight: "55vh"`，`bg-black`
- 左栏：`w-[220px] shrink-0`
- 未使用旧版 55%/30% 百分比

## 运行验证
- `npm install`：✅ 334 packages
- `tsc -b`（typecheck）：✅ exit 0
- `vite build`：✅ 2153 模块，dist ~496KB JS / 104KB CSS
- `vite --host 0.0.0.0`：✅ 在 0.0.0.0:5173 启动（ready in 320ms）
- `vitest run`：✅ `src/test/App.test.tsx` 1 passed（App renders Smart Scribe 标题）
- `.gitignore` 已含 `node_modules` 与 `dist`

## 遗留问题 / 备注
1. **sessions 列表端点缺失**：后端无 `GET /api/sessions`，前端用 localStorage 维护历史会话列表；换浏览器或清缓存会丢失历史（但数据库里的 session 仍在，只是 UI 列表不显示）。建议后端后续补 list 端点。
2. **URL 上传未接入**：后端只有 `POST /api/media/upload`（文件）无 URL 上传端点；「粘贴链接」目前仅创建一个以 URL 为标题的会话，并 toast 提示需用文件上传。
3. **主题初始值**：`defaultTheme="dark"`，首次加载即夜间；用户可手动切到 light；`enableSystem` 已开但默认优先 dark。
4. **媒体真正画面预览**：4:3 区当前显示证据块计数占位，未拉取具体帧/图片（后端 `/media/evidence` 只返回文本型证据块，无图片 URL）；点击证据块会滚动时间线高亮，但不会在预览区显示画面——这是数据接口限制。
5. **vitest 与 vite 版本**：vitest 2.x 内部绑定 vite 5，根 vite 7，导致 `vitest.config.ts` 若引入 `@vitejs/plugin-react` 会产生类型冲突；已在 vitest config 中移除 react 插件（JSX 由 vitest 默认 esbuild automatic runtime 处理，测试正常）。
6. **产生 dist 目录**：build 生成了 `frontend/dist/`，已在 .gitignore 中过滤。
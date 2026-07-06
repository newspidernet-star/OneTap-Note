import React, { useState, useEffect, useRef, useMemo } from "react";
import { Sparkles, Mic2, ImageIcon, ListChecks, TriangleAlert, Film, ScanLine, Link2, Settings, CheckCircle2, Loader2, XCircle, KeyRound, CheckCircle, Sun, Moon, CloudUpload, LinkIcon, ChevronDown, Play, Pause, SkipBack, SkipForward, ChevronLeft, ChevronRight, AlertCircle, Trash2, PanelRightClose, PanelRightOpen, Menu, X, Pencil, Plus, Copy, ArrowUp } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import {
  useListSessions,
  useGetEvidenceBlocks,
  useGetSummaryResult,
  useGenerateSummary,
  useGetMaterials,
  useCreateSession,
  useHeartbeat,
  useUploadFile,
  useDownloadLink,
  useProcessSession,
  useTranscribe,
  useMatchEvidence,
  useDeleteSession,
  useRenameSession,
  useGetSettings,
  useGetEphemeral,
  useExportObsidianMd,
  useUpdateSettings,
  getGetEvidenceBlocksQueryKey,
  getGetSummaryResultQueryKey,
  getGetMaterialsQueryKey,
  getListSessionsQueryKey,
  getGetSettingsQueryKey,
} from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import IslandButton, { ButtonStatus } from "@/components/IslandButton";
import UploadProgress, { UploadStatus } from "@/components/UploadProgress";
import TimelinePanel from "@/components/TimelinePanel";
import { useToast } from "@/hooks/use-toast";
import { useIsMobile } from "@/hooks/use-mobile";
import { toast as sonnerToast } from "sonner";

const MOCK_EVIDENCE = [
  { id: "S001", type: "speech", timestamp: "00:12", speaker: "张老师", text: "电磁感应定律是描述磁通量变化产生感应电动势的基本规律。" },
  { id: "P001", type: "screen", timestamp: "00:14", text: "法拉第电磁感应定律 · 磁通量变化率" },
  { id: "S002", type: "speech", timestamp: "01:05", speaker: "张老师", text: "我们来看楞次定律——感应电流的方向总是阻碍磁通量的变化。" },
];

const MOCK_SUMMARY = {
  corrected_text: "电磁感应定律是描述磁通量变化产生感应电动势的基本规律。法拉第电磁感应定律·磁通量变化率。我们来看楞次定律——感应电流的方向总是阻碍磁通量的变化。",
  summary: "本节课围绕电磁感应的核心理论展开，详细讲解了法拉第电磁感应定律和楞次定律两大基本规律。法拉第电磁感应定律指出，闭合回路中感应电动势的大小等于穿过该回路的磁通量变化率的负值，这是发电机和变压器等设备工作的基本原理。楞次定律进一步确定了感应电流的方向——感应电流所产生的磁通量总是试图阻碍引起感应的原磁通量的变化，这体现了能量守恒定律在电磁现象中的具体表现。理解这两条定律的物理意义和数学表达是掌握电磁感应章节的关键。",
  key_points: [
    { point: "法拉第电磁感应定律：磁通量变化产生感应电动势，大小等于磁通量变化率的负值", citations: ["S001", "P001"] },
    { point: "楞次定律：感应电流方向总是阻碍磁通量变化，体现能量守恒", citations: ["S002"] },
    { point: "电磁感应是发电机和变压器工作的基本原理", citations: ["P001"] },
  ],
  unused_block_ids: [] as string[],
  citation_valid: true,
  invalid_citations: [] as string[],
  corrections: [] as any[],
};

const CitationTag = ({ id, type, onClick }: { id: string; type: string; onClick: (e: React.MouseEvent) => void }) => {
  const isSpeech = type === 'speech';
  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={(e) => { e.stopPropagation(); onClick(e); }}
      className={`rounded-full border px-2 py-0.5 text-xs font-mono cursor-pointer transition-colors ${isSpeech ? 'border-primary/20 bg-primary/10 text-primary hover:bg-primary/15' : 'border-slate-500/25 bg-slate-500/10 text-slate-600 hover:bg-slate-500/15 dark:text-slate-300'}`}
    >
      {id}
    </motion.button>
  );
};

const CollapsibleCard = ({ icon: Icon, title, defaultOpen, children }: { icon: any; title: string; defaultOpen: boolean; children: React.ReactNode }) => {
  const [open, setOpen] = useState(defaultOpen);
  useEffect(() => { setOpen(defaultOpen); }, [defaultOpen]);

  return (
    <div className="rounded-xl border border-border/70 bg-card/95 shadow-sm overflow-hidden transition-shadow hover:shadow-md">
      <button
        onClick={() => setOpen(!open)}
        className={`w-full flex items-center justify-between px-4 py-3.5 transition-colors hover:bg-muted/60 ${open ? "border-b border-border/60 bg-muted/35" : "bg-card"}`}
      >
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground/85">
          <Icon className="w-4 h-4 text-primary" /> {title}
        </div>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }} className="text-muted-foreground">
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="p-4">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const MOCK_SESSION_ID = "mock_demo";

const SETTINGS_FIELDS = [
  { key: "dashscope_api_key", label: "DashScope API Key", required: true, placeholder: "sk-...（阿里云百炼控制台 → API-KEY 管理）" },
  { key: "dashscope_workspace_id", label: "DashScope Workspace ID", required: false, placeholder: "如 ws-mw8ay5bl73cfmmue（只填 ID 段，不要整个域名；空着走默认）" },
  { key: "deepseek_api_key", label: "DeepSeek API Key", required: true, placeholder: "sk-...（DeepSeek 开放平台 → API Keys）" },
  { key: "paddleocr_cloud_key", label: "PaddleOCR Cloud Key", required: false, placeholder: "如 a30cf4ca...（百度 AI Studio → 访问令牌；云端 OCR 必填）" },
  { key: "ytdlp_cookie_path", label: "yt-dlp Cookie 路径", required: false, placeholder: "本机 cookies.txt 绝对路径（抓需登录视频时用，一般不用）" },
];

function isAudioVideoName(name: string): boolean {
  return /\.(mp4|mkv|webm|mov|avi|mp3|wav|m4a|aac|flac)$/i.test(name);
}

function fmtTimestamp(t: any): string {
  if (t == null || t === "") return "00:00";
  const n = typeof t === "number" ? t : parseFloat(t);
  if (Number.isNaN(n)) return String(t);
  const m = Math.floor(n / 60);
  const s = Math.floor(n % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function Workstation() {
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [highlightedBlock, setHighlightedBlock] = useState<string | null>(null);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadErrorSessionId, setUploadErrorSessionId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [isDark, setIsDark] = useState(true);
  const [showKeyPoints, setShowKeyPoints] = useState(true);
  const [justGenerated, setJustGenerated] = useState(false);
  const [mediaIndex, setMediaIndex] = useState(0);
  const [linkInput, setLinkInput] = useState("");
  const [uploadRunning, setUploadRunning] = useState(false);
  const [processingSessionId, setProcessingSessionId] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const isMobile = useIsMobile();
  const timelineRef = useRef<HTMLDivElement>(null);
  const mainScrollRef = useRef<HTMLDivElement>(null);
  const [timelineVisible, setTimelineVisible] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const appendFileInputRef = useRef<HTMLInputElement>(null);
  const transcribeTriggered = useRef<string>("");
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const renameInputRef = useRef<HTMLInputElement>(null);
  const [settingsDraft, setSettingsDraft] = useState<Record<string, string>>({});
  const [creatingSession, setCreatingSession] = useState(false);
  const [appendPanelOpen, setAppendPanelOpen] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) root.classList.add('dark');
    else root.classList.remove('dark');
  }, [isDark]);

  const hasSession = !!activeSessionId;
  const isMock = false;

  const queryClient2 = queryClient;
  const clientId = useMemo(() => {
    try {
      let id = sessionStorage.getItem("smart_scribe_client_id");
      if (!id) {
        id = (crypto as any).randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        sessionStorage.setItem("smart_scribe_client_id", id);
      }
      return id;
    } catch { return "anonymous"; }
  }, []);
  const { data: sessions = [], isFetching: sessionsFetching } = useListSessions(clientId);
  const heartbeatMut = useHeartbeat();
  const { data: ephemeralInfo } = useGetEphemeral();

  // 心跳：仅 ephemeral 模式下每 15s 续命当前会话；标签关闭时发 DELETE（beforeunload 尽力而为）
  // 本地默认 ephemeral=false，不发心跳、不隔离，自己用看到全部会话
  useEffect(() => {
    if (!activeSessionId) return;
    if (!ephemeralInfo?.enabled) return;
    heartbeatMut.mutate({ sessionId: activeSessionId, clientId });
    const interval = setInterval(() => {
      heartbeatMut.mutate({ sessionId: activeSessionId, clientId });
    }, 15000);
    const onUnload = () => {
      if (!activeSessionId) return;
      // 优先 fetch keepalive DELETE（现代浏览器）；fallback sendBeacon POST /purge（sendBeacon 只能 POST）
      try {
        fetch(`/api/sessions/${activeSessionId}`, {
          method: "DELETE",
          keepalive: true,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ client_id: clientId }),
        }).catch(() => {
          navigator.sendBeacon(
            `/api/sessions/${activeSessionId}/purge`,
            new Blob([JSON.stringify({ client_id: clientId })], { type: "application/json" })
          );
        });
      } catch {
        try {
          navigator.sendBeacon(
            `/api/sessions/${activeSessionId}/purge`,
            new Blob([JSON.stringify({ client_id: clientId })], { type: "application/json" })
          );
        } catch {}
      }
    };
    window.addEventListener("beforeunload", onUnload);
    return () => {
      clearInterval(interval);
      window.removeEventListener("beforeunload", onUnload);
    };
  }, [activeSessionId, clientId, ephemeralInfo?.enabled]);

  const realSessions = useMemo(
    () => (sessions as any[]).map(s => ({ ...s, id: String(s.id) })),
    [sessions]
  );

  useEffect(() => {
    if (realSessions.length > 0 && (isMock || !realSessions.some(s => s.id === activeSessionId))) {
      setActiveSessionId(realSessions[0].id);
    }
  }, [realSessions]);

  useEffect(() => {
    if (renamingId && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [renamingId]);

  // 切换/删除会话后，清理属于旧会话的上传错误和处理状态
  useEffect(() => {
    if (uploadErrorSessionId) {
      const errorSessionStillExists = realSessions.some(s => s.id === uploadErrorSessionId);
      if (!errorSessionStillExists || activeSessionId !== uploadErrorSessionId) {
        setUploadError(null);
        setUploadErrorSessionId(null);
      }
    }
    if (processingSessionId && activeSessionId !== processingSessionId) {
      setProcessingSessionId(null);
    }
    if (uploadRunning) {
      setUploadRunning(false);
    }
    setAppendPanelOpen(false);
  }, [activeSessionId, uploadErrorSessionId, processingSessionId, realSessions]);

  // 切换会话后清空链接输入框和生成错误，避免旧状态串到新会话
  const prevActiveSessionRef = useRef(activeSessionId);
  useEffect(() => {
    if (activeSessionId !== prevActiveSessionRef.current) {
      setLinkInput("");
      setGenerateError(null);
      prevActiveSessionRef.current = activeSessionId;
    }
  }, [activeSessionId]);

  const { data: evidence = [], refetch: refetchEvidence } = useGetEvidenceBlocks(activeSessionId, {
    query: { enabled: hasSession, queryKey: getGetEvidenceBlocksQueryKey(activeSessionId) },
  });
  const { data: materials = [], refetch: refetchMaterials } = useGetMaterials(activeSessionId, {
    query: { enabled: hasSession, queryKey: getGetMaterialsQueryKey(activeSessionId) },
  });
  const { data: summary } = useGetSummaryResult(activeSessionId, {
    query: { enabled: hasSession, queryKey: getGetSummaryResultQueryKey(activeSessionId), retry: false },
  });

  const createSessionMut = useCreateSession();
  const uploadMut = useUploadFile({
    mutation: {
      onError: (error: any) => setUploadError(error?.message || "上传失败"),
    },
  });
  const downloadLinkMut = useDownloadLink({
    mutation: {
      onError: (error: any) => setUploadError(error?.message || "链接下载失败"),
    },
  });
  const processMut = useProcessSession({
    mutation: {
      onError: (error: any) => {
        setUploadError(error?.message || "处理失败");
        queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
      },
    },
  });
  const transcribeMut = useTranscribe({
    mutation: {
      onError: (error: any) => {
        setUploadError(error?.message || "转写失败");
        queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
      },
    },
  });
  const matchMut = useMatchEvidence({
    mutation: {
      onError: () => {
        queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
      },
    },
  });
  const deleteMut = useDeleteSession({
    mutation: {
      onSuccess: () => {
        // 清理被删会话残留的处理状态，避免切到别的会话时还显示"处理中"
        setProcessingSessionId(null);
        setUploadRunning(false);
        setUploadError(null);
        setUploadErrorSessionId(null);
        setGenerateError(null);
        // reset 正在飞的 mutation，让 isPending 归 false
        uploadMut.reset();
        downloadLinkMut.reset();
        processMut.reset();
        transcribeMut.reset();
        // 取消属于被删会话的查询
        queryClient.cancelQueries({ queryKey: getGetMaterialsQueryKey(deleteTarget?.id || "") });
        queryClient.cancelQueries({ queryKey: getGetEvidenceBlocksQueryKey(deleteTarget?.id || "") });
        queryClient.cancelQueries({ queryKey: getGetSummaryResultQueryKey(deleteTarget?.id || "") });
        queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
        setDeleteTarget(null);
      },
      onError: (err: any) => {
        alert(`删除失败：${err?.message || '未知错误'}\n\n如果是文件被占用，等几秒后重试。`);
      },
    },
  });
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null);
  const renameMut = useRenameSession();
  const { data: settingsStatus = [] } = useGetSettings({
    query: { enabled: showSettings, queryKey: getGetSettingsQueryKey() },
  });
  const updateSettingsMut = useUpdateSettings({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetSettingsQueryKey() });
        setSettingsDraft({});
        setShowSettings(false);
      },
    },
  });
  const generateMutation = useGenerateSummary({
    mutation: {
      onSuccess: () => {
        queryClient2.invalidateQueries({ queryKey: getGetSummaryResultQueryKey(activeSessionId) });
        setGenerateError(null);
        setShowKeyPoints(true);
        setJustGenerated(true);
        setTimeout(() => setJustGenerated(false), 600);
      },
      onError: () => setGenerateError("生成失败，请检查 API 设置"),
    },
  });
  const exportMdMut = useExportObsidianMd();

  const activeSession = realSessions.find(s => s.id === activeSessionId);
  const displaySummary = summary ?? (isMock ? MOCK_SUMMARY : null);
  const displayEvidence = isMock ? MOCK_EVIDENCE : (evidence as any[]);

  const previewMaterials = useMemo(() => {
    if (isMock) return [];
    return (materials as any[]).filter(m => m.url && m.type !== "unknown");
  }, [materials, isMock]);
  const currentPreview = previewMaterials[mediaIndex] || previewMaterials[0];
  useEffect(() => {
    setMediaIndex(0);
  }, [activeSessionId]);
  useEffect(() => {
    if (mediaIndex >= previewMaterials.length) setMediaIndex(0);
  }, [previewMaterials.length, mediaIndex]);
  const previewVideo = useMemo(() => previewMaterials.find(m => m.type === "video"), [previewMaterials]);
  const previewAudio = useMemo(() => previewMaterials.find(m => m.type === "audio"), [previewMaterials]);
  const previewImages = useMemo(() => previewMaterials.filter(m => m.type === "image"), [previewMaterials]);

  const hasPrevMaterial = mediaIndex > 0;
  const hasNextMaterial = mediaIndex < previewMaterials.length - 1;
  const goToPrevMaterial = () => setMediaIndex(i => Math.max(0, i - 1));
  const goToNextMaterial = () => setMediaIndex(i => Math.min(previewMaterials.length - 1, i + 1));

  const invalidateAll = (sessionId = activeSessionId) => {
    queryClient2.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
    if (!sessionId) return;
    queryClient2.invalidateQueries({ queryKey: getGetEvidenceBlocksQueryKey(sessionId) });
    queryClient2.invalidateQueries({ queryKey: getGetMaterialsQueryKey(sessionId) });
    queryClient2.invalidateQueries({ queryKey: getGetSummaryResultQueryKey(sessionId) });
  };

  const runTranscribe = (sessionId: string) => {
    transcribeTriggered.current = sessionId;
    transcribeMut.mutate(
      { sessionId },
      {
        onSuccess: () => {
          setUploadError(null);
          setUploadErrorSessionId(null);
          invalidateAll(sessionId);
        },
        onError: () => invalidateAll(sessionId),
      }
    );
  };

  const handleFiles = async (files: FileList | null, appendToCurrent = false) => {
    if (!files || files.length === 0) return;
    const arr = Array.from(files);
    const baseName = arr[0]?.name.replace(/\.[^.]+$/, "") || "Untitled";
    const uploadedHasAudioVideo = arr.some(f => isAudioVideoName(f.name));
    let sessionId = activeSessionId;
    const wasAppending = appendToCurrent && activeSession?.status === "done";
    setUploadRunning(true);
    setUploadError(null);
    setUploadErrorSessionId(sessionId);
    setProcessingSessionId(sessionId);
    try {
      const needCreate = !realSessions.some(s => s.id === activeSessionId);
      if (needCreate) {
        const created = await createSessionMut.mutateAsync({ clientId, title: baseName.slice(0, 80) });
        sessionId = String(created.id);
        await queryClient2.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
        setActiveSessionId(sessionId);
        setUploadErrorSessionId(sessionId);
        setProcessingSessionId(sessionId);
      }
      const existingCount = (materials as any[]).length;
      for (let i = 0; i < arr.length; i++) {
        await uploadMut.mutateAsync({ sessionId: sessionId!, file: arr[i], sortOrder: existingCount + i });
      }
      const proc = await processMut.mutateAsync({ sessionId: sessionId! });
      invalidateAll(sessionId);
      if (uploadedHasAudioVideo) {
        runTranscribe(sessionId!);
      }
      if (wasAppending) {
        sonnerToast.success("素材已追加并处理完成", {
          description: "新证据已加入时间线，请重新生成 AI 总结以纳入新内容",
        });
      }
      void proc;
    } catch (error: any) {
      setUploadError(error?.message || "处理失败");
      invalidateAll(sessionId);
    } finally {
      setUploadRunning(false);
      if (appendToCurrent) setAppendPanelOpen(false);
      setProcessingSessionId(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (appendFileInputRef.current) appendFileInputRef.current.value = "";
    }
  };

  const handleCitationClick = (id: string) => {
    setTimelineVisible(true);
    setHighlightedBlock(id);
    setTimeout(() => {
      const el = document.getElementById(`ev-${id}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const block = displayEvidence.find(b => b.id === id);
      if (block && videoRef.current) {
        const ts = typeof block.timestamp === "number" ? block.timestamp : parseTimestamp(block.timestamp);
        if (ts !== null && !Number.isNaN(ts)) videoRef.current.currentTime = ts;
      }
    }, 300);
    setTimeout(() => setHighlightedBlock(null), 2000);
  };

  const parseTimestamp = (ts: any): number | null => {
    if (typeof ts === "number") return ts;
    const parts = String(ts).split(':');
    if (parts.length === 2) return parseInt(parts[0]) * 60 + parseInt(parts[1]);
    if (parts.length === 3) return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
    return null;
  };

  const [pulseUpload, setPulseUpload] = useState(false);
  const pulseUploadOnce = () => {
    setPulseUpload(true);
    setTimeout(() => setPulseUpload(false), 2000);
  };

  const handleGenerate = async () => {
    if (isMock || !activeSessionId || displayEvidence.length === 0) {
      pulseUploadOnce();
      toast({
        title: "还不能生成总结",
        description: "请等待媒体处理完成并生成证据块后再试。",
        variant: "destructive",
      });
      return;
    }
    if (matchMut.isPending || generateMutation.isPending) return;
    setGenerateError(null);
    try {
      await matchMut.mutateAsync({ sessionId: activeSessionId });
      generateMutation.mutate({ sessionId: activeSessionId });
    } catch {
      setGenerateError("匹配失败，请检查证据块");
    }
  };

  const handleAddLink = async (appendToCurrent = false) => {
    const url = linkInput.trim();
    if (!url) return;
    let sessionId = activeSessionId;
    const wasAppending = appendToCurrent && activeSession?.status === "done";
    setUploadRunning(true);
    setUploadError(null);
    setUploadErrorSessionId(sessionId);
    setProcessingSessionId(sessionId);
    try {
      const needCreate = !realSessions.some(s => s.id === activeSessionId);
      if (needCreate) {
        let title = "链接素材";
        try {
          title = new URL(url).hostname.replace(/^www\./, "") || title;
        } catch {}
        const created = await createSessionMut.mutateAsync({ title });
        sessionId = String(created.id);
        await queryClient2.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
        setActiveSessionId(sessionId);
        setUploadErrorSessionId(sessionId);
        setProcessingSessionId(sessionId);
      }
      const downloaded = await downloadLinkMut.mutateAsync({ sessionId: sessionId!, url });
      await processMut.mutateAsync({ sessionId: sessionId! });
      invalidateAll(sessionId);
      const downloadedMaterials = (downloaded?.materials ?? []) as any[];
      if (downloadedMaterials.some(m => m.type === "audio" || m.type === "video")) {
        runTranscribe(sessionId!);
      }
      if (wasAppending) {
        sonnerToast.success("素材已追加并处理完成", {
          description: "新证据已加入时间线，请重新生成 AI 总结以纳入新内容",
        });
      }
      setLinkInput("");
    } catch (error: any) {
      setUploadError(error?.message || "链接处理失败");
      invalidateAll(sessionId);
    } finally {
      setUploadRunning(false);
      if (appendToCurrent) setAppendPanelOpen(false);
      setProcessingSessionId(null);
    }
  };

  const statusText = (s: string) => s === 'done' ? '已完成' : s === 'processing' ? '处理中' : s === 'failed' ? '失败' : (s || '就绪');
  const isProcessing = uploadMut.isPending || downloadLinkMut.isPending || processMut.isPending || transcribeMut.isPending;
  const pipelineError = uploadError || activeSession?.error_message || generateError || undefined;

  const uploadStatus: UploadStatus = pipelineError && !matchMut.isPending && !generateMutation.isPending
    ? "error"
    : uploadRunning || uploadMut.isPending || processMut.isPending || transcribeMut.isPending
      ? "uploading"
      : (activeSession?.status === 'done' || activeSession?.status === 'processing')
        ? "done"
        : "idle";

  const buttonStatus: ButtonStatus = generateError
    ? "error"
    : matchMut.isPending
      ? "matching"
      : generateMutation.isPending
        ? "summarizing"
        : displaySummary
          ? "done"
          : "idle";

  const canGenerate = !isMock && !matchMut.isPending && !generateMutation.isPending && !!activeSessionId && displayEvidence.length > 0;
  const settingsByKey = useMemo(
    () => new Map((settingsStatus as any[]).map(item => [item.key, item])),
    [settingsStatus]
  );
  const handleSaveSettings = async () => {
    const changed = SETTINGS_FIELDS
      .filter(field => !settingsByKey.get(field.key)?.from_env)
      .map(field => ({
        key: field.key,
        value: (settingsDraft[field.key] || "").trim(),
        is_required: field.required,
      }))
      .filter(item => item.value.length > 0);

    if (changed.length === 0) {
      setShowSettings(false);
      return;
    }
    await updateSettingsMut.mutateAsync({ settings: changed });
  };

  return (
    <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden font-sans">
      <header className="safe-area-top h-12 border-b border-border/40 bg-card flex items-center justify-between px-4 shrink-0 z-10 relative">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-primary">
            <Sparkles className="w-5 h-5" />
            <span className="font-bold tracking-tight">Smart Scribe</span>
          </div>
          <div className="w-px h-4 bg-border max-md:hidden" />
          <input
            key={activeSession?.id || "mock"}
            type="text"
            defaultValue={activeSession?.title || ""}
            onBlur={(e) => {
              const newTitle = e.target.value.trim();
              if (newTitle && activeSessionId && !isMock && newTitle !== activeSession?.title) {
                renameMut.mutate({ sessionId: activeSessionId, title: newTitle });
                queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
              }
            }}
            className="bg-transparent border-none outline-none focus:ring-1 ring-primary rounded px-2 text-sm font-medium w-64 max-md:hidden"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs max-md:hidden">
            {isProcessing ? <Loader2 className="w-3 h-3 animate-spin text-amber-500" /> :
              activeSession?.status === 'done' ? <span className="w-2 h-2 rounded-full bg-green-500" /> :
              isMock ? <span className="w-2 h-2 rounded-full bg-muted-foreground/40" /> : <span className="w-2 h-2 rounded-full bg-primary" />}
            <span className="text-muted-foreground">{isMock ? '演示数据' : statusText(activeSession?.status)}</span>
          </div>
          <button
            disabled={creatingSession}
            onClick={async () => {
              setCreatingSession(true);
              try {
                const created = await createSessionMut.mutateAsync({ clientId, title: "新会话" });
                const sid = String(created.id);
                await queryClient2.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
                setActiveSessionId(sid);
              } finally {
                setCreatingSession(false);
              }
            }}
            className="md:hidden p-1.5 hover:bg-white/10 rounded-md transition-colors text-muted-foreground hover:text-foreground flex items-center gap-1 disabled:opacity-50"
            title="新建会话"
          >
            {creatingSession ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-5 h-5" />}
          </button>
          <button onClick={() => setShowMobileMenu(true)} className="md:hidden p-1.5 hover:bg-white/10 rounded-md">
            <Menu className="w-5 h-5" />
          </button>
          <button onClick={() => setTimelineVisible(true)} className="md:hidden p-1.5 hover:bg-white/10 rounded-md transition-colors text-muted-foreground hover:text-foreground flex items-center gap-1.5">
            <Film className="w-4 h-4" />
            <span className="text-xs font-medium">时间线</span>
          </button>
          <button onClick={() => setIsDark(d => !d)} className="relative w-14 h-7 rounded-full border border-border bg-muted transition-colors hover:border-primary/30">
            <motion.div
              className="absolute top-0.5 w-6 h-6 rounded-full bg-card shadow-sm border border-border/60 flex items-center justify-center"
              animate={{ left: isDark ? 4 : 28 }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            >
              {isDark ? <Moon className="w-3.5 h-3.5 text-white" /> : <Sun className="w-3.5 h-3.5 text-amber-500" />}
            </motion.div>
          </button>
          <button onClick={() => setShowSettings(true)} className="p-1.5 hover:bg-white/10 rounded-md transition-colors text-muted-foreground hover:text-foreground">
            <Settings className="w-4 h-4" />
          </button>
          <button onClick={() => setTimelineVisible(v => !v)} className="max-md:hidden p-1.5 hover:bg-white/10 rounded-md transition-colors text-muted-foreground hover:text-foreground flex items-center gap-1.5">
            {timelineVisible ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
            <span className="text-xs font-medium">时间线</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 min-h-0 items-stretch max-md:flex-col max-md:overflow-y-auto">
        <aside className="w-[220px] md:w-[200px] lg:w-[220px] bg-card/50 flex flex-col shrink-0 border-r-2 border-border/50 z-10 max-md:w-full max-md:border-r-0 max-md:border-b-2">
          <div className="p-4 space-y-3 overflow-x-hidden">
            <input ref={fileInputRef} type="file" multiple accept="video/*,audio/*,image/*" className="hidden" onChange={e => handleFiles(e.target.files)} />
            <AnimatePresence mode="wait">
              {uploadStatus !== "idle" ? (
                <motion.div key="progress" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                  <UploadProgress
                    status={uploadStatus}
                    errorMessage={pipelineError}
                    onDismiss={() => setUploadError(null)}
                    onRetry={async () => {
                      if (!activeSessionId) return;
                      transcribeTriggered.current = "";
                      setUploadError(null);
                      setUploadErrorSessionId(activeSessionId);
                      setProcessingSessionId(activeSessionId);
                      try {
                        const mats = await refetchMaterials();
                        const freshMaterials = (mats.data as any[]) ?? [];
                        // 如果当前会话没有素材但输入框里还有链接，说明之前下载失败，优先重试下载
                        if (freshMaterials.length === 0 && linkInput.trim()) {
                          await handleAddLink();
                          return;
                        }
                        await processMut.mutateAsync({ sessionId: activeSessionId });
                        invalidateAll(activeSessionId);
                        const refreshed = await refetchMaterials();
                        const refreshedMaterials = (refreshed.data as any[]) ?? [];
                        const hasAV = refreshedMaterials.some(m => m.type === "audio" || m.type === "video");
                        if (hasAV) {
                          runTranscribe(activeSessionId);
                        }
                      } catch {
                        // errors surface via mutations
                      } finally {
                        setProcessingSessionId(null);
                      }
                    }}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="entry"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  className="space-y-3"
                >
                  <motion.button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadRunning}
                    animate={pulseUpload ? {
                      borderColor: ["hsl(var(--border))", "rgba(239,68,68,0.9)", "hsl(var(--border))", "rgba(239,68,68,0.7)", "hsl(var(--border))"],
                      boxShadow: ["0 0 0 0 rgba(239,68,68,0)", "0 0 24px 4px rgba(239,68,68,0.35)", "0 0 0 0 rgba(239,68,68,0)", "0 0 18px 2px rgba(239,68,68,0.25)", "0 0 0 0 rgba(239,68,68,0)"],
                      scale: [1, 1.015, 1, 1.01, 1],
                    } : {}}
                    transition={pulseUpload ? { duration: 2, times: [0, 0.25, 0.5, 0.75, 1] } : { duration: 0.2 }}
                    className="w-full rounded-2xl bg-card border-2 border-dashed border-border hover:border-primary/40 transition-colors cursor-pointer group p-5 flex flex-col items-center justify-center gap-3 min-h-[140px] disabled:opacity-60"
                  >
                    <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                      {uploadRunning ? <Loader2 className="w-6 h-6 text-primary animate-spin" /> : <CloudUpload className="w-6 h-6 text-primary group-hover:scale-110 transition-transform" />}
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-semibold text-foreground">{uploadRunning ? "上传中…" : "上传媒体"}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">拖拽文件或点击上传</p>
                      <p className="text-[10px] text-muted-foreground/60 mt-1">mp4 · mp3 · m4a · png · jpg</p>
                    </div>
                  </motion.button>
                  <div className="flex flex-col gap-2">
                    <motion.div
                      animate={pulseUpload ? {
                        borderColor: ["hsl(var(--border))", "rgba(239,68,68,0.7)", "hsl(var(--border))"],
                        boxShadow: ["0 0 0 0 rgba(239,68,68,0)", "0 0 18px 2px rgba(239,68,68,0.25)", "0 0 0 0 rgba(239,68,68,0)"],
                      } : {}}
                      transition={pulseUpload ? { duration: 2, times: [0, 0.3, 1] } : { duration: 0.2 }}
                      className="flex items-center gap-2 px-3 py-2.5 max-md:py-2.5 rounded-xl bg-card/80 border hover:border-primary/30 transition-colors group cursor-text"
                    >
                      <LinkIcon className="w-3.5 h-3.5 text-muted-foreground shrink-0 group-focus-within:text-primary transition-colors" />
                      <input type="text" value={linkInput} onChange={e => setLinkInput(e.target.value)} disabled={uploadRunning || downloadLinkMut.isPending} onKeyDown={e => { if (e.key === 'Enter' && !uploadRunning) handleAddLink(); }} placeholder={uploadRunning || downloadLinkMut.isPending ? "处理中，请稍候..." : "粘贴视频或音频链接..."} className="flex-1 bg-transparent border-none outline-none text-xs placeholder:text-muted-foreground/60 disabled:opacity-50" />
                    </motion.div>
                    <button onClick={() => handleAddLink()} disabled={uploadRunning || downloadLinkMut.isPending || !linkInput.trim()} className="w-full py-2 rounded-lg bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1.5">
                      {uploadRunning || downloadLinkMut.isPending ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> 处理中...</> : "添加链接"}
                    </button>
                  </div>
                </motion.div>
)}
      </AnimatePresence>
    </div>
           <div className="flex-1 overflow-y-auto p-2 space-y-1 max-md:space-y-1.5 max-md:hidden">
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">历史会话</span>
            </div>
            <button
              disabled={creatingSession}
              onClick={async () => {
                setCreatingSession(true);
                try {
                  const created = await createSessionMut.mutateAsync({ clientId, title: "新会话" });
                  const sid = String(created.id);
                  await queryClient2.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
                  setActiveSessionId(sid);
                } finally {
                  setCreatingSession(false);
                }
              }}
              className="w-full mb-1 py-2 rounded-lg border border-dashed border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creatingSession ? (<Loader2 className="w-3 h-3 animate-spin inline-block mr-1" />) : null}+ 新建会话
            </button>
            <div className="group relative hidden">
              <button
                onClick={() => setActiveSessionId(MOCK_SESSION_ID)}
                className={`w-full text-left px-3 py-2 pr-8 rounded-md text-sm flex items-center gap-2 transition-colors ${isMock ? 'bg-primary/10 text-primary' : 'hover:bg-white/5 text-muted-foreground'}`}
              >
                <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40" />
                <span className="truncate">演示会话（mock）</span>
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: MOCK_SESSION_ID, title: "演示会话（mock）" }); }}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all"
                title="删除"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
            {realSessions.map(s => (
              <div key={s.id} className="group relative">
                {renamingId === s.id ? (
                  <input
                    ref={renameInputRef}
                    value={renameDraft}
                    onChange={e => setRenameDraft(e.target.value)}
                    onBlur={() => {
                      if (renameDraft.trim() && renameDraft.trim() !== s.title) {
                        renameMut.mutate({ sessionId: s.id, title: renameDraft.trim() });
                        queryClient.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
                      }
                      setRenamingId(null);
                    }}
                    onKeyDown={e => {
                      if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
                      if (e.key === 'Escape') setRenamingId(null);
                    }}
                    className="w-full text-left px-3 py-2 rounded-md text-sm bg-primary/10 border border-primary/30 outline-none"
                  />
                ) : (
                  <>
                    <button onClick={() => setActiveSessionId(s.id)}
                      onDoubleClick={() => { setRenamingId(s.id); setRenameDraft(s.title); }}
                      className={`w-full text-left px-3 py-2 max-md:py-2.5 pr-8 rounded-md text-sm flex items-center gap-2 transition-colors ${activeSessionId === s.id ? 'bg-primary/10 text-primary' : 'hover:bg-white/5 text-muted-foreground'}`}
                    >
                      <div className={`w-1.5 h-1.5 rounded-full ${s.id === processingSessionId ? 'bg-primary animate-pulse' : s.status === 'failed' ? 'bg-red-500' : s.status === 'done' ? 'bg-emerald-500' : s.status === 'processing' ? 'bg-amber-500' : 'bg-muted-foreground/40'}`} />
                      <span className="truncate">{s.title}</span>
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setRenamingId(s.id); setRenameDraft(s.title); }}
                      className="absolute right-7 top-1/2 -translate-y-1/2 p-1 rounded-md opacity-0 group-hover:opacity-100 max-md:opacity-100 max-md:min-w-[32px] max-md:min-h-[32px] max-md:flex max-md:items-center max-md:justify-center hover:bg-foreground/5 text-muted-foreground hover:text-foreground transition-all"
                      title="重命名"
                    >
                      <Pencil className="w-3 h-3 max-md:w-4 max-md:h-4" />
                    </button>
                  </>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: s.id, title: s.title }); }}
                  className={`absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded-md ${s.status === 'failed' || s.status === 'processing' ? 'opacity-100 text-red-400' : 'opacity-0 group-hover:opacity-100'} max-md:opacity-100 max-md:min-w-[32px] max-md:min-h-[32px] max-md:flex max-md:items-center max-md:justify-center max-md:text-muted-foreground/50 hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-all`}
                  title="删除"
                >
                  <Trash2 className="w-3.5 h-3.5 max-md:w-4 max-md:h-4" />
                </button>
              </div>
            ))}
            {sessionsFetching && realSessions.length === 0 && (
              <div className="px-3 py-2 text-xs text-muted-foreground/60 flex items-center gap-2"><Loader2 className="w-3 h-3 animate-spin" /> 加载中…</div>
            )}
          </div>
        </aside>

        <main key={activeSessionId || "empty"} className="relative flex-1 flex flex-col bg-background max-md:min-h-0 max-md:flex-none">
          <div className="px-5 pt-4 pb-3 flex items-center justify-between gap-3 sticky top-0 bg-background/95 backdrop-blur z-10 border-b border-border/50">
            <div className="flex items-center gap-2.5">
              <Sparkles className="w-5 h-5 text-primary" />
              <span className="font-semibold text-base">AI 总结</span>
            </div>
            {activeSession?.status === "done" && !isMock && (
              <div className="relative">
                <input
                  ref={appendFileInputRef}
                  type="file"
                  multiple
                  accept="video/*,audio/*,image/*"
                  className="hidden"
                  onChange={(e) => handleFiles(e.target.files, true)}
                />
                <button
                  onClick={() => setAppendPanelOpen((v) => !v)}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-primary/20 bg-primary px-3 text-xs font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
                >
                  <Plus className="h-3.5 w-3.5" />
                  补充资料
                </button>
                <AnimatePresence>
                  {appendPanelOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -4, scale: 0.98 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: -4, scale: 0.98 }}
                      className="absolute right-0 top-10 z-30 w-[340px] max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-popover p-3 shadow-xl max-md:fixed max-md:left-4 max-md:right-4 max-md:top-16 max-md:w-auto"
                    >
                      <div className="mb-3 flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-semibold text-foreground">补充到当前会话</div>
                          <p className="mt-1 text-xs leading-5 text-muted-foreground">
                            新素材会进入时间线；总结需要重新生成后才会纳入新内容。
                          </p>
                        </div>
                        <button
                          onClick={() => setAppendPanelOpen(false)}
                          className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                          aria-label="关闭补充资料"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                      <button
                        onClick={() => appendFileInputRef.current?.click()}
                        disabled={uploadRunning}
                        className="mb-2 inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-lg border border-dashed border-primary/40 bg-primary/5 px-3 text-sm font-medium text-primary transition-colors hover:bg-primary/10 disabled:opacity-50"
                      >
                        {uploadRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <CloudUpload className="h-4 w-4" />}
                        上传本地素材
                      </button>
                      <div className="flex items-center gap-2 rounded-lg border border-border bg-background/60 px-3 py-2">
                        <LinkIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <input
                          type="text"
                          value={linkInput}
                          onChange={(e) => setLinkInput(e.target.value)}
                          disabled={uploadRunning || downloadLinkMut.isPending}
                          onKeyDown={(e) => { if (e.key === "Enter" && linkInput.trim()) handleAddLink(true); }}
                          placeholder="粘贴要补充的视频或音频链接"
                          className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/60 disabled:opacity-50"
                        />
                        <button
                          onClick={() => handleAddLink(true)}
                          disabled={uploadRunning || downloadLinkMut.isPending || !linkInput.trim()}
                          className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-opacity disabled:opacity-40"
                        >
                          添加
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </div>
          <div
            ref={mainScrollRef}
            onScroll={(e) => setShowBackToTop(e.currentTarget.scrollTop > 420)}
            className="flex-1 overflow-y-auto px-5 pb-20 pt-4 space-y-4 flex flex-col items-center max-md:overflow-visible"
          >
            <div id="island-btn">
            <IslandButton
              status={buttonStatus}
              generable={canGenerate || isMock}
              onGenerate={handleGenerate}
              onRegenerate={handleGenerate}
              mediaUrl={currentPreview?.url}
              mediaType={currentPreview?.type as any}
              videoRef={videoRef}
              errorMessage={generateError || undefined}
              onPrev={hasPrevMaterial ? goToPrevMaterial : undefined}
              onNext={hasNextMaterial ? goToNextMaterial : undefined}
              hasPrev={hasPrevMaterial}
              hasNext={hasNextMaterial}
              sessionId={activeSessionId}
              materialId={currentPreview?.id}
              onFrameCaptured={() => {
                refetchEvidence();
                invalidateAll(activeSessionId);
              }}
            />
            </div>

            {displaySummary && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-[640px] space-y-3">
                <div className="flex items-center gap-2 flex-wrap">
                  {displaySummary.citation_valid && (
                    <div className="inline-flex items-center gap-1.5 text-xs text-green-500 bg-green-500/10 px-3 py-1.5 rounded-full border border-green-500/20">
                      <CheckCircle className="w-3.5 h-3.5 shrink-0" /> 引用校验通过
                    </div>
                  )}
                  <button
                    onClick={async () => {
                      try {
                        const result = await exportMdMut.mutateAsync({ sessionId: activeSessionId });
                        await navigator.clipboard.writeText(result.markdown);
                        alert(`已复制到剪贴板\n保存为 ${result.filename}`);
                      } catch (e: any) {
                        alert(`导出失败：${e?.message || '未知错误'}`);
                      }
                    }}
                    disabled={exportMdMut.isPending}
                    className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary shadow-sm transition-colors hover:bg-primary/15 disabled:opacity-50"
                  >
                    {exportMdMut.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Copy className="w-3.5 h-3.5" />}
                    复制 MD
                  </button>
                </div>

                <motion.div
                  animate={justGenerated ? { scale: [1, 1.03, 1] } : {}}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                >
                  <CollapsibleCard icon={ListChecks} title="核心要点" defaultOpen={showKeyPoints}>
                    <div className="space-y-3">
                      {displaySummary.key_points.map((kp, idx) => (
                        <motion.div
                          key={idx}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: idx * 0.08 }}
                          className="flex gap-3 rounded-lg border border-border/50 bg-background/70 p-3 transition-colors cursor-pointer group hover:border-primary/30 hover:bg-muted/40"
                          onClick={() => {
                            if (kp.citations.length > 0) handleCitationClick(kp.citations[0]);
                          }}
                        >
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary text-primary-foreground border border-primary/20 flex items-center justify-center text-xs font-semibold mt-0.5 group-hover:scale-110 transition-transform">
                            {idx + 1}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-[14px] text-foreground/90 leading-7">{kp.point}</p>
                            <div className="flex flex-wrap gap-1.5 mt-1.5">
                              {kp.citations.map(c => {
                                const ev = displayEvidence.find(e => e.id === c);
                                return <CitationTag key={c} id={c} type={ev?.type || 'speech'} onClick={() => handleCitationClick(c)} />;
                              })}
                            </div>
                          </div>
                          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/30 mt-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </motion.div>
                      ))}
                    </div>
                  </CollapsibleCard>
                </motion.div>

                <CollapsibleCard icon={Sparkles} title="摘要" defaultOpen={true}>
                  <div className="rounded-lg border border-border/50 bg-background/70 p-4 text-[14px] leading-7 text-foreground/90">{displaySummary.summary}</div>
                </CollapsibleCard>

              </motion.div>
            )}
            {displayEvidence.length > 0 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-[640px]">
                <CollapsibleCard icon={ScanLine} title={`详细原文 · ${displayEvidence.length} 块`} defaultOpen={!displaySummary}>
                  <div className="space-y-2">
                    {displayEvidence.map((block) => {
                      const isSpeech = block.type === "speech";
                      return (
                        <div key={block.id} className="rounded-lg border border-border/60 bg-background/70 p-3">
                          <div className="mb-1.5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                            <span className={`rounded-md border px-1.5 py-0.5 font-mono font-bold ${isSpeech ? "border-primary/20 bg-primary/10 text-primary" : "border-slate-500/25 bg-slate-500/10 text-slate-600 dark:text-slate-300"}`}>
                              {block.id}
                            </span>
                            <span className="font-mono">{fmtTimestamp(block.timestamp)}</span>
                            {block.speaker && <span>{block.speaker}</span>}
                            {block.is_manual && <span className="rounded-md bg-amber-400/15 px-1.5 py-0.5 text-amber-600 dark:text-amber-300">手动选帧</span>}
                          </div>
                          <p className="whitespace-pre-wrap text-[13px] leading-6 text-foreground/80">
                            {block.text || "（无文字内容）"}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </CollapsibleCard>
              </motion.div>
            )}
            {displaySummary && displaySummary.unused_block_ids.length > 0 && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="w-full max-w-[640px]">
                <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 overflow-hidden">
                  <div className="px-4 py-3 flex items-center gap-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    <TriangleAlert className="w-3.5 h-3.5 text-amber-500" /> 未被引用
                  </div>
                  <div className="px-4 pb-3 flex flex-wrap gap-1.5">
                    {displaySummary.unused_block_ids.map(id => (
                      <span key={id} className="px-2.5 py-1 rounded-lg border border-border bg-background/50 text-xs font-mono text-muted-foreground">{id}</span>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
            {!displaySummary && !isMock && displayEvidence.length === 0 && (
              <div className="text-center text-xs text-muted-foreground/50 py-8">先上传媒体、处理生成证据块后，点击上方按钮生成总结</div>
            )}
            <div className="md:hidden mt-4 w-full max-w-[520px]">
              <CollapsibleCard icon={Film} title={`原文证据 · ${displayEvidence.length} 块`} defaultOpen={false}>
                <div className="space-y-3">
                  {displayEvidence.map((block, i) => {
                    const isSpeech = block.type === 'speech';
                    const isHighlighted = highlightedBlock === block.id;
                    return (
                      <motion.div id={`ev-${block.id}`} key={block.id}
                        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }} whileHover={{ scale: 1.005, x: 2 }}
                        className={`relative p-3 rounded-xl border bg-card cursor-pointer transition-all duration-300
                          ${isSpeech ? 'border-l-4 border-l-primary' : 'border-l-4 border-l-slate-500'}
                          ${isHighlighted ? 'ring-2 ring-primary shadow-[0_0_15px_rgba(233,69,96,0.3)] scale-[1.01]' : 'border-border hover:border-border/80'}`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`px-1.5 py-0.5 rounded border text-[10px] font-mono flex items-center gap-1.5 ${isSpeech ? 'border-primary/20 bg-primary/10 text-primary' : 'border-slate-500/25 bg-slate-500/10 text-slate-600 dark:text-slate-300'}`}>
                            {isSpeech ? <Mic2 className="w-3 h-3" /> : <ImageIcon className="w-3 h-3" />}
                            {block.id}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-mono text-muted-foreground hover:text-primary transition-colors cursor-pointer"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (currentPreview?.type === "video" || currentPreview?.type === "audio") {
                                    document.getElementById("island-btn")?.scrollIntoView({ behavior: "smooth", block: "start" });
                                    const ts = typeof block.timestamp === "number" ? block.timestamp : parseTimestamp(block.timestamp);
                                    setTimeout(() => {
                                      if (videoRef.current && ts !== null && !Number.isNaN(ts)) videoRef.current.currentTime = ts;
                                    }, 400);
                                  }
                                }}
                              >
                                ▶ {fmtTimestamp(block.timestamp)}
                              </span>
                              {block.speaker && <span className="text-xs font-medium text-foreground/80">{block.speaker}</span>}
                            </div>
                            <p className="text-sm text-foreground/90 leading-relaxed">{block.text}</p>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                  {displayEvidence.length === 0 && !isMock && (
                    <div className="text-center text-xs text-muted-foreground/50 py-4">暂无证据块，上传媒体后自动处理生成</div>
                  )}
                  {displayEvidence.length === 0 && isMock && (
                    <div className="text-center text-xs text-muted-foreground/50 py-4">演示数据 · 点击证据块 ID 跳转</div>
                  )}
                </div>
              </CollapsibleCard>
            </div>
          </div>
          <AnimatePresence>
            {showBackToTop && (
              <motion.button
                initial={{ opacity: 0, y: 8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.96 }}
                transition={{ duration: 0.16, ease: "easeOut" }}
                onClick={() => mainScrollRef.current?.scrollTo({ top: 0, behavior: "smooth" })}
                className="absolute bottom-5 left-1/2 z-30 inline-flex h-10 -translate-x-1/2 items-center gap-2 rounded-full border border-primary/20 bg-primary px-4 text-sm font-semibold text-primary-foreground shadow-lg shadow-black/10 backdrop-blur transition-colors hover:bg-primary/90"
                aria-label="回到顶部"
                title="回到顶部"
              >
                <ArrowUp className="h-4 w-4" />
                <span>回到顶部</span>
              </motion.button>
            )}
          </AnimatePresence>
        </main>

        <div className="hidden md:block self-stretch flex flex-col min-h-0 bg-card">
        <AnimatePresence>
              {timelineVisible && !isMobile ? (
                <motion.aside
                  key="timeline-open"
                  initial={{ width: 0, opacity: 0 }}
                  animate={{ width: 465, opacity: 1 }}
                  exit={{ width: 0, opacity: 0 }}
                  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                  className="flex-1 flex flex-col bg-card border-l border-border z-10 overflow-hidden max-md:hidden"
                >
                  <TimelinePanel
                    blocks={displayEvidence}
                    highlightedBlock={highlightedBlock}
                    onBlockClick={(id) => {
                      setHighlightedBlock(highlightedBlock === id ? null : id);
                      document.getElementById(`ev-${id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
                    }}
                    onTimestampClick={(block) => {
                      if (currentPreview?.type === "video" || currentPreview?.type === "audio") {
                        const ts = typeof block.timestamp === "number" ? block.timestamp : parseTimestamp(block.timestamp);
                        if (videoRef.current && ts !== null && !Number.isNaN(ts)) videoRef.current.currentTime = ts;
                      }
                    }}
                    currentPreviewType={currentPreview?.type}
                    videoRef={videoRef}
                  />
                </motion.aside>
              ) : null}
            </AnimatePresence>
        </div>

      </div>

      <AnimatePresence>
        {timelineVisible && isMobile && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[70] md:hidden"
            onClick={() => setTimelineVisible(false)}
          >
            <motion.div initial={{ x: "100%" }} animate={{ x: 0 }} exit={{ x: "100%" }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              onClick={e => e.stopPropagation()}
              className="absolute right-0 inset-y-0 w-full max-w-[400px] bg-card border-l border-border shadow-2xl flex flex-col"
            >
              <div className="safe-area-top shrink-0 flex items-center justify-between px-4 py-3 border-b border-border bg-card">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <Film className="w-4 h-4 text-primary" /> 时间线 · 证据块
                </div>
                <button onClick={() => setTimelineVisible(false)} className="p-1.5 rounded-md hover:bg-foreground/5 text-muted-foreground hover:text-foreground transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-hidden safe-area-pad">
                <TimelinePanel
                  blocks={displayEvidence}
                  highlightedBlock={highlightedBlock}
                  onBlockClick={(id) => {
                    setHighlightedBlock(highlightedBlock === id ? null : id);
                    setTimelineVisible(false);
                  }}
                  onTimestampClick={(block) => {
                    setTimelineVisible(false);
                    if (currentPreview?.type === "video" || currentPreview?.type === "audio") {
                      const ts = typeof block.timestamp === "number" ? block.timestamp : parseTimestamp(block.timestamp);
                      setTimeout(() => {
                        if (videoRef.current && ts !== null && !Number.isNaN(ts)) videoRef.current.currentTime = ts;
                      }, 300);
                    }
                  }}
                  currentPreviewType={currentPreview?.type}
                  videoRef={videoRef}
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showMobileMenu && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 md:hidden"
            onClick={() => setShowMobileMenu(false)}
          >
            <motion.div initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }}
              transition={{ type: "spring", damping: 30, stiffness: 400 }}
              onClick={e => e.stopPropagation()}
              className="safe-area-pad w-[280px] h-full bg-card border-r border-border overflow-y-auto p-4"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="font-semibold text-base">历史会话</span>
                <button onClick={() => setShowMobileMenu(false)} className="p-1 text-muted-foreground hover:text-foreground">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <button onClick={() => { setActiveSessionId(MOCK_SESSION_ID); setShowMobileMenu(false); }}
                className="hidden w-full text-left px-3 py-2 rounded-md text-sm flex items-center gap-2 mb-1 transition-colors"
              >
                <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40" />
                演示会话（mock）
              </button>
              {realSessions.map(s => (
                <div key={s.id} className="group relative">
                  <button onClick={() => { setActiveSessionId(s.id); setShowMobileMenu(false); }}
                    className="w-full text-left px-3 py-2 pr-8 rounded-md text-sm flex items-center gap-2 transition-colors hover:bg-white/5 text-muted-foreground"
                  >
                    <div className={`w-1.5 h-1.5 rounded-full ${s.id === processingSessionId ? 'bg-primary animate-pulse' : s.status === 'failed' ? 'bg-red-500' : s.status === 'done' ? 'bg-emerald-500' : s.status === 'processing' ? 'bg-amber-500' : 'bg-muted-foreground/40'}`} />
                    {s.title}
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: s.id, title: s.title }); }}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1.5 opacity-0 group-hover:opacity-100 max-md:opacity-100 min-w-[32px] min-h-[32px] flex items-center justify-center text-muted-foreground/50 hover:text-red-400">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              <button
                disabled={creatingSession}
                onClick={async () => {
                  setCreatingSession(true);
                  try {
                    const created = await createSessionMut.mutateAsync({ clientId, title: "新会话" });
                    const sid = String(created.id);
                    await queryClient2.invalidateQueries({ queryKey: getListSessionsQueryKey(clientId) });
                    setActiveSessionId(sid);
                    setShowMobileMenu(false);
                  } finally {
                    setCreatingSession(false);
                  }
                }}
                className="w-full mt-3 py-2 rounded-lg border border-dashed border-border text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                {creatingSession ? (<Loader2 className="w-3 h-3 animate-spin inline-block mr-1" />) : null}+ 新建会话
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {deleteTarget && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4"
            onClick={() => setDeleteTarget(null)}
          >
            <motion.div
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              onClick={e => e.stopPropagation()}
              className="bg-card border border-border rounded-2xl p-6 w-full max-w-sm shadow-2xl max-md:rounded-b-none max-md:fixed max-md:bottom-0 max-md:left-0 max-md:right-0 max-md:max-w-none"
              style={{ paddingBottom: 'calc(1.5rem + env(safe-area-inset-bottom, 0px))' }}
            >
              <h3 className="font-semibold text-foreground text-lg mb-2">删除会话</h3>
              <p className="text-sm text-muted-foreground mb-6">
                确定删除「{deleteTarget.title}」吗？<br />
                <span className="text-red-400 text-xs">媒体文件、证据块、总结将一并清除。</span>
              </p>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setDeleteTarget(null)}
                  className="px-4 py-2 rounded-lg text-sm font-medium hover:bg-foreground/5 transition-colors">
                  取消
                </button>
                <button onClick={() => {
                  deleteMut.mutate({ sessionId: deleteTarget.id });
                  if (activeSessionId === deleteTarget.id) {
                    const remaining = realSessions.filter(s => s.id !== deleteTarget.id);
                    if (remaining.length > 0) setActiveSessionId(remaining[0].id);
                    else setActiveSessionId("");
                  }
                }}
                  disabled={deleteMut.isPending}
                  className="px-4 py-2 rounded-lg bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-2">
                  {deleteMut.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  删除
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showSettings && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowSettings(false)}
          >
            <motion.div initial={{ scale: 0.95, y: 10 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 10 }}
              onClick={e => e.stopPropagation()}
              className="bg-card border border-border rounded-2xl p-6 w-full max-w-md shadow-2xl max-md:rounded-b-none max-md:fixed max-md:bottom-0 max-md:left-0 max-md:right-0 max-md:max-w-none max-md:rounded-t-2xl overflow-hidden"
              style={{ paddingBottom: 'calc(1.5rem + env(safe-area-inset-bottom, 0px))' }}
            >
              <div className="p-4 border-b border-border flex items-center justify-between bg-black/20">
                <div className="flex items-center gap-2">
                  <KeyRound className="w-4 h-4 text-primary" />
                  <span className="font-semibold text-sm">API 设置</span>
                </div>
                <button onClick={() => setShowSettings(false)} className="text-muted-foreground hover:text-foreground">
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
              <div className="p-5 space-y-5">
                {ephemeralInfo?.enabled && (
                  <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>
                      关闭标签后清除模式：关闭此浏览器标签约 {ephemeralInfo.ttl ?? 60} 秒后，该会话的媒体与记录将被自动删除，请及时复制结果。
                    </span>
                  </div>
                )}
                {SETTINGS_FIELDS.map(field => {
                  const status = settingsByKey.get(field.key);
                  const isSet = Boolean(status?.is_set);
                  const fromEnv = Boolean(status?.from_env);
                  return (
                    <div key={field.key} className="space-y-1.5">
                      <label className="text-xs font-mono text-muted-foreground">
                        {field.label}
                        <span className={`ml-2 text-[10px] font-sans ${field.required ? "text-red-400" : "text-muted-foreground"}`}>
                          {field.required ? "必填" : "可选"}
                        </span>
                        {fromEnv && <span className="ml-2 text-[10px] text-emerald-400 font-sans">✓ 由部署者配置</span>}
                        {!fromEnv && isSet && <span className="ml-2 text-[10px] text-emerald-400 font-sans">已保存</span>}
                      </label>
                      <input
                        type="password"
                        value={fromEnv ? "" : (settingsDraft[field.key] || "")}
                        onChange={e => setSettingsDraft(d => ({ ...d, [field.key]: e.target.value }))}
                        disabled={fromEnv}
                        placeholder={fromEnv ? "已由部署者通过环境变量配置，无需填写" : (isSet ? "已保存，留空保持不变" : field.placeholder)}
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:border-primary outline-none font-mono disabled:opacity-60 disabled:cursor-not-allowed"
                      />
                    </div>
                  );
                })}
                {updateSettingsMut.isError && (
                  <p className="text-xs text-red-400">保存失败，请检查后端服务状态</p>
                )}
              </div>
              <div className="p-4 border-t border-border flex justify-end gap-2">
                <button onClick={() => setShowSettings(false)} className="px-4 py-2 rounded-lg text-sm font-medium hover:bg-white/5 transition-colors">取消</button>
                <button
                  onClick={handleSaveSettings}
                  disabled={updateSettingsMut.isPending}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-all disabled:opacity-60 flex items-center gap-2"
                >
                  {updateSettingsMut.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  保存
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

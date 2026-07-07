import { motion, AnimatePresence } from "framer-motion";
import { Upload, Check, AlertCircle, Loader2, RefreshCw, X } from "lucide-react";
import type { ProcessingProgress } from "@/lib/api";
import { getFriendlyProgressMessage } from "@/lib/progress-copy";

export type UploadStatus =
  | "idle"
  | "uploading"
  | "done"
  | "error";

interface Props {
  status: UploadStatus;
  errorMessage?: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  progress?: ProcessingProgress;
}

const statusMap: Record<UploadStatus, { label: string; accent: string }> = {
  idle: { label: "待上传", accent: "text-muted-foreground" },
  uploading: { label: "处理中…", accent: "text-primary" },
  done: { label: "上传完成", accent: "text-emerald-400" },
  error: { label: "处理失败", accent: "text-red-400" },
};

export default function UploadProgress({ status, errorMessage, onRetry, onDismiss, progress }: Props) {
  const info = statusMap[status];
  const liveProgress = progress?.status === "processing" ? progress : null;

  return (
    <div className="flex flex-col items-center justify-center gap-3 w-full min-h-[140px] max-md:min-h-[100px] rounded-2xl bg-card border-2 border-dashed border-border/60 select-none">
      <AnimatePresence mode="wait">
        <motion.div
          key={status}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25 }}
          className="flex flex-col items-center gap-3"
        >
          <ProgressIcon status={status} />

          <div className="text-center">
            <p className={`text-sm font-semibold ${info.accent}`}>{liveProgress?.label || info.label}</p>
            {liveProgress && (
              <>
                <p className="mt-1 max-w-[190px] text-[10px] leading-4 text-muted-foreground/70">
                  {getFriendlyProgressMessage(liveProgress)}
                </p>
                <p className="mt-1 text-[11px] font-mono text-muted-foreground">
                  当前 {formatDuration(liveProgress.stage_elapsed_seconds)} · 总计 {formatDuration(liveProgress.elapsed_seconds)}
                </p>
              </>
            )}
            {status === "done" && (
              <p className="text-[11px] text-muted-foreground/70 mt-0.5">点击右侧「生成知识笔记」</p>
            )}
          </div>

          {status === "error" && (
            <div className="flex flex-col items-center gap-2">
              <p className="text-[11px] text-red-400/70 text-center max-w-[200px] max-md:max-w-[180px]">
                {errorMessage || "请检查文件或 API 设置"}
              </p>
              <div className="flex items-center gap-2">
                {onRetry && (
                  <button
                    onClick={onRetry}
                    className="px-4 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
                  >
                    <RefreshCw className="w-3 h-3" /> 重新处理
                  </button>
                )}
                {onDismiss && (
                  <button
                    onClick={onDismiss}
                    aria-label="关闭错误提示"
                    className="px-2 py-1.5 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:bg-foreground/5 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          )}
          {liveProgress && liveProgress.completed_stages.length > 0 && (
            <div className="flex max-w-[200px] flex-wrap justify-center gap-1">
              {liveProgress.completed_stages.slice(-3).map((stage) => (
                <span key={`${stage.stage}-${stage.duration_seconds}`} className="rounded-md bg-foreground/5 px-1.5 py-0.5 text-[9px] text-muted-foreground">
                  {stage.label} {formatDuration(stage.duration_seconds)}
                </span>
              ))}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

function formatDuration(seconds: number) {
  const value = Math.max(0, Math.floor(seconds || 0));
  if (value < 60) return `${value}s`;
  return `${Math.floor(value / 60)}m ${value % 60}s`;
}

function ProgressIcon({ status }: { status: UploadStatus }) {
  if (status === "done") {
    return (
      <motion.div
        initial={{ scale: 0.6 }} animate={{ scale: 1 }}
        transition={{ type: "spring", stiffness: 500, damping: 18 }}
        className="w-10 h-10 rounded-xl border border-border/40 bg-foreground/5 flex items-center justify-center text-emerald-400"
      >
        <Check className="w-5 h-5" strokeWidth={3} />
      </motion.div>
    );
  }
  if (status === "error") {
    return (
      <motion.div initial={{ scale: 0.6 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 500, damping: 18 }}
        className="w-10 h-10 rounded-xl border border-red-400/30 bg-red-500/10 flex items-center justify-center text-red-400">
        <AlertCircle className="w-5 h-5" />
      </motion.div>
    );
  }
  if (status === "uploading") {
    return (
      <motion.div animate={{ y: [0, -4, 0] }} transition={{ duration: 0.9, repeat: Infinity, ease: "easeInOut" }}
        className="w-10 h-10 rounded-xl border border-primary/30 bg-primary/10 flex items-center justify-center text-primary">
        <Upload className="w-5 h-5" />
      </motion.div>
    );
  }
  return <Upload className="w-5 h-5 text-muted-foreground" />;
}

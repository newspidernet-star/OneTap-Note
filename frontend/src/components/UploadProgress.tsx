import { motion, AnimatePresence } from "framer-motion";
import { Upload, Check, AlertCircle, Loader2, RefreshCw, X } from "lucide-react";

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
}

const statusMap: Record<UploadStatus, { label: string; accent: string }> = {
  idle: { label: "待上传", accent: "text-muted-foreground" },
  uploading: { label: "处理中…", accent: "text-blue-400" },
  done: { label: "上传完成", accent: "text-emerald-400" },
  error: { label: "处理失败", accent: "text-red-400" },
};

export default function UploadProgress({ status, errorMessage, onRetry, onDismiss }: Props) {
  const info = statusMap[status];

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
            <p className={`text-sm font-semibold ${info.accent}`}>{info.label}</p>
            {status === "done" && (
              <p className="text-[11px] text-muted-foreground/70 mt-0.5">点击右侧「生成 AI 总结」</p>
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
        </motion.div>
      </AnimatePresence>
    </div>
  );
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
        className="w-10 h-10 rounded-xl border border-blue-400/30 bg-blue-500/10 flex items-center justify-center text-blue-400">
        <Upload className="w-5 h-5" />
      </motion.div>
    );
  }
  return <Upload className="w-5 h-5 text-muted-foreground" />;
}

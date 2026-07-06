import React, { useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Film, X, Upload, ScanLine, Mic2, Link2, Sparkles, Check, AlertCircle } from "lucide-react";

export type IslandStatus =
  | "idle"
  | "uploading"
  | "ocr"
  | "transcribing"
  | "matching"
  | "summarizing"
  | "done"
  | "error";

interface Props {
  status: IslandStatus;
  uploadProgress?: number;
  mediaUrl?: string;
  mediaType?: "video" | "audio" | "image";
  videoRef?: React.RefObject<HTMLVideoElement>;
  onToggle: () => void;
  expanded: boolean;
  errorMessage?: string;
}

const statusConfig: Record<IslandStatus, { icon: any; label: string; accent: string }> = {
  idle: { icon: Film, label: "查看媒体", accent: "text-primary" },
  uploading: { icon: Upload, label: "上传中", accent: "text-primary" },
  ocr: { icon: ScanLine, label: "OCR 识别", accent: "text-amber-400" },
  transcribing: { icon: Mic2, label: "转写", accent: "text-emerald-400" },
  matching: { icon: Link2, label: "匹配", accent: "text-primary" },
  summarizing: { icon: Sparkles, label: "总结", accent: "text-amber-300" },
  done: { icon: Check, label: "完成", accent: "text-emerald-400" },
  error: { icon: AlertCircle, label: "失败", accent: "text-red-400" },
};

export default function DynamicIsland({
  status, uploadProgress = 0, mediaUrl, mediaType, videoRef, onToggle, expanded, errorMessage,
}: Props) {
  const cfg = statusConfig[status];
  const canExpand = (status === "idle" || status === "done") && mediaUrl;

  return (
    <div className="flex justify-center w-full pt-3 pb-2 relative">
      <motion.div
        layout
        layoutId="island"
        className="relative overflow-hidden rounded-2xl border border-border/60 bg-card text-card-foreground shadow-[0_8px_30px_-8px_rgba(0,0,0,0.35),0_16px_48px_-16px_rgba(0,0,0,0.15)]"
      >
        <motion.div
          layout
          className="flex items-center justify-center"
          animate={{
            width: expanded ? (mediaType === "image" ? 400 : 560) : 220,
            height: expanded ? (mediaType === "image" ? 250 : mediaType === "audio" ? 150 : 315) : 46,
          }}
          transition={{ type: "spring", stiffness: 380, damping: 30, mass: 0.9 }}
        >
          <AnimatePresence mode="wait">
            {expanded && canExpand ? (
              <motion.div
                key="expanded"
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.85 }}
                transition={{ duration: 0.2 }}
                className="relative w-full h-full bg-black"
              >
                {mediaType === "video" && mediaUrl && (
                  <video
                    ref={videoRef}
                    src={mediaUrl}
                    controls
                    autoPlay
                    className="w-full h-full object-contain"
                    style={{ borderRadius: "inherit" }}
                  />
                )}
                {mediaType === "audio" && mediaUrl && (
                  <div className="flex flex-col items-center justify-center h-full gap-3 p-3 bg-gradient-to-b from-[#1a1a2e] to-[#0a0a0c]">
                    <div className="w-14 h-14 rounded-full bg-white/5 border border-white/10 flex items-center justify-center">
                      <Mic2 className="w-6 h-6 text-primary" />
                    </div>
                    <audio ref={videoRef as any} src={mediaUrl} controls autoPlay className="w-4/5" />
                  </div>
                )}
                {mediaType === "image" && mediaUrl && (
                  <img src={mediaUrl} className="w-full h-full object-contain bg-black" style={{ borderRadius: "inherit" }} alt="media" />
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); onToggle(); }}
                  className="absolute top-2 right-2 w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition-colors backdrop-blur-sm border border-white/10"
                  title="收起"
                >
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            ) : (
              <motion.button
                key="collapsed"
                layout
                onClick={canExpand ? onToggle : undefined}
                className="flex items-center gap-2.5 px-4 h-full cursor-pointer disabled:cursor-default select-none"
                disabled={!canExpand}
              >
                <IslandStatusIcon status={status} cfg={cfg} />
                <span className="text-sm font-medium text-foreground/90 whitespace-nowrap">{cfg.label}</span>
                {status === "uploading" && uploadProgress > 0 && (
                  <span className="text-xs font-mono text-primary ml-0.5">{Math.round(uploadProgress)}%</span>
                )}
                {status === "error" && errorMessage && (
                  <span className="text-xs text-red-400/80 truncate max-w-[120px] ml-1">{errorMessage}</span>
                )}
                {canExpand && (
                  <span className="ml-1 text-[10px] text-muted-foreground/50 font-mono uppercase tracking-wider">点击展开</span>
                )}
              </motion.button>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </div>
  );
}

function IslandStatusIcon({ status, cfg }: { status: IslandStatus; cfg: any }) {
  const cls = `w-5 h-5 ${cfg.accent}`;
  if (status === "uploading") {
    return (
      <motion.div animate={{ y: [0, -3, 0] }} transition={{ duration: 0.8, repeat: Infinity }}>
        <Upload className={cls} />
      </motion.div>
    );
  }
  if (status === "ocr") {
    return <motion.div animate={{ x: [0, 4, 0] }} transition={{ duration: 0.6, repeat: Infinity }}><ScanLine className={cls} /></motion.div>;
  }
  if (status === "transcribing") {
    return <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: "linear" }}><Mic2 className={cls} /></motion.div>;
  }
  if (status === "matching") {
    return (
      <div className="flex gap-1 items-center">
        {[0, 1, 2].map(i => (
          <motion.span key={i} className="w-1.5 h-1.5 rounded-full bg-primary"
            animate={{ y: [0, -5, 0] }} transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.15 }}
          />
        ))}
      </div>
    );
  }
  if (status === "summarizing") {
    return (
      <div className="flex items-end gap-1 h-5">
        {[0.4, 0.7, 1].map((h, i) => (
          <motion.span key={i} className="w-1 rounded-full bg-amber-300"
            animate={{ scaleY: [h * 0.3, h, h * 0.3] }}
            transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.1, ease: "easeInOut" }}
            style={{ height: "100%", originY: 1 }}
          />
        ))}
      </div>
    );
  }
  if (status === "done") {
    return (
      <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 500, damping: 20 }}>
        <Check className={cls} strokeWidth={3} />
      </motion.div>
    );
  }
  if (status === "error") {
    return (
      <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 500, damping: 20 }}>
        <AlertCircle className={cls} />
      </motion.div>
    );
  }
  return <Film className={cls} />;
}

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Check, AlertCircle, RefreshCw, Mic2, ArrowRight } from "lucide-react";
import { SummaryHeroCard, type SummaryCTAState } from "@/components/SummaryHeroCard";
import AudioPlayer from "@/components/ui/audio-player";

export type ButtonStatus =
  | "idle"
  | "uploading"
  | "ocr"
  | "transcribing"
  | "matching"
  | "summarizing"
  | "done"
  | "error";

interface Props {
  status: ButtonStatus;
  generable: boolean;
  size?: "large" | "compact";
  onGenerate: () => void;
  onRegenerate?: () => void;
  disabled?: boolean;
  mediaUrl?: string;
  mediaType?: "video" | "audio" | "image";
  videoRef?: React.RefObject<HTMLVideoElement>;
  errorMessage?: string;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
  sessionId?: string;
  materialId?: number;
  onFrameCaptured?: () => void;
}

const stageIndex: Record<string, number> = {
  uploading: 0,
  ocr: 1,
  transcribing: 2,
  matching: 3,
  summarizing: 4,
};

export default function IslandButton({
  status, generable, size = "large", onGenerate, onRegenerate, disabled = false,
  mediaUrl, mediaType, videoRef, errorMessage,
  onPrev, onNext, hasPrev, hasNext,
  sessionId, materialId, onFrameCaptured,
}: Props) {
  const hasMedia = !!(mediaUrl && mediaType);
  const isLarge = size === "large";

  const isPipeline = ["uploading", "ocr", "transcribing", "matching", "summarizing"].includes(status);
  const showHeroCard = isLarge && (
    status === "idle" ||
    status === "error" ||
    isPipeline ||
    (status === "done" && !hasMedia)
  );

  const heroState: SummaryCTAState =
    status === "error" ? "error"
    : status === "done" && !hasMedia ? "generated"
    : isPipeline ? "loading"
    : "idle";

  return (
    <motion.div
      className="w-full"
    >
      <AnimatePresence mode="wait">
        {showHeroCard && (
          <motion.div
            key="hero"
            layout
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.25 }}
            className="w-full"
          >
            <SummaryHeroCard
              state={heroState}
              currentStage={stageIndex[status] ?? 0}
              onGenerate={onGenerate}
              onRetry={onGenerate}
              onRegenerate={onRegenerate || onGenerate}
              disabled={disabled}
            />
          </motion.div>
        )}

        {status === "done" && hasMedia && (
          <motion.div
            key="preview"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="w-full flex flex-col gap-2"
          >
            <div className="relative w-full rounded-3xl overflow-hidden bg-[#eaeaea] dark:bg-black">
              <AudioPlayer
                src={mediaUrl}
                type={mediaType}
                audioRef={videoRef as any}
                onPrev={onPrev}
                onNext={onNext}
                hasPrev={hasPrev}
                hasNext={hasNext}
                sessionId={sessionId}
                materialId={materialId}
                onFrameCaptured={onFrameCaptured}
              />
            </div>
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 text-xs text-emerald-500">
                <Check className="w-3.5 h-3.5" /> 总结已生成
              </div>
              {onRegenerate && (
                <button onClick={onRegenerate} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded-md hover:bg-foreground/5">
                  <RefreshCw className="w-3 h-3" /> 重新生成
                </button>
              )}
            </div>
          </motion.div>
        )}

        {!showHeroCard && status !== "done" && (
          <motion.div
            key="compact"
            layout
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.25 }}
            className="w-full"
          >
            {status === "error" ? (
              <div className="w-full rounded-xl border border-red-500/20 bg-red-500/5 flex flex-col items-center gap-2.5 py-3">
                <div className="flex items-center gap-1.5 text-xs text-red-500">
                  <AlertCircle className="w-4 h-4" /> {errorMessage || "生成失败"}
                </div>
                <button onClick={onGenerate} disabled={!generable}
                  className="px-4 py-1.5 rounded-lg bg-foreground/5 hover:bg-foreground/10 text-foreground text-sm font-medium transition-colors flex items-center gap-1.5 disabled:opacity-40">
                  <RefreshCw className="w-3.5 h-3.5" /> 重试
                </button>
              </div>
            ) : (
              <button
                onClick={onGenerate}
                disabled={!generable}
                className="group w-full rounded-xl border border-primary/20 bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 transition-colors flex items-center justify-center gap-2 py-3.5 px-4 text-base font-semibold disabled:opacity-45"
              >
                <span>{status === "done" && !hasMedia ? "重新生成" : "生成 AI 总结"}</span>
                <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

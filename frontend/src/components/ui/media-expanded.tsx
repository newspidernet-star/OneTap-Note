"use client";

import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BookmarkPlus, HelpCircle, Loader2, Plus, Trash2, Wand2, X } from "lucide-react";
import { toast } from "sonner";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useCaptureFramesBatch } from "@/lib/api";
import { cn } from "@/lib/utils";

type MediaElement = HTMLAudioElement | HTMLVideoElement;

type MediaExpandedProps = {
  src: string;
  type: "video" | "audio" | "image" | string;
  title?: string;
  isOpen: boolean;
  onClose: () => void;
  sourceMediaRef?: React.RefObject<MediaElement | null>;
  isPlaying?: boolean;
  sessionId?: string;
  materialId?: number;
  onFrameCaptured?: (data?: any) => void;
};

const formatTime = (seconds = 0) => {
  if (!Number.isFinite(seconds)) return "0:00";
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.floor(seconds % 60);
  return `${minutes}:${remaining.toString().padStart(2, "0")}`;
};

export default function MediaExpanded({
  src,
  type,
  title,
  isOpen,
  onClose,
  sourceMediaRef,
  sessionId,
  materialId,
  onFrameCaptured,
}: MediaExpandedProps) {
  const isVideo = type === "video";
  const isImage = type === "image";
  const isAudio = type === "audio";
  const canCapture = !!(isVideo && sessionId && materialId != null);
  const expandedMediaRef = useRef<MediaElement | null>(null);
  const wasPlayingRef = useRef(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [pickMode, setPickMode] = useState(false);
  const [pickedFrames, setPickedFrames] = useState<number[]>([]);
  const batchMut = useCaptureFramesBatch();

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleEsc);
      document.body.style.overflow = "hidden";
    }
    return () => {
      window.removeEventListener("keydown", handleEsc);
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const source = sourceMediaRef?.current;
    const expanded = expandedMediaRef.current;
    if (!source || !expanded) return;
    try {
      wasPlayingRef.current = !source.paused;
      source.pause();
      if (Number.isFinite(source.currentTime)) expanded.currentTime = source.currentTime;
      if (wasPlayingRef.current && expanded.paused) void expanded.play();
    } catch {}
  }, [isOpen, sourceMediaRef]);

  const syncTime = () => {
    const media = expandedMediaRef.current;
    if (!media) return;
    setCurrentTime(Number.isFinite(media.currentTime) ? media.currentTime : 0);
    setDuration(Number.isFinite(media.duration) ? media.duration : 0);
  };

  const handleClose = () => {
    const source = sourceMediaRef?.current;
    const expanded = expandedMediaRef.current;
    if (source && expanded && Number.isFinite(expanded.currentTime)) {
      try {
        expanded.pause();
        source.currentTime = expanded.currentTime;
        if (wasPlayingRef.current) void source.play();
      } catch {}
    }
    onClose();
  };

  const addCurrentFrame = () => {
    const key = Math.round(currentTime * 100) / 100;
    setPickedFrames((prev) => {
      if (prev.some((t) => Math.abs(t - key) < 0.05)) {
        toast.message("该时间点已选过", { description: formatTime(key) });
        return prev;
      }
      return [...prev, key].sort((a, b) => a - b);
    });
  };

  const removeFrame = (ts: number) => {
    setPickedFrames((prev) => prev.filter((t) => Math.abs(t - ts) > 0.001));
  };

  const processPickedFrames = () => {
    if (!canCapture || pickedFrames.length === 0) return;
    batchMut.mutate(
      { sessionId: sessionId!, materialId: materialId!, timestamps: pickedFrames },
      {
        onSuccess: (data: any) => {
          const ok = data?.blocks?.length ?? 0;
          const skip = data?.skipped?.length ?? 0;
          if (ok > 0) {
            toast.success(`已抓取 ${ok} 帧`, {
              description: skip > 0 ? `${skip} 帧失败已跳过` : "已加入时间线，并将自动纳入知识笔记",
            });
          } else {
            toast.error("抓帧失败");
          }
          setPickedFrames([]);
          onFrameCaptured?.(data);
        },
        onError: (e: any) => {
          toast.error("批量抓帧失败", { description: String(e?.message ?? e) });
        },
      }
    );
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-3 sm:p-6"
          onClick={handleClose}
        >
          <button
            onClick={handleClose}
            className="absolute right-4 top-4 z-20 rounded-full bg-black/50 p-2 text-white transition-colors hover:bg-white/20"
            aria-label="关闭"
          >
            <X className="h-6 w-6" />
          </button>

          <div className="relative max-h-full max-w-full overflow-hidden rounded-xl bg-black" onClick={(e) => e.stopPropagation()}>
            {isVideo && (
              <video
                ref={expandedMediaRef as React.RefObject<HTMLVideoElement>}
                src={src}
                playsInline
                controls={!pickMode}
                onLoadedMetadata={syncTime}
                onTimeUpdate={syncTime}
                onSeeking={syncTime}
                onSeeked={syncTime}
                className="max-h-[calc(100vh-3rem)] max-w-[calc(100vw-1.5rem)] object-contain sm:max-w-[calc(100vw-3rem)]"
              />
            )}

            {isImage && (
              <img src={src} alt={title || "media"} className="max-h-[calc(100vh-3rem)] max-w-[calc(100vw-3rem)] object-contain" />
            )}

            {isAudio && (
              <div className="flex h-[300px] w-[300px] items-center justify-center bg-gradient-to-b from-white/10 to-black/10 sm:h-[360px] sm:w-[360px]">
                <audio ref={expandedMediaRef as React.RefObject<HTMLAudioElement>} src={src} controls className="w-[calc(100%-2rem)]" />
              </div>
            )}

            {canCapture && (
              <div className="absolute inset-x-2 bottom-2 z-10 max-h-[42vh] overflow-y-auto rounded-2xl bg-black/75 p-2 text-white shadow-2xl backdrop-blur sm:inset-x-3 sm:bottom-3">
                <div className="grid grid-cols-[auto_auto_1fr] items-center gap-2 max-sm:grid-cols-[auto_1fr]">
                  <button
                    onClick={() => setPickMode((v) => !v)}
                    className={cn(
                      "inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-xs font-medium transition-colors hover:bg-white/10",
                      pickMode && "bg-amber-400/20 text-amber-200 ring-1 ring-amber-300/50"
                    )}
                  >
                    <BookmarkPlus className="h-4 w-4" />
                    {pickMode ? "选帧中" : "选帧"}
                  </button>

                  <Popover>
                    <PopoverTrigger asChild>
                      <button className="grid h-8 w-8 place-items-center rounded-full text-white/70 hover:bg-white/10 hover:text-white" aria-label="选帧说明">
                        <HelpCircle className="h-4 w-4" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent side="top" align="start" className="w-72 text-sm">
                      <ol className="list-decimal space-y-1 pl-4 text-muted-foreground">
                        <li>进入选帧模式</li>
                        <li>拖到想补充的画面</li>
                        <li>标记当前帧，可选多个</li>
                        <li>处理全部后自动加入时间线</li>
                        <li>完成后自动重新生成知识笔记</li>
                      </ol>
                    </PopoverContent>
                  </Popover>

                  <span className="min-w-[82px] justify-self-end text-xs font-mono text-white/80">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>

                  <div className="relative h-2 min-w-[120px] rounded-full bg-white/20 max-sm:col-span-2">
                    <div className="h-full rounded-full bg-white/70" style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }} />
                    {duration > 0 && pickedFrames.map((ts) => (
                      <i
                        key={ts}
                        className="absolute top-1/2 h-4 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-400"
                        style={{ left: `${Math.min(100, Math.max(0, (ts / duration) * 100))}%` }}
                      />
                    ))}
                  </div>
                </div>

                {pickMode && (
                  <div className="mt-2 flex flex-wrap items-center gap-2 border-t border-white/10 pt-2 max-sm:flex-col max-sm:items-stretch">
                    <button onClick={addCurrentFrame} className="inline-flex h-8 items-center gap-1 rounded-full bg-amber-500 px-3 text-xs font-medium text-white hover:bg-amber-600">
                      <Plus className="h-3.5 w-3.5" />
                      标记当前帧
                    </button>
                    {pickedFrames.map((ts) => (
                      <span key={ts} className="inline-flex items-center gap-1 rounded-full bg-amber-400/20 px-2 py-1 text-xs font-mono text-amber-100">
                        {formatTime(ts)}
                        <button onClick={() => removeFrame(ts)} className="grid h-4 w-4 place-items-center rounded-full hover:bg-white/10" aria-label={`移除 ${formatTime(ts)}`}>
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                    <div className="ml-auto flex items-center gap-2 max-sm:ml-0 max-sm:justify-between">
                      {pickedFrames.length > 0 && (
                        <button onClick={() => setPickedFrames([])} className="text-xs text-white/60 hover:text-white">清空</button>
                      )}
                      <button
                        onClick={processPickedFrames}
                        disabled={pickedFrames.length === 0 || batchMut.isPending}
                        className="inline-flex h-8 items-center gap-1.5 rounded-full bg-white px-3 text-xs font-medium text-black transition-colors hover:bg-white/90 disabled:opacity-50"
                      >
                        {batchMut.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5" />}
                        处理全部{pickedFrames.length ? `(${pickedFrames.length})` : ""}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

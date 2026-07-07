"use client";

import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookmarkPlus,
  HelpCircle,
  Loader2,
  Maximize2,
  Pause,
  Play,
  Plus,
  Trash2,
  Volume2,
  VolumeX,
  Wand2,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Slider } from "@/components/ui/slider";
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
  // Shared pick state with parent (AudioPlayer) so small & fullscreen stay in sync
  pickedFrames?: number[];
  setPickedFrames?: React.Dispatch<React.SetStateAction<number[]>>;
  pickMode?: boolean;
  setPickMode?: React.Dispatch<React.SetStateAction<boolean>>;
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
  pickedFrames: extPickedFrames,
  setPickedFrames: extSetPickedFrames,
  pickMode: extPickMode,
  setPickMode: extSetPickMode,
}: MediaExpandedProps) {
  const isVideo = type === "video";
  const isImage = type === "image";
  const isAudio = type === "audio";
  const canCapture = !!(isVideo && sessionId && materialId != null);
  const expandedMediaRef = useRef<MediaElement | null>(null);
  const wasPlayingRef = useRef(false);
  const trackRef = useRef<HTMLDivElement>(null);
  const tagsScrollRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [localPickedFrames, setLocalPickedFrames] = useState<number[]>([]);
  const [localPickMode, setLocalPickMode] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(100);
  const [prevVolume, setPrevVolume] = useState(100);
  const batchMut = useCaptureFramesBatch();

  // Use external state if provided (sync with parent), else local
  const pickedFrames = extPickedFrames ?? localPickedFrames;
  const setPickedFrames = extSetPickedFrames ?? setLocalPickedFrames;
  const pickMode = extPickMode ?? localPickMode;
  const setPickMode = extSetPickMode ?? setLocalPickMode;

  const isProcessing = batchMut.isPending;
  const hasDuration = duration > 0 && Number.isFinite(duration);
  const progressPercent = hasDuration ? (currentTime / duration) * 100 : 0;

  // ── ESC / body scroll lock ──────────────────────────────────────────
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

  // ── Sync from source media on open ──────────────────────────────────
  useEffect(() => {
    if (!isOpen) return;
    const source = sourceMediaRef?.current;
    const expanded = expandedMediaRef.current;
    if (!source || !expanded) return;
    try {
      wasPlayingRef.current = !source.paused;
      source.pause();
      if (Number.isFinite(source.currentTime)) expanded.currentTime = source.currentTime;
      // Sync volume
      expanded.volume = source.volume;
      setVolume(Math.round(source.volume * 100));
      if (wasPlayingRef.current && expanded.paused) void expanded.play();
    } catch {}
  }, [isOpen, sourceMediaRef]);

  // ── Auto-scroll tags to right when new frame added ──────────────────
  useEffect(() => {
    if (tagsScrollRef.current) {
      tagsScrollRef.current.scrollLeft = tagsScrollRef.current.scrollWidth;
    }
  }, [pickedFrames]);

  // ── Sync state from media events ────────────────────────────────────
  const syncTime = () => {
    const media = expandedMediaRef.current;
    if (!media) return;
    setCurrentTime(Number.isFinite(media.currentTime) ? media.currentTime : 0);
    setDuration(Number.isFinite(media.duration) ? media.duration : 0);
  };

  const syncVolume = () => {
    const media = expandedMediaRef.current;
    if (!media) return;
    setVolume(Math.round(media.volume * 100));
  };

  // ── Close handler — preserves time, volume, play state ──────────────
  const handleClose = () => {
    const source = sourceMediaRef?.current;
    const expanded = expandedMediaRef.current;
    if (source && expanded) {
      try {
        expanded.pause();
        if (Number.isFinite(expanded.currentTime)) source.currentTime = expanded.currentTime;
        source.volume = expanded.volume;
        if (wasPlayingRef.current) void source.play();
      } catch {}
    }
    onClose();
  };

  // ── Play / pause ────────────────────────────────────────────────────
  const togglePlay = () => {
    const media = expandedMediaRef.current;
    if (!media) return;
    if (media.paused) void media.play();
    else media.pause();
  };

  // ── Volume / mute ───────────────────────────────────────────────────
  const handleVolumeChange = (v: number) => {
    setVolume(v);
    if (v > 0) setPrevVolume(v);
    const media = expandedMediaRef.current;
    if (media) media.volume = v / 100;
  };

  const toggleMute = () => {
    if (volume > 0) {
      setPrevVolume(volume);
      setVolume(0);
      const media = expandedMediaRef.current;
      if (media) media.volume = 0;
    } else {
      const v = prevVolume || 100;
      setVolume(v);
      const media = expandedMediaRef.current;
      if (media) media.volume = v / 100;
    }
  };

  // ── Seek from pointer position ──────────────────────────────────────
  const seekFromClientX = (clientX: number) => {
    if (!hasDuration) return;
    const track = trackRef.current;
    if (!track) return;
    const rect = track.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    const media = expandedMediaRef.current;
    if (media) media.currentTime = ratio * duration;
  };

  const onTrackPointerDown = (e: React.PointerEvent) => {
    e.stopPropagation();
    draggingRef.current = true;
    seekFromClientX(e.clientX);
    const onMove = (ev: PointerEvent) => {
      if (draggingRef.current) seekFromClientX(ev.clientX);
    };
    const onUp = () => {
      draggingRef.current = false;
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  const seekToTimestamp = (ts: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const media = expandedMediaRef.current;
    if (!media || !hasDuration) return;
    media.currentTime = ts;
  };

  // ── Frame picking ───────────────────────────────────────────────────
  const addCurrentFrame = () => {
    if (isProcessing) return;
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
    if (isProcessing) return;
    setPickedFrames((prev) => prev.filter((t) => Math.abs(t - ts) > 0.001));
  };

  const clearFrames = () => {
    if (isProcessing) return;
    setPickedFrames([]);
  };

  const processPickedFrames = () => {
    if (!canCapture || pickedFrames.length === 0 || isProcessing) return;
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

  // ── Render ──────────────────────────────────────────────────────────
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
          {/* Close button (top-right) */}
          <button
            onClick={handleClose}
            className="absolute right-4 top-4 z-20 rounded-full bg-black/50 p-2 text-white transition-colors hover:bg-white/20"
            aria-label="关闭"
          >
            <X className="h-6 w-6" />
          </button>

          <div
            className="relative max-h-full max-w-full overflow-hidden rounded-xl bg-black"
            onClick={(e) => e.stopPropagation()}
          >
            {isVideo && (
              <video
                ref={expandedMediaRef as React.RefObject<HTMLVideoElement>}
                src={src}
                playsInline
                onLoadedMetadata={syncTime}
                onTimeUpdate={syncTime}
                onSeeking={syncTime}
                onSeeked={syncTime}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onVolumeChange={syncVolume}
                className="max-h-[calc(100vh-3rem)] max-w-[calc(100vw-1.5rem)] object-contain sm:max-w-[calc(100vw-3rem)]"
              />
            )}

            {isImage && (
              <img src={src} alt={title || "media"} className="max-h-[calc(100vh-3rem)] max-w-[calc(100vw-1.5rem)] object-contain" />
            )}

            {isAudio && (
              <div className="flex h-[300px] w-[300px] items-center justify-center bg-gradient-to-b from-white/10 to-black/10 sm:h-[360px] sm:w-[360px]">
                <audio ref={expandedMediaRef as React.RefObject<HTMLAudioElement>} src={src} controls className="w-[calc(100%-2rem)]" />
              </div>
            )}

            {/* ── Custom control bar for video ─────────────────────── */}
            {isVideo && (
              <div className="absolute inset-x-0 bottom-0 z-[110] bg-gradient-to-t from-black/95 via-black/80 to-transparent px-3 pb-3 pt-6 text-white sm:px-4">
                {/* Progress bar — full width, min 24px click height */}
                <div
                  ref={trackRef}
                  onPointerDown={onTrackPointerDown}
                  className="relative h-6 w-full cursor-pointer touch-none"
                >
                  {/* Track background */}
                  <div className="absolute top-1/2 left-0 right-0 h-1.5 -translate-y-1/2 rounded-full bg-white/20" />
                  {/* Filled progress */}
                  <div
                    className="absolute top-1/2 left-0 h-1.5 -translate-y-1/2 rounded-full bg-white/70"
                    style={{ width: `${progressPercent}%` }}
                  />
                  {/* Playhead handle */}
                  {hasDuration && (
                    <div
                      className="pointer-events-none absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-md"
                      style={{ left: `${progressPercent}%` }}
                    />
                  )}
                  {/* Yellow markers */}
                  {hasDuration &&
                    pickedFrames.map((ts) => (
                      <button
                        key={ts}
                        onClick={(e) => seekToTimestamp(ts, e)}
                        className="absolute top-1/2 z-10 h-4 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-400 transition-colors hover:bg-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-300/50"
                        style={{ left: `${Math.min(100, Math.max(0, (ts / duration) * 100))}%` }}
                        title={formatTime(ts)}
                        aria-label={`跳转到 ${formatTime(ts)}`}
                      />
                    ))}
                </div>

                {/* ── Control bar ──
                   右侧容器用 max-w 限制宽度 + overflow hidden，内部 flex 布局。
                   标签区 flex-1 min-w-0 overflow-x-auto 内部滚动，不撑大容器。
                   所以标记当前帧/处理全部位置恒定。 */}
                <div className="mt-1.5 flex h-8 items-center gap-1.5 sm:gap-2">
                  {/* Left: transport controls */}
                  <button
                    onClick={togglePlay}
                    className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-white transition-colors hover:bg-white/15"
                    aria-label={isPlaying ? "暂停" : "播放"}
                  >
                    {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </button>
                  <button
                    onClick={toggleMute}
                    className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-white transition-colors hover:bg-white/15"
                    aria-label={volume > 0 ? "静音" : "取消静音"}
                  >
                    {volume > 0 ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                  </button>
                  <Slider
                    value={[volume]}
                    onValueChange={(v) => handleVolumeChange(v[0])}
                    max={100}
                    step={1}
                    className="w-16 shrink-0 sm:w-24"
                    aria-label="音量"
                  />
                  <span className="shrink-0 text-xs font-mono text-white/80 whitespace-nowrap">
                    {formatTime(currentTime)} / {formatTime(duration)}
                  </span>

                  {/* Right cluster — flex-1 自适应宽度，标签区滚动，按钮位置稳定 */}
                  {canCapture && (
                    <div className="ml-auto flex h-8 min-w-0 max-w-full flex-1 items-center gap-1.5 overflow-hidden sm:max-w-[80%] sm:gap-2">
                      {/* 选帧 toggle */}
                      <button
                        onClick={() => setPickMode((v) => !v)}
                        className={cn(
                          "inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full px-2.5 text-xs font-medium transition-colors hover:bg-white/10",
                          pickMode && "bg-amber-400/20 text-amber-200 ring-1 ring-amber-300/50",
                          !pickMode && "text-white/80"
                        )}
                      >
                        <BookmarkPlus className="h-4 w-4" />
                        <span className="hidden sm:inline">{pickMode ? "选帧中" : "选帧"}</span>
                      </button>

                      {/* Help popover */}
                      <Popover>
                        <PopoverTrigger asChild>
                          <button
                            className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-white/70 transition-colors hover:bg-white/10 hover:text-white"
                            aria-label="选帧说明"
                          >
                            <HelpCircle className="h-4 w-4" />
                          </button>
                        </PopoverTrigger>
                        <PopoverContent
                          side="top"
                          align="end"
                          sideOffset={8}
                          className="z-[120] w-72 text-sm"
                        >
                          <p className="mb-1.5 font-semibold text-foreground">选帧再处理 · 使用说明</p>
                          <ol className="list-decimal space-y-1 pl-4 text-muted-foreground">
                            <li>点 选帧 进入选帧模式</li>
                            <li>拖动播放头到要补的关键帧位置</li>
                            <li>点 标记当前帧 加入待处理列表（可重复多次）</li>
                            <li>点 处理全部 批量抽帧 + OCR，自动加入时间线</li>
                            <li>完成后可重新生成知识笔记，让新帧参与引用</li>
                          </ol>
                          <p className="mt-2 text-xs text-muted-foreground/70">适用于自动抽帧漏掉的 PPT 页 / 关键画面</p>
                        </PopoverContent>
                      </Popover>

                      {/* pickMode 时的操作按钮 + 标签 */}
                      {pickMode && (
                        <>
                          {/* 标签区 — 在标记当前帧左边，flex-1 min-w-0 内部滚动，不撑大外层容器 */}
                          <div
                            ref={tagsScrollRef}
                            className="flex min-w-0 flex-1 flex-nowrap gap-1 overflow-x-auto scrollbar-hide"
                          >
                            {pickedFrames.map((ts) => (
                              <span
                                key={ts}
                                className="inline-flex shrink-0 items-center gap-1 rounded-full bg-amber-400/20 px-2 py-1 text-xs font-mono text-amber-100"
                              >
                                <button
                                  onClick={(e) => seekToTimestamp(ts, e)}
                                  className="hover:text-white"
                                  title={`跳转到 ${formatTime(ts)}`}
                                >
                                  {formatTime(ts)}
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    removeFrame(ts);
                                  }}
                                  disabled={isProcessing}
                                  className="grid h-4 w-4 place-items-center rounded-full hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
                                  aria-label={`移除 ${formatTime(ts)}`}
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              </span>
                            ))}
                          </div>

                          {/* 标记当前帧 — 紧跟标签区右边，位置在 ? 和清空之间 */}
                          <button
                            onClick={addCurrentFrame}
                            disabled={isProcessing}
                            className="inline-flex h-8 shrink-0 items-center gap-1 rounded-full bg-amber-500 px-3 text-xs font-medium text-white transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <Plus className="h-3.5 w-3.5" />
                            <span className="hidden sm:inline">标记当前帧</span>
                            <span className="sm:hidden">标记</span>
                          </button>

                          {pickedFrames.length > 0 && (
                            <button
                              onClick={clearFrames}
                              disabled={isProcessing}
                              className="shrink-0 text-xs text-white/60 transition-colors hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                            >
                              清空
                            </button>
                          )}
                          <button
                            onClick={processPickedFrames}
                            disabled={pickedFrames.length === 0 || isProcessing}
                            className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full bg-white px-3 text-xs font-medium text-black transition-colors hover:bg-white/90 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {isProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5" />}
                            <span className="hidden sm:inline">处理全部{pickedFrames.length ? `(${pickedFrames.length})` : ""}</span>
                            <span className="sm:hidden">处理{pickedFrames.length ? `(${pickedFrames.length})` : ""}</span>
                          </button>
                        </>
                      )}

                      {!pickMode && (
                        <button
                          onClick={handleClose}
                          className="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full px-2.5 text-xs font-medium text-white transition-colors hover:bg-white/15"
                          aria-label="退出全屏"
                        >
                          <Maximize2 className="h-3.5 w-3.5 rotate-180" />
                          <span className="hidden sm:inline">退出全屏</span>
                        </button>
                      )}
                    </div>
                  )}

                  {/* Exit fullscreen when no canCapture */}
                  {!canCapture && (
                    <button
                      onClick={handleClose}
                      className="ml-auto inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full px-2.5 text-xs font-medium text-white transition-colors hover:bg-white/15"
                      aria-label="退出全屏"
                    >
                      <Maximize2 className="h-3.5 w-3.5 rotate-180" />
                      <span className="hidden sm:inline">退出全屏</span>
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

"use client";

import React, { useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  AudioLines,
  BookmarkPlus,
  ChevronLeft,
  ChevronRight,
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
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import { useCaptureFramesBatch } from "@/lib/api";
import { cn } from "@/lib/utils";
import MediaExpanded from "@/components/ui/media-expanded";

type MediaElement = HTMLAudioElement | HTMLVideoElement;
type MediaType = "audio" | "video" | "image";

type AudioPlayerProps = {
  src: string;
  cover?: string;
  title?: string;
  type?: MediaType | string;
  audioRef?: React.RefObject<MediaElement | null>;
  className?: string;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
  sessionId?: string;
  materialId?: number;
  onFrameCaptured?: (data?: any) => void;
};

const formatTime = (seconds: number = 0) => {
  if (!Number.isFinite(seconds)) return "0:00";

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
};

const inferMediaType = (src: string, type?: MediaType | string): MediaType => {
  const normalizedType = type?.toLowerCase();

  if (
    normalizedType === "audio" ||
    normalizedType === "video" ||
    normalizedType === "image"
  ) {
    return normalizedType;
  }

  if (normalizedType?.startsWith("audio/")) return "audio";
  if (normalizedType?.startsWith("video/")) return "video";
  if (normalizedType?.startsWith("image/")) return "image";

  const cleanSrc = src.split("?")[0]?.split("#")[0]?.toLowerCase() ?? "";

  if (/\.(mp4|webm|mov|m4v|ogg)$/i.test(cleanSrc)) return "video";
  if (/\.(png|jpe?g|gif|webp|avif|svg)$/i.test(cleanSrc)) return "image";

  return "audio";
};

const CustomSlider = ({
  value,
  onChange,
  disabled,
  className,
}: {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  className?: string;
}) => {
  return (
    <motion.div
      className={cn(
        "relative w-full h-1 bg-black/20 dark:bg-white/20 rounded-full",
        disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
        className
      )}
    >
      <motion.div
        className="absolute left-0 top-0 h-full rounded-full bg-neutral-800 dark:bg-white"
        style={{ width: `${value}%` }}
        initial={{ width: 0 }}
        animate={{ width: `${value}%` }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      />
      <input
        type="range"
        min={0}
        max={100}
        step={0.1}
        value={value}
        disabled={disabled}
        aria-label="播放进度"
        onChange={(event) => onChange(Number(event.target.value))}
        className="absolute left-0 top-1/2 h-8 w-full -translate-y-1/2 cursor-pointer opacity-0 disabled:cursor-not-allowed"
      />
    </motion.div>
  );
};

const AudioPlayer = ({
  src,
  cover,
  title,
  type,
  audioRef: externalRef,
  className,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  sessionId,
  materialId,
  onFrameCaptured,
}: AudioPlayerProps) => {
  const internalRef = useRef<MediaElement | null>(null);
  const mediaRef = externalRef || internalRef;
  const mediaType = useMemo(() => inferMediaType(src, type), [src, type]);
  const isImage = mediaType === "image";
  const isVideo = mediaType === "video";
  const canCapture = !!(isVideo && sessionId && materialId != null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [orientation, setOrientation] = useState<"portrait" | "landscape" | "unknown">("unknown");
  const [volume, setVolume] = useState(100);
  const [prevVolume, setPrevVolume] = useState(100);
  const [pickMode, setPickMode] = useState(false);
  const [pickedFrames, setPickedFrames] = useState<number[]>([]);
  const batchMut = useCaptureFramesBatch();

  const getMedia = () => mediaRef.current;

  const syncTime = () => {
    const media = getMedia();
    if (!media) return;

    const nextDuration = Number.isFinite(media.duration) ? media.duration : 0;
    const nextProgress = nextDuration
      ? (media.currentTime / nextDuration) * 100
      : 0;

    setProgress(Number.isFinite(nextProgress) ? nextProgress : 0);
    setCurrentTime(Number.isFinite(media.currentTime) ? media.currentTime : 0);
    setDuration(nextDuration);
  };

  const togglePlay = () => {
    const media = getMedia();
    if (!media) return;

    if (media.paused) {
      void media.play();
    } else {
      media.pause();
    }
  };

  const handleSeek = (value: number) => {
    const media = getMedia();
    if (!media || !media.duration) return;

    const nextProgress = Math.min(Math.max(value, 0), 100);
    const nextTime = (nextProgress / 100) * media.duration;

    if (Number.isFinite(nextTime)) {
      media.currentTime = nextTime;
      setProgress(nextProgress);
      setCurrentTime(nextTime);
    }
  };

  const handleVolumeChange = (value: number) => {
    const media = getMedia();
    const v = Math.min(Math.max(value, 0), 100);
    setVolume(v);
    if (v > 0) setPrevVolume(v);
    if (media) media.volume = v / 100;
  };

  const toggleMute = () => {
    const media = getMedia();
    if (volume > 0) {
      setPrevVolume(volume);
      setVolume(0);
      if (media) media.volume = 0;
    } else {
      const v = prevVolume || 100;
      setVolume(v);
      if (media) media.volume = v / 100;
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    syncTime();
  };

  const getCurrentTime = (): number => {
    const media = getMedia();
    return media ? media.currentTime : currentTime;
  };

  const addCurrentFrame = () => {
    const ts = getCurrentTime();
    if (!Number.isFinite(ts)) {
      toast.error("无法获取当前时间点");
      return;
    }
    const key = Math.round(ts * 100) / 100;
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
              description: skip > 0 ? `${skip} 帧抽帧失败已跳过` : "已加入时间线，并将自动纳入知识笔记",
            });
          } else {
            toast.error("抓帧失败", { description: "所有帧抽帧均失败" });
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

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    if (img.naturalWidth && img.naturalHeight) {
      setOrientation(img.naturalHeight > img.naturalWidth ? "portrait" : "landscape");
    }
  };

  const handleVideoLoadedMetadata = () => {
    const video = mediaRef.current as HTMLVideoElement | null;
    if (video?.videoWidth && video?.videoHeight) {
      setOrientation(video.videoHeight > video.videoWidth ? "portrait" : "landscape");
    }
    syncTime();
    // 初始化音量
    const media = getMedia();
    if (media) media.volume = volume / 100;
  };

  const openExpanded = () => setIsExpanded(true);
  const closeExpanded = () => setIsExpanded(false);

  const handleMediaClick = () => {
    if (typeof window !== "undefined" && window.matchMedia("(pointer: coarse)").matches) {
      openExpanded();
    }
  };

  const handleMediaDoubleClick = () => {
    if (typeof window !== "undefined" && !window.matchMedia("(pointer: coarse)").matches) {
      openExpanded();
    }
  };

  if (!src) return null;

  return (
    <AnimatePresence>
      <motion.div
        className={cn(
          "relative flex w-full flex-col overflow-hidden rounded-3xl bg-[#eaeaea] dark:bg-[#11111198] p-3 shadow-[0_0_20px_rgba(0,0,0,0.2)] backdrop-blur-sm",
          "max-w-[624px]",
          className
        )}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 6 }}
        transition={{
          duration: 0.18,
          ease: "easeOut",
        }}
      >
        {mediaType === "audio" && (
          <audio
            ref={mediaRef as React.RefObject<HTMLAudioElement>}
            onLoadedMetadata={syncTime}
            onTimeUpdate={syncTime}
            onSeeking={syncTime}
            onSeeked={syncTime}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onEnded={handleEnded}
            src={src}
            preload="metadata"
            className="hidden"
          />
        )}

        <motion.div
          className="flex flex-col"
          animate={{ opacity: 1 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
        >
          <motion.div className="relative h-[300px] max-md:h-[200px] w-full overflow-hidden rounded-[16px] bg-[#eaeaea] dark:bg-white/20">
            {(onPrev || onNext) && (
              <>
                {onPrev && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onPrev(); }}
                    disabled={hasPrev === false}
                    className="absolute left-2 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full bg-white/60 hover:bg-white/80 flex items-center justify-center text-neutral-800 transition-colors disabled:opacity-30 disabled:cursor-not-allowed dark:bg-black/40 dark:hover:bg-black/60 dark:text-white"
                    aria-label="上一张"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                )}
                {onNext && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onNext(); }}
                    disabled={hasNext === false}
                    className="absolute right-2 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full bg-white/60 hover:bg-white/80 flex items-center justify-center text-neutral-800 transition-colors disabled:opacity-30 disabled:cursor-not-allowed dark:bg-black/40 dark:hover:bg-black/60 dark:text-white"
                    aria-label="下一张"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                )}
              </>
            )}
            {mediaType === "video" && (
              <video
                ref={mediaRef as React.RefObject<HTMLVideoElement>}
                src={src}
                poster={cover}
                preload="metadata"
                playsInline
                onLoadedMetadata={handleVideoLoadedMetadata}
                onTimeUpdate={syncTime}
                onSeeking={syncTime}
                onSeeked={syncTime}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onEnded={handleEnded}
                onClick={handleMediaClick}
                onDoubleClick={handleMediaDoubleClick}
                className="h-full w-full border-none object-cover"
              />
            )}

            {mediaType === "image" && (
              <img
                src={src}
                alt={title || "media"}
                onLoad={handleImageLoad}
                onClick={handleMediaClick}
                onDoubleClick={handleMediaDoubleClick}
                className="h-full w-full border-none object-cover"
              />
            )}

            {mediaType === "audio" && (
              <div className="flex h-full w-full items-center justify-center bg-gradient-to-b from-black/5 to-white/5 dark:from-white/10 dark:to-black/10">
                <div className="flex h-[72px] w-[72px] items-center justify-center rounded-full border border-black/10 bg-black/10 text-neutral-800 shadow-[0_0_24px_rgba(0,0,0,0.1)] dark:border-white/10 dark:bg-white/10 dark:text-white dark:shadow-[0_0_24px_rgba(0,0,0,0.2)]">
                  <AudioLines className="h-9 w-9" />
                </div>
              </div>
            )}
          </motion.div>

          <motion.div className="flex w-full flex-col gap-y-2">
            {title && (
              <motion.h3 className="mt-1 text-center text-base font-bold text-neutral-800 dark:text-white">
                {title}
              </motion.h3>
            )}

            {!isImage && (
              <>
                <motion.div className="flex flex-col gap-y-1 pt-1">
                  <div className="relative w-full">
                    <CustomSlider
                      value={progress}
                      onChange={handleSeek}
                      disabled={!duration}
                      className="w-full"
                    />
                    {pickMode && duration > 0 && pickedFrames.map((ts) => (
                      <div
                        key={ts}
                        className="pointer-events-none absolute top-1/2 z-10 h-3 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-amber-500"
                        style={{ left: `${Math.min(100, Math.max(0, (ts / duration) * 100))}%` }}
                        title={formatTime(ts)}
                      />
                    ))}
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-neutral-800 dark:text-white">
                      {formatTime(currentTime)}
                    </span>
                    <span className="text-sm text-neutral-800 dark:text-white">
                      {formatTime(duration)}
                    </span>
                  </div>
                </motion.div>

<motion.div className="grid w-full grid-cols-[1fr_auto_1fr] items-center gap-2 max-sm:grid-cols-1 max-sm:justify-items-center">
                   <motion.div
                     className="order-2 max-sm:order-1"
                     whileHover={{ scale: 1.1 }}
                     whileTap={{ scale: 0.9 }}
                   >
                     <Button
                       onClick={(event) => {
                         event.stopPropagation();
                         togglePlay();
                       }}
                       variant="ghost"
                       size="icon"
                       aria-label={isPlaying ? "暂停" : "播放"}
                       className="h-10 w-10 rounded-full text-neutral-800 hover:bg-black/10 hover:text-neutral-800 dark:text-white dark:hover:bg-[#111111d1] dark:hover:text-white"
                     >
                       {isPlaying ? (
                         <Pause className="h-6 w-6" />
                       ) : (
                         <Play className="h-6 w-6" />
                       )}
                     </Button>
                   </motion.div>

                    {/* 选帧模式开关 + 帮助按钮（位于控制栏左侧） */}
                    {canCapture && (
                      <div className="order-1 flex min-w-0 items-center gap-1.5 justify-self-start max-sm:order-2 max-sm:w-full max-sm:justify-center">
                        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                          <Button
                            onClick={(event) => {
                              event.stopPropagation();
                              setPickMode((v) => !v);
                            }}
                            variant="ghost"
                            aria-label={pickMode ? "退出选帧模式" : "进入选帧模式"}
                            className={cn(
                              "h-8 gap-1.5 rounded-full px-3 text-xs font-medium text-neutral-800 hover:bg-black/10 hover:text-neutral-800 dark:text-white dark:hover:bg-[#111111d1] dark:hover:text-white",
                              pickMode && "bg-amber-400/20 text-amber-600 dark:text-amber-400 ring-1 ring-amber-400/50"
                            )}
                          >
                            <BookmarkPlus className="h-4 w-4" />
                            {pickMode ? "选帧中" : "选帧"}
                          </Button>
                        </motion.div>
                        <Popover>
                          <PopoverTrigger asChild>
                            <button
                              onClick={(e) => e.stopPropagation()}
                              aria-label="使用说明"
                              className="grid h-7 w-7 place-items-center rounded-full text-neutral-500 hover:bg-black/10 hover:text-neutral-700 dark:text-white/60 dark:hover:bg-white/10 dark:hover:text-white"
                            >
                              <HelpCircle className="h-4 w-4" />
                            </button>
                          </PopoverTrigger>
                          <PopoverContent side="top" align="start" className="w-72 text-sm">
                            <div className="space-y-2">
                              <p className="font-semibold">选帧再处理 · 使用说明</p>
                              <ol className="list-decimal space-y-1 pl-4 text-muted-foreground">
                                <li>点 <span className="font-medium text-foreground">选帧</span> 进入选帧模式</li>
                                <li>拖动播放头到要补的关键帧位置</li>
                                <li>点 <span className="font-medium text-foreground">标记当前帧</span> 加入待处理列表（可重复多次）</li>
                                <li>点 <span className="font-medium text-foreground">处理全部</span> 批量抽帧 + OCR，自动加入时间线</li>
                                <li>完成后可重新生成知识笔记，让新帧参与引用</li>
                              </ol>
                              <p className="text-xs text-muted-foreground/70">适用于自动抽帧漏掉的 PPT 页 / 关键画面。</p>
                            </div>
                          </PopoverContent>
                        </Popover>
                      </div>
                    )}

                    {/* 音量控制 + 全屏按钮（音量调节位于全屏按钮左侧） */}
                    <div className="order-3 ml-auto flex min-w-0 items-center gap-2 justify-self-end max-sm:ml-0 max-sm:w-full max-sm:justify-center">
                      <motion.div
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                      >
                        <Button
                          onClick={(event) => {
                            event.stopPropagation();
                            toggleMute();
                          }}
                          variant="ghost"
                          size="icon"
                          aria-label={volume > 0 ? "静音" : "取消静音"}
                          className="h-8 w-8 rounded-full text-neutral-800 hover:bg-black/10 hover:text-neutral-800 dark:text-white dark:hover:bg-[#111111d1] dark:hover:text-white"
                        >
                          {volume > 0 ? (
                            <Volume2 className="h-4 w-4" />
                          ) : (
                            <VolumeX className="h-4 w-4" />
                          )}
                        </Button>
                      </motion.div>

                      <Slider
                        value={[volume]}
                        onValueChange={(value) => handleVolumeChange(value[0])}
                        max={100}
                        step={1}
                        showTooltip
                        tooltipContent={(value) => `${value}`}
                        aria-label="音量"
                        className="w-24 max-sm:w-28"
                      />

                      <motion.div
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                      >
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label="全屏查看"
                          onClick={(event) => {
                            event.stopPropagation();
                            openExpanded();
                          }}
                          className="h-8 w-8 rounded-full text-neutral-800 hover:bg-black/10 hover:text-neutral-800 dark:text-white dark:hover:bg-[#111111d1] dark:hover:text-white"
                        >
                          <Maximize2 className="h-4 w-4" />
                        </Button>
                      </motion.div>
                    </div>
                </motion.div>

                {/* 选帧面板：进入选帧模式后展开 */}
                <AnimatePresence>
                  {pickMode && canCapture && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-2 rounded-2xl border border-amber-400/30 bg-amber-400/5 p-3 dark:bg-amber-400/5">
                        <div className="mb-2 flex items-center justify-between gap-2 max-sm:flex-col max-sm:items-stretch">
                          <div className="flex items-center gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400">
                            <BookmarkPlus className="h-3.5 w-3.5" />
                            选帧模式
                            <span className="text-muted-foreground">· 已选 {pickedFrames.length} 帧</span>
                          </div>
                          <button
                            onClick={(e) => { e.stopPropagation(); addCurrentFrame(); }}
                            className="inline-flex h-8 items-center justify-center gap-1 rounded-full bg-amber-500 px-3 text-xs font-medium text-white hover:bg-amber-600 transition-colors"
                          >
                            <Plus className="h-3.5 w-3.5" />
                            标记当前帧 {formatTime(getCurrentTime())}
                          </button>
                        </div>

                        <div className="flex h-7 min-w-0 flex-nowrap items-center gap-1.5 overflow-x-auto overflow-y-hidden scrollbar-hide">
                          {pickedFrames.length === 0 ? (
                            <p className="shrink-0 text-xs text-muted-foreground">
                              拖动播放头到要补帧的位置，点「标记当前帧」加入列表。
                            </p>
                          ) : (
                            pickedFrames.map((ts) => (
                              <span
                                key={ts}
                                className="inline-flex h-7 shrink-0 items-center gap-1 rounded-full bg-amber-400/15 px-2 text-xs font-mono text-amber-700 dark:text-amber-300"
                              >
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (duration > 0) handleSeek((ts / duration) * 100);
                                  }}
                                  title={`跳转到 ${formatTime(ts)}`}
                                >
                                  {formatTime(ts)}
                                </button>
                                <button
                                  onClick={(e) => { e.stopPropagation(); removeFrame(ts); }}
                                  className="grid h-4 w-4 place-items-center rounded-full hover:bg-amber-400/30"
                                  aria-label={`移除 ${formatTime(ts)}`}
                                >
                                  <Trash2 className="h-3 w-3" />
                                </button>
                              </span>
                            ))
                          )}
                        </div>

                        <div className="mt-2 flex h-8 items-center justify-end gap-2 max-sm:justify-between">
                          <button
                              onClick={(e) => { e.stopPropagation(); setPickedFrames([]); }}
                              disabled={pickedFrames.length === 0 || batchMut.isPending}
                              className="text-xs text-muted-foreground hover:text-foreground transition-colors disabled:cursor-not-allowed disabled:opacity-30"
                            >
                              清空
                          </button>
                          <button
                              onClick={(e) => { e.stopPropagation(); processPickedFrames(); }}
                              disabled={pickedFrames.length === 0 || batchMut.isPending}
                              className="inline-flex h-8 items-center gap-1.5 rounded-full bg-primary px-3 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                            >
                              {batchMut.isPending ? (
                                <><Loader2 className="h-3.5 w-3.5 animate-spin" /> 处理中…</>
                              ) : (
                                <><Wand2 className="h-3.5 w-3.5" /> 处理全部（{pickedFrames.length}）</>
                              )}
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </>
            )}
          </motion.div>
        </motion.div>
      </motion.div>

      <MediaExpanded
        src={src}
        type={mediaType}
        title={title}
        isOpen={isExpanded}
        onClose={closeExpanded}
        sourceMediaRef={mediaRef}
        isPlaying={isPlaying}
        sessionId={sessionId}
        materialId={materialId}
        onFrameCaptured={onFrameCaptured}
        pickedFrames={pickedFrames}
        setPickedFrames={setPickedFrames}
        pickMode={pickMode}
        setPickMode={setPickMode}
      />
    </AnimatePresence>
  );
};

export default AudioPlayer;

"use client";

import React, { useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { AudioLines, ChevronLeft, ChevronRight, Maximize2, Pause, Play } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
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
}: AudioPlayerProps) => {
  const internalRef = useRef<MediaElement | null>(null);
  const mediaRef = externalRef || internalRef;
  const mediaType = useMemo(() => inferMediaType(src, type), [src, type]);
  const isImage = mediaType === "image";
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isExpanded, setIsExpanded] = useState(false);
  const [orientation, setOrientation] = useState<"portrait" | "landscape" | "unknown">("unknown");

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

  const handleEnded = () => {
    setIsPlaying(false);
    syncTime();
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
          orientation === "portrait" ? "max-w-[520px]" : "max-w-[624px]",
          className
        )}
        initial={{ opacity: 0, filter: "blur(10px)" }}
        animate={{ opacity: 1, filter: "blur(0px)" }}
        exit={{ opacity: 0, filter: "blur(10px)" }}
        transition={{
          duration: 0.3,
          ease: "easeInOut",
          delay: 0.1,
          type: "spring",
        }}
        layout
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
          layout
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
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
                  <CustomSlider
                    value={progress}
                    onChange={handleSeek}
                    disabled={!duration}
                    className="w-full"
                  />
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-neutral-800 dark:text-white">
                      {formatTime(currentTime)}
                    </span>
                    <span className="text-sm text-neutral-800 dark:text-white">
                      {formatTime(duration)}
                    </span>
                  </div>
                </motion.div>

                <motion.div className="relative flex w-full items-center justify-center">
                  <motion.div
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

                  <motion.div
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    className="absolute right-0"
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
                </motion.div>
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
      />
    </AnimatePresence>
  );
};

export default AudioPlayer;

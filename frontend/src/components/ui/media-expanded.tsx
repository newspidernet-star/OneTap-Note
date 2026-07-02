"use client";

import React, { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

type MediaElement = HTMLAudioElement | HTMLVideoElement;

type MediaExpandedProps = {
  src: string;
  type: "video" | "audio" | "image" | string;
  title?: string;
  isOpen: boolean;
  onClose: () => void;
  sourceMediaRef?: React.RefObject<MediaElement | null>;
  isPlaying?: boolean;
};

export default function MediaExpanded({
  src,
  type,
  title,
  isOpen,
  onClose,
  sourceMediaRef,
  isPlaying = false,
}: MediaExpandedProps) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleEsc);
      document.body.style.overflow = "hidden";
    }
    return () => {
      window.removeEventListener("keydown", handleEsc);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  const isVideo = type === "video";
  const isImage = type === "image";
  const isAudio = type === "audio";
  const expandedMediaRef = useRef<MediaElement | null>(null);
  const wasPlayingRef = useRef(false);

  // 展开时：暂停原播放器，把进度和播放状态同步给放大播放器
  useEffect(() => {
    if (!isOpen) return;
    const source = sourceMediaRef?.current;
    const expanded = expandedMediaRef.current;
    if (!source || !expanded) return;

    try {
      wasPlayingRef.current = !source.paused;
      source.pause();
      if (Number.isFinite(source.currentTime)) {
        expanded.currentTime = source.currentTime;
      }
      if (wasPlayingRef.current && expanded.paused) {
        void expanded.play();
      }
    } catch {
      // ignore media sync errors
    }
  }, [isOpen, sourceMediaRef]);

  const handleClose = () => {
    const source = sourceMediaRef?.current;
    const expanded = expandedMediaRef.current;
    if (source && expanded && Number.isFinite(expanded.currentTime)) {
      try {
        expanded.pause();
        source.currentTime = expanded.currentTime;
        if (wasPlayingRef.current) {
          void source.play();
        }
      } catch {
        // ignore media sync errors
      }
    }
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-4 sm:p-6"
          onClick={handleClose}
        >
          <button
            onClick={handleClose}
            className="absolute top-4 right-4 z-10 p-2 rounded-full bg-black/50 text-white hover:bg-white/20 transition-colors"
            aria-label="关闭"
          >
            <X className="w-6 h-6" />
          </button>

          <div
            className="relative max-h-full max-w-full rounded-xl overflow-hidden bg-black"
            onClick={(e) => e.stopPropagation()}
          >
            {isVideo && (
              <video
                ref={expandedMediaRef as React.RefObject<HTMLVideoElement>}
                src={src}
                controls
                playsInline
                className="max-h-[calc(100vh-3rem)] max-w-[calc(100vw-3rem)] object-contain"
              />
            )}

            {isImage && (
              <img
                src={src}
                alt={title || "media"}
                className="max-h-[calc(100vh-3rem)] max-w-[calc(100vw-3rem)] object-contain"
              />
            )}

            {isAudio && (
              <div className="flex h-[300px] w-[300px] sm:h-[360px] sm:w-[360px] items-center justify-center bg-gradient-to-b from-white/10 to-black/10">
                <audio
                  ref={expandedMediaRef as React.RefObject<HTMLAudioElement>}
                  src={src}
                  controls
                  className="w-[calc(100%-2rem)]"
                />
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

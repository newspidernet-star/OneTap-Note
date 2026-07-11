import React, { memo, useMemo } from "react";
import { motion } from "framer-motion";
import { Copy, Film, Hand, ImageIcon, Mic2, Play } from "lucide-react";

interface EvidenceBlock {
  id: string;
  type: string;
  timestamp: any;
  speaker?: string;
  text: string;
  is_manual?: boolean;
}

interface TimelinePanelProps {
  blocks: EvidenceBlock[];
  highlightedBlock: string | null;
  onBlockClick: (id: string) => void;
  onTimestampClick: (block: EvidenceBlock) => void;
  currentPreviewType?: string;
  videoRef?: React.RefObject<HTMLVideoElement>;
  className?: string;
  onCopyTimestamps?: () => void;
  canCopyTimestamps?: boolean;
  copyingTimestamps?: boolean;
}

const MATERIAL_TYPES = new Set(["video_frame", "image", "document", "screen"]);
const LARGE_LIST_THRESHOLD = 120;

function fmtTimestamp(t: any): string {
  if (t == null || t === "") return "00:00";
  const n = typeof t === "number" ? t : parseFloat(t);
  if (Number.isNaN(n)) return String(t);
  const m = Math.floor(n / 60);
  const s = Math.floor(n % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function TimelinePanel({
  blocks,
  highlightedBlock,
  onBlockClick,
  onTimestampClick,
  className = "",
  onCopyTimestamps,
  canCopyTimestamps = false,
  copyingTimestamps = false,
}: TimelinePanelProps) {
  const isSpeech = (block: EvidenceBlock) => block.type === "speech";
  const isSource = (block: EvidenceBlock) => MATERIAL_TYPES.has(block.type);
  const largeList = blocks.length > LARGE_LIST_THRESHOLD;

  const speakerOrder = useMemo(
    () => Array.from(new Set(blocks.filter(isSpeech).map((b) => b.speaker || "未知"))),
    [blocks]
  );
  const speakerMap = useMemo(
    () => new Map(speakerOrder.map((name, i) => [name, `说话人${i + 1}`])),
    [speakerOrder]
  );
  const speakers = useMemo(() => Array.from(speakerMap.values()), [speakerMap]);
  const hasSource = useMemo(() => blocks.some(isSource), [blocks]);

  const displaySpeaker = (block: EvidenceBlock) =>
    isSpeech(block) ? speakerMap.get(block.speaker || "未知") || "说话人" : "";

  const nodeLabel = (block: EvidenceBlock) => {
    if (block.type === "video_frame") return "V";
    if (block.type === "image" || block.type === "screen") return "P";
    if (block.type === "document") return "D";
    const label = displaySpeaker(block);
    const num = label.replace(/\D/g, "");
    return num || "记";
  };

  const renderBlock = (block: EvidenceBlock, i: number) => {
    const speech = isSpeech(block);
    const isHighlighted = highlightedBlock === block.id;
    const rowClassName = "relative grid grid-cols-[32px_1fr] gap-3 mb-4 last:mb-0";
    const rowStyle = largeList
      ? ({ contentVisibility: "auto", containIntrinsicSize: "112px" } as React.CSSProperties)
      : undefined;

    const rowContent = (
      <>
        <div
          className={`relative z-10 w-[32px] h-[32px] rounded-[11px] grid place-items-center mt-0.5 text-xs font-extrabold shadow-sm ${
            speech ? "bg-primary text-primary-foreground" : "bg-cyan-600 text-white dark:bg-cyan-500 dark:text-slate-950"
          }`}
        >
          {nodeLabel(block)}
        </div>

        <div
          onClick={() => onBlockClick(block.id)}
          className={`relative border rounded-2xl bg-card overflow-hidden cursor-pointer transition-colors ${
            isHighlighted
              ? "border-primary/50 shadow-[0_0_20px_hsl(var(--primary)/0.18)] ring-1 ring-primary/25"
              : "border-border shadow-[0_8px_18px_rgba(22,28,45,0.04)]"
          }`}
        >
          <div className={`absolute inset-y-0 left-0 w-1 ${speech ? "bg-primary" : "bg-cyan-600 dark:bg-cyan-500"}`} />

          <div className="min-h-9 pl-4 pr-3.5 pt-2.5 flex flex-wrap items-center justify-between gap-y-2 gap-x-3">
            <div className="min-w-0 flex items-center gap-1.5 text-[13px] font-bold text-foreground">
              <span
                className={`h-[22px] px-1.5 inline-flex items-center gap-1 rounded-md text-[10px] font-extrabold font-mono whitespace-nowrap ${
                  speech
                    ? "text-primary bg-primary/10"
                    : "bg-cyan-50 text-cyan-800 dark:bg-cyan-400/12 dark:text-cyan-200"
                }`}
              >
                {speech ? <Mic2 className="w-3 h-3" /> : <ImageIcon className="w-3 h-3" />}
                {block.id}
              </span>
              {block.is_manual && (
                <span className="h-[22px] px-1.5 inline-flex items-center gap-1 rounded-md bg-amber-400/15 text-[10px] font-bold text-amber-600 dark:text-amber-300">
                  <Hand className="w-3 h-3" />
                  手动
                </span>
              )}
              <span className="truncate">
                {speech
                  ? displaySpeaker(block)
                  : block.type === "video_frame"
                    ? block.is_manual ? "手动选帧" : "视频帧"
                    : block.type === "image" || block.type === "screen"
                      ? "课件截图"
                      : "文档页面"}
              </span>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onTimestampClick(block);
                }}
                className="w-7 h-7 rounded-full grid place-items-center bg-muted text-muted-foreground hover:bg-muted/80 transition-colors"
                aria-label={`播放 ${fmtTimestamp(block.timestamp)}`}
              >
                <Play className="w-3 h-3 fill-current translate-x-px" />
              </button>
              <time className="text-[11px] font-bold text-muted-foreground font-mono">
                {fmtTimestamp(block.timestamp)}
              </time>
            </div>
          </div>

          <p className={`mt-1 mx-0 mb-0 pl-4 pr-4 pb-4 text-sm leading-6 font-semibold ${isHighlighted ? "text-foreground" : "text-foreground/80"}`}>
            {block.text}
          </p>
        </div>
      </>
    );

    if (largeList) {
      return (
        <div id={`ev-${block.id}`} key={block.id} className={rowClassName} style={rowStyle}>
          {rowContent}
        </div>
      );
    }

    return (
      <motion.div
        id={`ev-${block.id}`}
        key={block.id}
        initial={{ opacity: 0, y: 8 }}
        animate={isHighlighted ? { opacity: 1, y: 0, scale: 1.02 } : { opacity: 1, y: 0 }}
        transition={{ delay: Math.min(i * 0.015, 0.12), duration: 0.18 }}
        className={rowClassName}
      >
        {rowContent}
      </motion.div>
    );
  };

  return (
    <div className={`flex-1 min-h-0 flex flex-col overflow-hidden bg-card ${className}`}>
      <div className="min-h-[56px] px-4 py-3 sm:px-5 grid grid-cols-[1fr_auto] gap-x-3 gap-y-1.5 border-b border-border/40 shrink-0">
        <div className="flex items-center gap-2 text-sm font-semibold tracking-normal min-w-0">
          <Film className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          <span className="truncate">时间线</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-medium text-muted-foreground whitespace-nowrap">{blocks.length} 段</span>
          <button
            type="button"
            disabled={!canCopyTimestamps || copyingTimestamps}
            onClick={onCopyTimestamps}
            className="inline-flex h-7 items-center gap-1.5 rounded-md px-2 text-[11px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="复制时间戳"
            title="复制时间戳"
          >
            <Copy className="h-3.5 w-3.5" />
            <span className="max-sm:hidden">复制时间戳</span>
          </button>
        </div>

        <div className="col-span-full flex items-center gap-2 overflow-x-auto scrollbar-hide">
          <span className="h-6 px-2.5 inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/50 text-foreground text-[11px] font-medium whitespace-nowrap">
            全部
          </span>
          {speakers.map((speaker) => (
            <span
              key={speaker}
              className="h-6 px-2.5 inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card text-muted-foreground text-[11px] font-medium whitespace-nowrap"
            >
              <i className="w-1.5 h-1.5 rounded-full bg-primary" />
              {speaker}
            </span>
          ))}
          {hasSource && (
            <span className="h-6 px-2.5 inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card text-muted-foreground text-[11px] font-medium whitespace-nowrap">
              <i className="w-1.5 h-1.5 rounded-full bg-cyan-600 dark:bg-cyan-400" />
              资料
            </span>
          )}
        </div>
      </div>

      <div className="relative flex-1 min-h-0 overflow-y-auto px-4 pt-5 pb-6 sm:px-5 bg-card" style={{ maxHeight: "calc(100dvh - 112px)" }}>
        <div className="relative">
          <div className="absolute left-[31px] sm:left-[35px] top-7 bottom-8 w-0.5 rounded-full bg-gradient-to-b from-primary/20 via-cyan-500/25 to-primary/20 dark:via-cyan-400/25" />

          {blocks.map(renderBlock)}

          {blocks.length === 0 && (
            <div className="text-center text-xs text-muted-foreground/50 py-8">暂无证据块，上传媒体后自动处理生成</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default memo(TimelinePanel);

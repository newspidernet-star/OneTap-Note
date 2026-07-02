import React from "react";

interface HeroCardProps {
  title?: string;
  subtitle?: string;
  buttonText?: string;
  disabled?: boolean;
  onClick?: () => void;
}

export function HeroCard({
  title = "AI 总结",
  subtitle = "上传媒体或粘贴链接后生成智能总结",
  buttonText = "生成 AI 总结 →",
  disabled = false,
  onClick,
}: HeroCardProps) {
  return (
    <div className="w-[640px] max-w-full rounded-3xl bg-muted p-10 flex flex-col items-center text-center gap-5 shadow-sm">
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold tracking-tight text-foreground">
          {title}
        </h2>
        <p className="text-base text-muted-foreground">
          {subtitle}
        </p>
      </div>

      <button
        onClick={onClick}
        disabled={disabled}
        className="group inline-flex items-center gap-2 rounded-xl border border-border/50 bg-secondary px-8 py-4 text-lg font-medium text-secondary-foreground transition-all hover:bg-secondary/80 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 dark:bg-primary dark:text-primary-foreground dark:hover:bg-primary/90"
      >
        <span>{buttonText.replace(/→/g, "").trim()}</span>
        <span className="transition-transform duration-300 group-hover:translate-x-1">
          →
        </span>
      </button>
    </div>
  );
}

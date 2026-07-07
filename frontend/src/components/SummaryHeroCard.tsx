import { ArrowRight, RefreshCw, Sparkles } from "lucide-react";
import { DynamicIsland, DynamicIslandView } from "@/components/ui/be-ui-dynamic-island";
import { cn } from "@/lib/utils";
import { useIsMobile } from "@/hooks/use-mobile";

type SummaryCTAState = "idle" | "loading" | "error" | "generated";

const stages = ["上传", "OCR", "转写", "匹配证据块", "生成知识笔记"];

interface SummaryHeroCardProps {
  state?: SummaryCTAState;
  currentStage?: number;
  onGenerate?: () => void;
  onRetry?: () => void;
  onRegenerate?: () => void;
  disabled?: boolean;
  className?: string;
}

export function SummaryHeroCard({
  state = "idle",
  currentStage = 0,
  onGenerate,
  onRetry,
  onRegenerate,
  disabled = false,
  className,
}: SummaryHeroCardProps) {
  const isMobile = useIsMobile();
  const isLoading = state === "loading";
  const isError = state === "error";
  const isGenerated = state === "generated";

  const buttonLabel = isError
    ? "重试生成"
    : isGenerated
      ? "重新生成笔记"
      : "生成知识笔记";

  const handleClick = isError ? onRetry : isGenerated ? onRegenerate : onGenerate;

  return (
    <section
      className={cn(
        "mx-auto flex min-h-[420px] w-full items-start justify-center px-4 pt-16 sm:pt-20",
        className,
      )}
    >
      <div className="w-full max-w-[640px] px-6 py-10 text-center sm:px-12 sm:py-12">
        <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-muted text-foreground">
          <Sparkles className="h-5 w-5" />
        </div>

        <h2 className="text-3xl font-semibold tracking-normal text-card-foreground sm:text-4xl">
          知识笔记
        </h2>

        <p className="mx-auto mt-3 max-w-md text-base leading-7 text-muted-foreground sm:text-lg">
          上传媒体或粘贴链接后，生成不看原视频也能直接使用的知识笔记
        </p>

        <div className="mt-8 flex justify-center">
          <DynamicIsland
            view={isLoading && !isMobile ? "loading" : null}
            compact={
              <button
                onClick={handleClick}
                disabled={disabled}
                className={cn(
                  "group inline-flex h-full w-full items-center justify-center gap-2 font-semibold",
                  disabled && "opacity-50 cursor-not-allowed"
                )}
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>{stages[currentStage] ?? "处理中"}</span>
                  </>
                ) : (
                  <>
                    <span>{buttonLabel}</span>
                    {!isError && (
                      <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1" />
                    )}
                    {isError && <RefreshCw className="h-4 w-4" />}
                  </>
                )}
              </button>
            }
            compactClassName="h-[52px] min-w-[180px] px-7 py-0 text-base leading-none"
            shellClassName="bg-[#eaeaea] text-neutral-800 shadow-none dark:bg-primary dark:text-primary-foreground"
          >
            <DynamicIslandView id="loading" className="hidden sm:flex w-[280px] flex-col gap-4 sm:w-[360px]">
              <div className="flex items-center justify-center gap-2 text-sm font-medium">
                <RefreshCw className="h-4 w-4 animate-spin" />
                <span>{stages[currentStage] ?? "处理中"}</span>
              </div>

              <div className="grid grid-cols-5 gap-2">
                {stages.map((stage, index) => {
                  const active = index <= currentStage;

                  return (
                    <div key={stage} className="space-y-2">
                      <div
                        className={cn(
                          "h-1.5 rounded-full bg-neutral-300 dark:bg-primary-foreground/20",
                          active && "bg-neutral-600 dark:bg-primary-foreground",
                        )}
                      />
                      <div
                        className={cn(
                          "text-[10px] text-neutral-500 dark:text-primary-foreground/60",
                          active && "font-medium text-neutral-800 dark:text-primary-foreground",
                        )}
                      >
                        {stage}
                      </div>
                    </div>
                  );
                })}
              </div>
            </DynamicIslandView>
          </DynamicIsland>
        </div>

        {isError && (
          <p className="mt-5 text-sm text-muted-foreground">
            生成时遇到问题，请检查媒体或链接后重试。
          </p>
        )}
      </div>
    </section>
  );
}

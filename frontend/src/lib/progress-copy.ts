import type { ProcessingProgress } from "@/lib/api";

const stageMessages: Record<string, string[]> = {
  upload: ["正在把这份素材接进来…", "马上就能开始处理了…"],
  download: ["正在把链接里的内容带回来…", "视频有点大，再等我一下…"],
  prepare: ["正在看看这份素材该怎么处理…", "正在把音频准备好…"],
  transcribe: [
    "正在认真听视频里的内容…",
    "正在把口语整理成可读文字…",
    "正在分辨人物、事件和关键转折…",
    "长视频要多听一会儿，我还在认真记…",
  ],
  match: ["正在把前后内容串起来…", "正在找出真正重要的线索…"],
  generate: [
    "正在找出真正值得留下的内容…",
    "正在把零散信息整理成一篇笔记…",
    "正在避免把笔记写成视频简介…",
  ],
  review: [
    "正在看看有没有漏掉重要内容…",
    "正在核对数字、清单和关键细节…",
    "快好了，正在做最后一遍检查…",
  ],
  finalize: ["正在为你的笔记起一个不水的标题…", "马上就好…"],
};

export function getFriendlyProgressMessage(progress: ProcessingProgress) {
  const messages = stageMessages[progress.stage];
  if (!messages?.length) return progress.detail;
  const index = Math.floor(progress.stage_elapsed_seconds / 5) % messages.length;
  return messages[index];
}

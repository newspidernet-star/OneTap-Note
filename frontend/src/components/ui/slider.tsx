"use client"

import * as React from "react"
import * as SliderPrimitive from "@radix-ui/react-slider"

import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

type SliderProps = React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root> & {
  showTooltip?: boolean
  tooltipContent?: (value: number) => React.ReactNode
}

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  SliderProps
>(({ className, showTooltip = false, tooltipContent, value, defaultValue, ...props }, ref) => {
  const currentValue = Array.isArray(value)
    ? value[0]
    : Array.isArray(defaultValue)
      ? defaultValue[0]
      : 0
  const thumb = (
    <SliderPrimitive.Thumb className="block h-4 w-4 rounded-full border border-primary/50 bg-background shadow transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50" />
  )

  return (
    <SliderPrimitive.Root
      ref={ref}
      value={value}
      defaultValue={defaultValue}
      className={cn("relative flex w-full touch-none select-none items-center", className)}
      {...props}
    >
      <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden rounded-full bg-primary/20">
        <SliderPrimitive.Range className="absolute h-full bg-primary" />
      </SliderPrimitive.Track>
      {showTooltip ? (
        <TooltipProvider delayDuration={0}>
          <Tooltip open>
            <TooltipTrigger asChild>{thumb}</TooltipTrigger>
            <TooltipContent side="top" showArrow>
              {tooltipContent ? tooltipContent(Number(currentValue ?? 0)) : currentValue}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      ) : (
        thumb
      )}
    </SliderPrimitive.Root>
  )
})
Slider.displayName = SliderPrimitive.Root.displayName

export { Slider }

import { Button } from "@/components/ui/button";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface GetStartedButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: "default" | "sm" | "lg" | "icon";
}

export function GetStartedButton({
  children = "Get Started",
  className,
  size = "lg",
  disabled,
  ...props
}: GetStartedButtonProps) {
  return (
    <Button
      className={cn(
        "group relative overflow-hidden w-full",
        className
      )}
      size={size}
      disabled={disabled}
      {...props}
    >
      <span className="mr-8 transition-opacity duration-500 group-hover:opacity-0">
        {children}
      </span>
      <i className="absolute right-1 top-1 bottom-1 rounded-sm z-10 grid w-1/4 place-items-center transition-all duration-500 bg-primary-foreground/15 group-hover:w-[calc(100%-0.5rem)] group-active:scale-95 text-primary">
        <ChevronRight size={16} strokeWidth={2} aria-hidden="true" />
      </i>
    </Button>
  );
}

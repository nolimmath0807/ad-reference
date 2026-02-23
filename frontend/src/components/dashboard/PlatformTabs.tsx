import { cn } from "@/lib/utils";
import type { PlatformType } from "@/types/ad";

interface PlatformTabsProps {
  activePlatform: "all" | PlatformType;
  onPlatformChange: (platform: "all" | PlatformType) => void;
}

const platforms: { value: "all" | PlatformType; label: string }[] = [
  { value: "all", label: "All" },
  { value: "meta", label: "Meta" },
  { value: "google", label: "Google" },
  { value: "tiktok", label: "TikTok" },
  { value: "instagram", label: "Instagram" },
];

export function PlatformTabs({ activePlatform, onPlatformChange }: PlatformTabsProps) {
  return (
    <div className="flex items-center gap-1 border-b">
      {platforms.map((platform) => {
        const isActive = activePlatform === platform.value;
        return (
          <button
            key={platform.value}
            onClick={() => onPlatformChange(platform.value)}
            className={cn(
              "relative px-4 py-2.5 text-sm font-medium transition-colors",
              isActive
                ? "text-brand-primary"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {platform.label}
            {isActive && (
              <span className="absolute inset-x-0 bottom-0 h-0.5 bg-brand-primary rounded-full" />
            )}
          </button>
        );
      })}
    </div>
  );
}

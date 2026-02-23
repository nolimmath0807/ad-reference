import { Heart, MessageCircle, Share2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface AdMetricsProps {
  likes: number | null;
  comments: number | null;
  shares: number | null;
  className?: string;
}

function formatCount(count: number | null): string {
  if (count === null || count === undefined) return "-";
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  return count.toLocaleString();
}

export function AdMetrics({ likes, comments, shares, className }: AdMetricsProps) {
  const metrics = [
    { icon: Heart, label: "Likes", value: likes },
    { icon: MessageCircle, label: "Comments", value: comments },
    { icon: Share2, label: "Shares", value: shares },
  ];

  return (
    <div className={cn("grid grid-cols-3 gap-3", className)}>
      {metrics.map(({ icon: Icon, label, value }) => (
        <div
          key={label}
          className="flex flex-col items-center gap-1 rounded-lg bg-muted/60 px-3 py-2.5"
        >
          <Icon className="size-4 text-muted-foreground" />
          <span className="text-sm font-semibold tabular-nums">
            {formatCount(value)}
          </span>
          <span className="text-[11px] text-muted-foreground">{label}</span>
        </div>
      ))}
    </div>
  );
}

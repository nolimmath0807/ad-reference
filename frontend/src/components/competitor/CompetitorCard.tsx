import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Trash2, Activity, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { MiniDonutChart } from "@/components/competitor/charts/MiniDonutChart";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { CompetitorStats } from "@/types/competitor";

interface CompetitorCardProps {
  stats: CompetitorStats;
  onDeleted: () => void;
}

const PLATFORM_COLORS: Record<string, string> = {
  google: "bg-blue-500/10 text-blue-600",
  meta: "bg-indigo-500/10 text-indigo-600",
  tiktok: "bg-neutral-900/10 text-neutral-800",
  instagram: "bg-pink-500/10 text-pink-600",
  all: "bg-neutral-500/10 text-neutral-600",
};

const FORMAT_COLORS: Record<string, string> = {
  image: "#8b5cf6",
  video: "#06b6d4",
  text: "#f59e0b",
};

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const date = new Date(dateStr).getTime();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
  return String(count);
}

export function CompetitorCard({ stats, onDeleted }: CompetitorCardProps) {
  const navigate = useNavigate();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const { domain_info, total_ads, last_collected_at } = stats;

  const handleDelete = async () => {
    setIsDeleting(true);
    await api.delete(`/monitored-domains/${domain_info.id}`);
    toast.success(`"${domain_info.domain}" has been removed.`);
    setIsDeleting(false);
    setShowDeleteDialog(false);
    onDeleted();
  };

  const handleCardClick = () => {
    navigate(`/competitors/${domain_info.id}`);
  };

  const formatEntries = Object.entries(stats.ads_by_format);

  const donutData = formatEntries.map(([name, value]) => ({
    name,
    value,
    fill: FORMAT_COLORS[name] ?? "#737373",
  }));

  return (
    <>
      <div
        className="group cursor-pointer overflow-hidden rounded-2xl border bg-card/80 shadow-sm backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 hover:scale-[1.01] hover:shadow-lg"
        onClick={handleCardClick}
      >
        <div className="flex flex-col gap-4 p-5">
          {/* Header: domain + platform + status + delete */}
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-base font-semibold">{domain_info.domain}</h3>
              <div className="mt-2 flex items-center gap-2">
                <Badge
                  variant="secondary"
                  className={`text-[10px] uppercase ${PLATFORM_COLORS[domain_info.platform] ?? PLATFORM_COLORS.all}`}
                >
                  {domain_info.platform}
                </Badge>
                {domain_info.is_active ? (
                  <span className="inline-flex items-center gap-1.5 text-[11px] text-emerald-600">
                    <span className="relative flex size-2">
                      <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                      <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
                    </span>
                    Active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <span className="relative flex size-2">
                      <span className="relative inline-flex size-2 rounded-full bg-muted-foreground/40" />
                    </span>
                    Paused
                  </span>
                )}
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon-xs"
              className="shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
              onClick={(e) => {
                e.stopPropagation();
                setShowDeleteDialog(true);
              }}
            >
              <Trash2 className="size-3.5 text-muted-foreground" />
            </Button>
          </div>

          {/* Stats section: format breakdown + mini donut */}
          {formatEntries.length > 0 && (
            <div className="flex items-center gap-4">
              <div className="flex flex-1 flex-col gap-1.5">
                {formatEntries.map(([format, count]) => (
                  <div key={format} className="flex items-center gap-2">
                    <span className="w-12 text-xs capitalize text-muted-foreground">
                      {format}
                    </span>
                    <Progress
                      value={total_ads > 0 ? (count / total_ads) * 100 : 0}
                      className="h-1.5 flex-1"
                    />
                    <span className="w-8 text-right text-xs tabular-nums">{count}</span>
                  </div>
                ))}
              </div>
              <div className="shrink-0">
                <MiniDonutChart data={donutData} size={72} />
              </div>
            </div>
          )}

          {/* Notes */}
          {domain_info.notes && (
            <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
              {domain_info.notes}
            </p>
          )}

          {/* Footer: total ads + last collected */}
          <div className="flex items-center justify-between border-t pt-3 text-xs text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Activity className="size-3.5" />
              <span className="font-semibold text-foreground">{formatCount(total_ads)}</span>
              <span>ads</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock className="size-3" />
              <span>
                {last_collected_at
                  ? formatRelativeTime(last_collected_at)
                  : "Not yet collected"}
              </span>
            </div>
          </div>
        </div>
      </div>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove competitor</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to stop monitoring "{domain_info.domain}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

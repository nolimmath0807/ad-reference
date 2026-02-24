import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Trash2, Activity, AlertCircle } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { CompetitorStats } from "@/types/competitor";

interface CompetitorCardProps {
  stats: CompetitorStats;
  onDeleted: () => void;
}

const platformColors: Record<string, string> = {
  google: "bg-red-500/10 text-red-600",
  meta: "bg-blue-500/10 text-blue-600",
  tiktok: "bg-neutral-900/10 text-neutral-800",
  instagram: "bg-pink-500/10 text-pink-600",
  all: "bg-neutral-500/10 text-neutral-600",
};

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

  const formatCount = (count: number): string => {
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return String(count);
  };

  const lastCollected = last_collected_at
    ? new Date(last_collected_at).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "Not yet collected";

  const formatEntries = Object.entries(stats.ads_by_format);

  return (
    <>
      <Card
        className="group cursor-pointer overflow-hidden transition-shadow hover:shadow-md"
        onClick={handleCardClick}
      >
        <div className="flex flex-col gap-3 p-5">
          {/* Header: domain + delete button */}
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-sm font-semibold">{domain_info.domain}</h3>
              <div className="mt-1.5 flex items-center gap-2">
                <Badge
                  variant="secondary"
                  className={`text-[10px] uppercase ${platformColors[domain_info.platform] ?? platformColors.all}`}
                >
                  {domain_info.platform}
                </Badge>
                {domain_info.is_active ? (
                  <span className="inline-flex items-center gap-1 text-[11px] text-green-600">
                    <span className="size-1.5 rounded-full bg-green-500" />
                    Active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                    <span className="size-1.5 rounded-full bg-muted-foreground/40" />
                    Inactive
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

          {/* Stats */}
          <div className="flex items-center gap-4 rounded-lg bg-muted/50 px-3 py-2.5">
            <div className="flex items-center gap-1.5">
              <Activity className="size-3.5 text-muted-foreground" />
              <span className="text-sm font-semibold">{formatCount(total_ads)}</span>
              <span className="text-xs text-muted-foreground">ads</span>
            </div>
            {formatEntries.length > 0 && (
              <div className="flex items-center gap-1.5 border-l pl-4">
                {formatEntries.slice(0, 3).map(([format, count]) => (
                  <Badge key={format} variant="outline" className="text-[10px] font-normal">
                    {format} {count}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Notes */}
          {domain_info.notes && (
            <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
              {domain_info.notes}
            </p>
          )}

          {/* Last collected */}
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <AlertCircle className="size-3" />
            Last collected: {lastCollected}
          </div>
        </div>
      </Card>

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

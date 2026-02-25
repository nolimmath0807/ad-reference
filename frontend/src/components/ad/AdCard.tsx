import { useState } from "react";
import { Eye, Bookmark, Heart, MessageCircle, Share2, ImageOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import type { Ad, PlatformType, FormatType } from "@/types/ad";

interface AdCardProps {
  ad: Ad;
  onClick?: (ad: Ad) => void;
  onSave?: (ad: Ad) => void;
}

const platformStyles: Record<PlatformType, { label: string; className: string }> = {
  meta: { label: "Meta", className: "bg-blue-500 text-white" },
  google: { label: "Google", className: "bg-red-500 text-white" },
  tiktok: { label: "TikTok", className: "bg-neutral-900 text-white" },
};

const formatLabels: Record<FormatType, string> = {
  image: "Image",
  video: "Video",
  carousel: "Carousel",
  reels: "Reels",
  text: "Text",
};

function formatCount(count: number | null): string {
  if (count === null) return "0";
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  return count.toLocaleString();
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function AdCard({ ad, onClick, onSave }: AdCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [imgError, setImgError] = useState(false);
  const platform = platformStyles[ad.platform];

  const showPlaceholder = !ad.thumbnail_url || imgError;

  return (
    <div
      className="group cursor-pointer overflow-hidden rounded-xl border border-border bg-card transition-all duration-200 hover:scale-[1.02] hover:shadow-lg"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onClick?.(ad)}
    >
      {/* Thumbnail */}
      <div className="relative aspect-[4/3] overflow-hidden bg-muted">
        {ad.format === "text" && ad.ad_copy ? (
          <div className="flex h-full w-full flex-col justify-center gap-2 bg-background p-4">
            <div className="flex items-center gap-1.5 text-xs">
              <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">Ad</span>
              {ad.landing_page_url && (
                <span className="truncate text-sm text-green-700 dark:text-green-400">
                  {(() => { try { return new URL(ad.landing_page_url).hostname; } catch { return ad.landing_page_url; } })()}
                </span>
              )}
            </div>
            <p className="line-clamp-2 text-sm font-medium leading-snug text-blue-600 dark:text-blue-400">
              {ad.ad_copy.split('\n')[0]}
            </p>
            {ad.ad_copy.split('\n').length > 1 && (
              <p className="line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                {ad.ad_copy.split('\n').slice(1).join(' ')}
              </p>
            )}
          </div>
        ) : ad.format === "text" && !ad.ad_copy && ad.thumbnail_url && !imgError ? (
          <>
            <img
              src={ad.thumbnail_url}
              alt={ad.advertiser_name}
              onError={() => setImgError(true)}
              className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            />
            <div className="absolute bottom-2 right-2 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-medium text-white">
              TEXT
            </div>
          </>
        ) : ad.format === "text" ? (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-muted">
            <span className="text-xs font-medium text-muted-foreground/60">Search Ad</span>
          </div>
        ) : showPlaceholder ? (
          <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-muted">
            <ImageOff className="size-8 text-muted-foreground/40" />
            <span className="text-xs font-medium text-muted-foreground/60">
              {formatLabels[ad.format]}
            </span>
          </div>
        ) : (
          <img
            src={ad.thumbnail_url}
            alt={ad.advertiser_name}
            onError={() => setImgError(true)}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        )}

        {/* Hover overlay */}
        <div
          className={cn(
            "absolute inset-0 flex items-center justify-center gap-3 bg-black/40 transition-opacity duration-200",
            isHovered ? "opacity-100" : "opacity-0"
          )}
        >
          <button
            className="flex size-10 items-center justify-center rounded-full bg-white/90 text-neutral-800 shadow-sm transition-transform hover:scale-110"
            onClick={(e) => {
              e.stopPropagation();
              onClick?.(ad);
            }}
          >
            <Eye className="size-4.5" />
          </button>
          <button
            className="flex size-10 items-center justify-center rounded-full bg-white/90 text-neutral-800 shadow-sm transition-transform hover:scale-110"
            onClick={(e) => {
              e.stopPropagation();
              onSave?.(ad);
            }}
          >
            <Bookmark className="size-4.5" />
          </button>
        </div>

        {/* Media type indicator for video */}
        {ad.media_type === "video" && (
          <div className="absolute bottom-2 right-2 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-medium text-white">
            VIDEO
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex flex-col gap-2.5 p-3.5">
        {/* Badges */}
        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold",
              platform.className
            )}
          >
            {platform.label}
          </span>
          <Badge variant="secondary" className="text-[10px] font-medium">
            {formatLabels[ad.format]}
          </Badge>
        </div>

        {/* Advertiser */}
        <div className="flex items-center gap-2">
          <Avatar size="sm">
            {ad.advertiser_avatar_url ? (
              <AvatarImage src={ad.advertiser_avatar_url} alt={ad.advertiser_name} />
            ) : null}
            <AvatarFallback>{ad.advertiser_name.charAt(0).toUpperCase()}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium leading-tight">{ad.advertiser_name}</p>
            {ad.advertiser_handle && (
              <p className="truncate text-xs text-muted-foreground">{ad.advertiser_handle}</p>
            )}
          </div>
        </div>

        {/* Ad copy */}
        {ad.ad_copy && (
          <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
            {ad.ad_copy}
          </p>
        )}

        {/* Engagement */}
        <div className="flex items-center gap-3.5 text-muted-foreground">
          <span className="flex items-center gap-1 text-xs">
            <Heart className="size-3.5" />
            {formatCount(ad.likes)}
          </span>
          <span className="flex items-center gap-1 text-xs">
            <MessageCircle className="size-3.5" />
            {formatCount(ad.comments)}
          </span>
          <span className="flex items-center gap-1 text-xs">
            <Share2 className="size-3.5" />
            {formatCount(ad.shares)}
          </span>
        </div>

        {/* Date */}
        {ad.start_date && (
          <p className="text-[11px] text-muted-foreground/70">{formatDate(ad.start_date)}</p>
        )}
      </div>
    </div>
  );
}

import { useState } from "react";
import { Heart, MessageCircle, Share2, ImageIcon, ImageOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { Ad } from "@/types/ad";

interface AdGridProps {
  ads: Ad[];
  loading: boolean;
  hasNext: boolean;
  onAdClick: (ad: Ad) => void;
  onLoadMore: () => void;
}

const platformColors: Record<string, string> = {
  meta: "bg-blue-500/10 text-blue-600",
  google: "bg-green-500/10 text-green-600",
  tiktok: "bg-neutral-900/10 text-neutral-800",
  instagram: "bg-pink-500/10 text-pink-600",
};

const formatLabels: Record<string, string> = {
  image: "Image",
  video: "Video",
  carousel: "Carousel",
  reels: "Reels",
};

function formatCount(count: number | null): string {
  if (count === null) return "--";
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
  return String(count);
}

function AdThumbnail({ url, alt, format }: { url: string | null; alt: string; format: string }) {
  const [imgError, setImgError] = useState(false);
  const showPlaceholder = !url || imgError;

  if (showPlaceholder) {
    return (
      <div className="flex size-full flex-col items-center justify-center gap-2 bg-muted">
        <ImageOff className="size-8 text-muted-foreground/40" />
        <span className="text-xs font-medium text-muted-foreground/60">
          {formatLabels[format] ?? format}
        </span>
      </div>
    );
  }

  return (
    <img
      src={url}
      alt={alt}
      onError={() => setImgError(true)}
      className="size-full object-cover transition-transform group-hover:scale-105"
    />
  );
}

function AdCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <Skeleton className="aspect-[4/3] w-full rounded-none" />
      <div className="space-y-3 p-4">
        <div className="flex items-center gap-2">
          <Skeleton className="size-6 rounded-full" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-12" />
        </div>
      </div>
    </div>
  );
}

export function AdGrid({ ads, loading, hasNext, onAdClick, onLoadMore }: AdGridProps) {
  if (loading && ads.length === 0) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <AdCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (!loading && ads.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20">
        <ImageIcon className="mb-4 size-12 text-muted-foreground/30" />
        <h3 className="text-lg font-semibold">No ads found</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Try adjusting your search or filters to find what you're looking for.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {ads.map((ad) => (
          <button
            key={ad.id}
            onClick={() => onAdClick(ad)}
            className="group overflow-hidden rounded-xl border bg-card text-left transition-shadow hover:shadow-md"
          >
            {/* Thumbnail */}
            <div className="relative aspect-[4/3] overflow-hidden bg-muted">
              <AdThumbnail url={ad.thumbnail_url} alt={ad.advertiser_name} format={ad.format} />
              {/* Platform badge */}
              <Badge
                variant="secondary"
                className={`absolute left-2 top-2 text-[10px] uppercase ${platformColors[ad.platform] ?? ""}`}
              >
                {ad.platform}
              </Badge>
              {/* Format badge */}
              <Badge variant="secondary" className="absolute right-2 top-2 text-[10px]">
                {formatLabels[ad.format] ?? ad.format}
              </Badge>
            </div>

            {/* Card body */}
            <div className="space-y-2.5 p-3.5">
              {/* Advertiser */}
              <div className="flex items-center gap-2">
                {ad.advertiser_avatar_url ? (
                  <img
                    src={ad.advertiser_avatar_url}
                    alt={ad.advertiser_name}
                    className="size-6 rounded-full object-cover"
                  />
                ) : (
                  <div className="flex size-6 items-center justify-center rounded-full bg-muted text-[10px] font-medium text-muted-foreground">
                    {ad.advertiser_name.charAt(0).toUpperCase()}
                  </div>
                )}
                <span className="truncate text-sm font-medium">{ad.advertiser_name}</span>
              </div>

              {/* Ad copy */}
              {ad.ad_copy && (
                <p className="line-clamp-2 text-xs text-muted-foreground leading-relaxed">
                  {ad.ad_copy}
                </p>
              )}

              {/* Engagement stats */}
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <Heart className="size-3" />
                  {formatCount(ad.likes)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <MessageCircle className="size-3" />
                  {formatCount(ad.comments)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <Share2 className="size-3" />
                  {formatCount(ad.shares)}
                </span>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Load more */}
      {hasNext && (
        <div className="flex justify-center">
          <Button
            variant="outline"
            onClick={onLoadMore}
            disabled={loading}
            className="min-w-[160px]"
          >
            {loading ? "Loading..." : "Load more"}
          </Button>
        </div>
      )}
    </div>
  );
}

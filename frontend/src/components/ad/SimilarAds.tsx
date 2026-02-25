import { useState } from "react";
import { cn } from "@/lib/utils";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import type { Ad, PlatformType } from "@/types/ad";

interface SimilarAdsProps {
  ads: Ad[];
  onAdClick?: (ad: Ad) => void;
}

const platformStyles: Record<PlatformType, { label: string; className: string }> = {
  meta: { label: "Meta", className: "bg-blue-500 text-white" },
  google: { label: "Google", className: "bg-red-500 text-white" },
  tiktok: { label: "TikTok", className: "bg-neutral-900 text-white" },
};

function getImageUrl(url: string | null | undefined): string {
  if (!url) return "";
  if (url.startsWith("/static/")) {
    return `${import.meta.env.VITE_API_BASE_URL}${url}`;
  }
  return url;
}

function SimilarAdImage({ ad }: { ad: Ad }) {
  const [imgError, setImgError] = useState(false);
  const resolvedUrl = getImageUrl(ad.thumbnail_url);
  const showPlaceholder = !resolvedUrl || imgError;

  return (
    <>
      {resolvedUrl && !imgError && (
        <img
          src={resolvedUrl}
          alt={ad.advertiser_name}
          className="h-full w-full object-cover transition-transform duration-200 hover:scale-105"
          onError={() => setImgError(true)}
        />
      )}
      {showPlaceholder && (
        <div className="flex h-full w-full items-center justify-center bg-muted">
          <span className="text-xs text-muted-foreground">{ad.format}</span>
        </div>
      )}
    </>
  );
}

export function SimilarAds({ ads, onAdClick }: SimilarAdsProps) {
  if (ads.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-foreground">Similar Ads</h3>
      <ScrollArea className="w-full">
        <div className="flex gap-3 pb-3">
          {ads.map((ad) => {
            const platform = platformStyles[ad.platform];
            return (
              <div
                key={ad.id}
                className="flex w-[150px] shrink-0 cursor-pointer flex-col overflow-hidden rounded-lg border border-border bg-card transition-all duration-200 hover:shadow-md"
                onClick={() => onAdClick?.(ad)}
              >
                <div className="relative aspect-[4/3] overflow-hidden bg-muted">
                  <SimilarAdImage ad={ad} />
                  <span
                    className={cn(
                      "absolute bottom-1.5 left-1.5 inline-flex items-center rounded-full px-1.5 py-0.5 text-[9px] font-semibold",
                      platform.className
                    )}
                  >
                    {platform.label}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5 px-2.5 py-2">
                  <p className="truncate text-xs font-medium">{ad.advertiser_name}</p>
                  {ad.ad_copy && (
                    <p className="line-clamp-1 text-[11px] text-muted-foreground">
                      {ad.ad_copy}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </div>
  );
}

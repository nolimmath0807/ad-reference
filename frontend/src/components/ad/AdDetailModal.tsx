import { useState, useEffect } from "react";
import {
  ExternalLink,
  Bookmark,
  Link2,
  Calendar,
  Tag,
  Loader2,
  ImageIcon,
  Film,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import { AdMetrics } from "@/components/ad/AdMetrics";
import { SimilarAds } from "@/components/ad/SimilarAds";
import { SaveToBoardDialog } from "@/components/ad/SaveToBoardDialog";
import type { Ad, AdDetailResponse, PlatformType, FormatType } from "@/types/ad";

interface AdDetailModalProps {
  ad: Ad | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const platformStyles: Record<PlatformType, { label: string; className: string }> = {
  meta: { label: "Meta", className: "bg-blue-500 text-white" },
  google: { label: "Google", className: "bg-red-500 text-white" },
  tiktok: { label: "TikTok", className: "bg-neutral-900 text-white" },
  instagram: {
    label: "Instagram",
    className: "bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 text-white",
  },
};

const formatLabels: Record<FormatType, string> = {
  image: "Image",
  video: "Video",
  carousel: "Carousel",
  reels: "Reels",
  text: "Text",
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function isPlayableVideoUrl(url: string): boolean {
  const lower = url.toLowerCase();
  const videoExtensions = [".mp4", ".webm", ".mov", ".ogg"];
  const videoHosts = [
    "googlevideo.com",
    "youtube.com",
    "ytimg.com",
    "googlesyndication.com",
    "fbcdn.net",
    "cdninstagram.com",
    "tiktokcdn.com",
  ];
  if (videoExtensions.some((ext) => lower.includes(ext))) return true;
  if (videoHosts.some((host) => lower.includes(host))) return true;
  return false;
}

function isYouTubeUrl(url: string): boolean {
  return url.includes("youtube.com/embed/") || url.includes("youtube.com/watch?v=") || url.includes("youtu.be/");
}

function getYouTubeEmbedUrl(url: string): string {
  const watchMatch = url.match(/youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)/);
  if (watchMatch) return `https://www.youtube.com/embed/${watchMatch[1]}`;
  const shortMatch = url.match(/youtu\.be\/([a-zA-Z0-9_-]+)/);
  if (shortMatch) return `https://www.youtube.com/embed/${shortMatch[1]}`;
  return url;
}

function getImageUrl(url: string | null | undefined): string {
  if (!url) return "";
  if (url.startsWith("/static/")) {
    return `${import.meta.env.VITE_API_BASE_URL}${url}`;
  }
  return url;
}

export function AdDetailModal({ ad, open, onOpenChange }: AdDetailModalProps) {
  const [detail, setDetail] = useState<AdDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [mediaError, setMediaError] = useState(false);

  useEffect(() => {
    if (open && ad) {
      setDetail(null);
      setIsLoading(true);
      setMediaError(false);
      api.get<AdDetailResponse>(`/ads/${ad.id}`).then((data) => {
        setDetail(data);
        setIsLoading(false);
      });
    }
  }, [open, ad?.id]);

  const currentAd = detail?.ad ?? ad;

  const handleCopyLink = () => {
    const url = `${window.location.origin}/ads/${currentAd?.id}`;
    navigator.clipboard.writeText(url);
    toast.success("Link copied to clipboard.");
  };

  if (!currentAd) return null;

  const platform = platformStyles[currentAd.platform];
  const isVideoAd =
    currentAd.media_type === "video" ||
    (currentAd.preview_url != null && isYouTubeUrl(currentAd.preview_url));

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[90vh] overflow-hidden p-0 sm:max-w-5xl">
          <ScrollArea className="max-h-[90vh]">
            <div className={cn("flex flex-col", !isVideoAd && "lg:flex-row")}>
              {/* Media preview */}
              <div
                className={cn(
                  "flex min-h-[300px] items-center justify-center bg-muted/30",
                  isVideoAd ? "w-full" : "lg:w-[55%]"
                )}
              >
                {currentAd.format === "text" && currentAd.ad_copy ? (
                  <div className="flex min-h-[300px] w-full flex-col justify-center gap-4 rounded-lg border bg-background p-8">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-muted px-2 py-1 text-xs font-semibold text-muted-foreground">Ad</span>
                      {currentAd.landing_page_url && (
                        <span className="text-sm text-green-700 dark:text-green-400">
                          {(() => { try { return new URL(currentAd.landing_page_url).hostname; } catch { return ''; } })()}
                        </span>
                      )}
                    </div>
                    <div className="space-y-3">
                      <p className="text-xl font-medium text-blue-600 dark:text-blue-400">
                        {currentAd.ad_copy.split('\n')[0]}
                      </p>
                      {currentAd.ad_copy.split('\n').length > 1 && (
                        <p className="whitespace-pre-line text-sm leading-relaxed text-foreground/70">
                          {currentAd.ad_copy.split('\n').slice(1).join('\n')}
                        </p>
                      )}
                    </div>
                  </div>
                ) : currentAd.format === "text" && !currentAd.ad_copy && currentAd.thumbnail_url && !mediaError ? (
                  <div className="relative flex min-h-[300px] w-full items-center justify-center">
                    <img
                      src={getImageUrl(currentAd.thumbnail_url)}
                      alt={currentAd.advertiser_name}
                      className="max-h-[500px] w-full object-contain"
                      onError={() => setMediaError(true)}
                    />
                    <div className="absolute bottom-3 right-3 rounded-md bg-black/70 px-2 py-1 text-xs font-medium text-white">
                      TEXT
                    </div>
                  </div>
                ) : mediaError || (!currentAd.thumbnail_url && !currentAd.preview_url) ? (
                  <div className="flex h-full min-h-[300px] w-full flex-col items-center justify-center gap-3 bg-muted/50">
                    {currentAd.media_type === "video" ? (
                      <Film className="size-12 text-muted-foreground/40" />
                    ) : (
                      <ImageIcon className="size-12 text-muted-foreground/40" />
                    )}
                    <Badge variant="secondary" className="text-xs">
                      {formatLabels[currentAd.format]}
                    </Badge>
                  </div>
                ) : currentAd.preview_url &&
                  isYouTubeUrl(currentAd.preview_url) ? (
                  <iframe
                    src={getYouTubeEmbedUrl(currentAd.preview_url)}
                    className="aspect-video max-h-[400px] w-full"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                ) : currentAd.media_type === "video" &&
                  currentAd.preview_url &&
                  isPlayableVideoUrl(currentAd.preview_url) ? (
                  <video
                    src={currentAd.preview_url}
                    controls
                    className="max-h-[500px] w-full object-contain"
                    poster={getImageUrl(currentAd.thumbnail_url)}
                    onError={() => setMediaError(true)}
                  />
                ) : (
                  <img
                    src={getImageUrl(currentAd.thumbnail_url)}
                    alt={currentAd.advertiser_name}
                    className="max-h-[500px] w-full object-contain"
                    onError={() => setMediaError(true)}
                  />
                )}
              </div>

              {/* Details */}
              <div
                className={cn(
                  "flex flex-col gap-5 p-6",
                  isVideoAd ? "w-full" : "lg:w-[45%]"
                )}
              >
                {/* Loading indicator */}
                {isLoading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="size-3.5 animate-spin" />
                    Loading details...
                  </div>
                )}

                {/* Header hidden for a11y, visually using advertiser below */}
                <DialogHeader className="sr-only">
                  <DialogTitle>{currentAd.advertiser_name} Ad Detail</DialogTitle>
                  <DialogDescription>Full details for this ad creative.</DialogDescription>
                </DialogHeader>

                {/* Advertiser */}
                <div className="flex items-center gap-3">
                  <Avatar>
                    {currentAd.advertiser_avatar_url ? (
                      <AvatarImage
                        src={currentAd.advertiser_avatar_url}
                        alt={currentAd.advertiser_name}
                      />
                    ) : null}
                    <AvatarFallback>
                      {currentAd.advertiser_name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{currentAd.advertiser_name}</p>
                    {currentAd.advertiser_handle && (
                      <p className="truncate text-xs text-muted-foreground">
                        {currentAd.advertiser_handle}
                      </p>
                    )}
                  </div>
                </div>

                {/* Badges */}
                <div className="flex flex-wrap items-center gap-1.5">
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
                      platform.className
                    )}
                  >
                    {platform.label}
                  </span>
                  <Badge variant="secondary" className="text-[11px]">
                    {formatLabels[currentAd.format]}
                  </Badge>
                </div>

                {/* Ad copy */}
                {currentAd.ad_copy && (
                  <p className="text-sm leading-relaxed text-foreground/80">
                    {currentAd.ad_copy}
                  </p>
                )}

                {/* CTA */}
                {currentAd.cta_text && (
                  <div className="rounded-lg bg-brand-primary/5 px-4 py-3 ring-1 ring-brand-primary/15">
                    <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                      Call to Action
                    </p>
                    <p className="mt-0.5 text-sm font-semibold text-brand-primary">
                      {currentAd.cta_text}
                    </p>
                  </div>
                )}

                {/* Metrics */}
                <AdMetrics
                  likes={currentAd.likes}
                  comments={currentAd.comments}
                  shares={currentAd.shares}
                />

                {/* Tags */}
                {currentAd.tags.length > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                      <Tag className="size-3.5" />
                      Tags
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {currentAd.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs font-normal">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Landing page */}
                {currentAd.landing_page_url && (
                  <a
                    href={currentAd.landing_page_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-sm text-brand-primary hover:underline"
                  >
                    <ExternalLink className="size-3.5" />
                    Visit landing page
                  </a>
                )}

                {/* Dates */}
                {(currentAd.start_date || currentAd.end_date) && (
                  <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
                    <Calendar className="mt-0.5 size-3.5 shrink-0" />
                    <span className="leading-relaxed">
                      {formatDate(currentAd.start_date)}
                      {currentAd.end_date && ` \u2014 ${formatDate(currentAd.end_date)}`}
                    </span>
                  </div>
                )}

                <Separator />

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    className="flex-1 bg-brand-primary text-brand-primary-foreground hover:bg-brand-primary/90"
                    onClick={() => setShowSaveDialog(true)}
                  >
                    <Bookmark className="size-4" />
                    Save to Board
                  </Button>
                  <Button variant="outline" size="icon" onClick={handleCopyLink}>
                    <Link2 className="size-4" />
                  </Button>
                </div>

                {/* Similar ads */}
                {detail?.similar_ads && detail.similar_ads.length > 0 && (
                  <>
                    <Separator />
                    <SimilarAds
                      ads={detail.similar_ads}
                      onAdClick={(newAd) => {
                        setDetail(null);
                        setIsLoading(true);
                        setMediaError(false);
                        api.get<AdDetailResponse>(`/ads/${newAd.id}`).then((data) => {
                          setDetail(data);
                          setIsLoading(false);
                        });
                      }}
                    />
                  </>
                )}
              </div>
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {currentAd && (
        <SaveToBoardDialog
          adId={currentAd.id}
          open={showSaveDialog}
          onOpenChange={setShowSaveDialog}
        />
      )}
    </>
  );
}

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
  FileText,
  Download,
  Star,
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
import { AdComments } from "@/components/ad/AdComments";
import { SimilarAds } from "@/components/ad/SimilarAds";
import { SaveToBoardDialog } from "@/components/ad/SaveToBoardDialog";
import type { Ad, AdDetailResponse, AdScriptResponse, PlatformType, FormatType } from "@/types/ad";
import { useAuth } from "@/contexts/AuthContext";

interface AdDetailModalProps {
  ad: Ad | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  featuredIds?: Set<string>;
  onFeaturedChange?: (adId: string) => void;
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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}


function isYouTubeUrl(url: string): boolean {
  return url.includes("youtube.com/embed/") || url.includes("youtube.com/watch?v=") || url.includes("youtu.be/");
}



const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function getImageUrl(url: string | null | undefined): string {
  if (!url) return "";
  if (url.startsWith("/static/")) {
    return `${import.meta.env.VITE_API_BASE_URL}${url}`;
  }
  return url;
}

function getDownloadFilename(ad: Ad): string {
  const name = (ad.advertiser_name || "ad").replace(/[\\/:*?"<>|]/g, "_");
  const date = ad.saved_at ? ad.saved_at.slice(0, 10).replace(/-/g, "") : "unknown";
  const shortId = ad.id.slice(0, 4);
  const ext = ad.media_type === "video" ? "mp4" : "jpg";
  return `${name}_${date}_${shortId}.${ext}`;
}

export function AdDetailModal({ ad, open, onOpenChange, featuredIds, onFeaturedChange }: AdDetailModalProps) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [detail, setDetail] = useState<AdDetailResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [mediaError, setMediaError] = useState(false);
  const [script, setScript] = useState<AdScriptResponse | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [featuredLoading, setFeaturedLoading] = useState(false);
  const [videoLoading, setVideoLoading] = useState(false);
  const [videoAttempt, setVideoAttempt] = useState(0);

  useEffect(() => {
    if (open && ad) {
      setDetail(null);
      setIsLoading(true);
      setMediaError(false);
      setVideoLoading(false);
      setVideoAttempt(0);
      api.get<AdDetailResponse>(`/ads/${ad.id}`).then((data) => {
        setDetail(data);
        setIsLoading(false);
      });
    }
  }, [open, ad?.id]);

  useEffect(() => {
    if (open && ad && ad.media_type === "video") {
      api
        .get<AdScriptResponse>(`/ads/${ad.id}/script`)
        .then((data) => {
          if (data.status !== "not_found") setScript(data);
        })
        .catch(() => {});
    }
    if (!open) {
      setScript(null);
      setIsExtracting(false);
    }
  }, [open, ad?.id]);

  const currentAd = detail?.ad ?? ad;

  const handleCopyLink = () => {
    const url = `${window.location.origin}/ads/${currentAd?.id}`;
    navigator.clipboard.writeText(url);
    toast.success("Link copied to clipboard.");
  };

  const handleAddToFeatured = async () => {
    if (!currentAd) return;
    const isFeatured = featuredIds?.has(currentAd.id) ?? false;
    if (isFeatured) {
      toast.info("이미 Featured References에 추가된 광고입니다.");
      return;
    }
    setFeaturedLoading(true);
    try {
      await api.post("/admin/featured-references", { ad_id: currentAd.id });
      toast.success("Featured References에 추가되었습니다.");
      onFeaturedChange?.(currentAd.id);
    } catch (err: any) {
      if (err?.status === 409 || err?.response?.status === 409) {
        toast.info("이미 Featured References에 추가된 광고입니다.");
        onFeaturedChange?.(currentAd.id);
      } else {
        toast.error("추가에 실패했습니다.");
      }
    } finally {
      setFeaturedLoading(false);
    }
  };

  const handleExtractScript = async () => {
    if (!currentAd) return;
    setIsExtracting(true);
    try {
      const result = await api.post<AdScriptResponse & { job_id?: string }>(
        `/ads/${currentAd.id}/script/extract`
      );
      if (result.status === "completed") {
        setScript(result);
        setIsExtracting(false);
        return;
      }
      const pollInterval = setInterval(async () => {
        const status = await api.get<AdScriptResponse>(
          `/ads/${currentAd.id}/script`
        );
        if (status.status === "completed" || status.status === "failed") {
          setScript(status);
          setIsExtracting(false);
          clearInterval(pollInterval);
        }
      }, 3000);
      setTimeout(() => {
        clearInterval(pollInterval);
        setIsExtracting(false);
      }, 120000);
    } catch {
      setIsExtracting(false);
    }
  };

  const handleDownload = async () => {
    if (!currentAd) return;
    setDownloading(true);
    try {
      // YouTube 영상: 백엔드 yt-dlp 프록시로 직접 다운로드 (fetch-blob 우회)
      if (currentAd.preview_url && isYouTubeUrl(currentAd.preview_url)) {
        const a = document.createElement("a");
        a.href = `${API_BASE_URL}/ads/${currentAd.id}/video/download`;
        a.download = getDownloadFilename(currentAd);
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        return;
      }

      const downloadUrl =
        currentAd.media_type === "video" && currentAd.preview_url
          ? currentAd.preview_url
          : getImageUrl(currentAd.thumbnail_url);

      const response = await fetch(downloadUrl, { mode: "cors" });
      if (!response.ok) throw new Error("Download failed");
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = getDownloadFilename(currentAd);
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(blobUrl);
    } catch {
      toast.error("다운로드에 실패했습니다.");
    } finally {
      setDownloading(false);
    }
  };

  if (!currentAd) return null;

  const platform = platformStyles[currentAd.platform];

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[90vh] overflow-hidden p-0 sm:max-w-5xl">
          <ScrollArea className="max-h-[90vh]">
            {/* Header hidden for a11y */}
            <DialogHeader className="sr-only">
              <DialogTitle>{currentAd.advertiser_name} Ad Detail</DialogTitle>
              <DialogDescription>Full details for this ad creative.</DialogDescription>
            </DialogHeader>

            {/* Main two-column layout */}
            <div className="flex flex-col md:flex-row">
              {/* Left: Media preview */}
              <div className="flex max-h-[40vh] shrink-0 flex-col overflow-hidden bg-muted/30 md:max-h-none md:sticky md:top-0 md:w-[55%] md:self-start">
                <div className="flex min-h-[200px] flex-1 w-full items-center justify-center md:min-h-[400px]">
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
                        className="max-h-[40vh] w-full object-contain md:max-h-[70vh]"
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
                  ) : currentAd.media_type === "video" && currentAd.preview_url ? (
                    <div className="relative w-full">
                      {videoLoading && (
                        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-muted/80">
                          <Loader2 className="size-8 animate-spin text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">영상 준비 중...</span>
                        </div>
                      )}
                      <video
                        key={videoAttempt}
                        src={
                          videoAttempt === 0
                            ? `${API_BASE_URL}/ads/${currentAd.id}/video`
                            : currentAd.preview_url ?? undefined
                        }
                        controls
                        className="w-full max-h-[40vh] object-contain md:max-h-[70vh]"
                        poster={getImageUrl(currentAd.thumbnail_url)}
                        onLoadStart={() => setVideoLoading(true)}
                        onCanPlay={() => setVideoLoading(false)}
                        onError={() => {
                          setVideoLoading(false);
                          const isYouTube =
                            currentAd.preview_url?.includes("youtube") ||
                            currentAd.preview_url?.includes("youtu.be");
                          if (videoAttempt === 0 && currentAd.preview_url && !isYouTube) {
                            setVideoAttempt(1);
                            setVideoLoading(true);
                          } else {
                            setMediaError(true);
                          }
                        }}
                      />
                    </div>
                  ) : (
                    <img
                      src={getImageUrl(currentAd.thumbnail_url)}
                      alt={currentAd.advertiser_name}
                      className="max-h-[40vh] w-full object-contain md:max-h-[70vh]"
                      onError={() => setMediaError(true)}
                    />
                  )}
                </div>

                {/* Media action bar */}
                {(currentAd.preview_url || currentAd.thumbnail_url) && (
                  <div className="flex items-center justify-between px-3 py-2">
                    <button
                      type="button"
                      onClick={handleDownload}
                      disabled={downloading}
                      className="inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground disabled:opacity-50"
                    >
                      {downloading ? (
                        <Loader2 className="size-3 animate-spin" />
                      ) : (
                        <Download className="size-3" />
                      )}
                      다운로드
                    </button>
                  </div>
                )}
              </div>

              {/* Right: Details */}
              <div className="flex flex-col gap-5 p-6 md:w-[45%] md:overflow-y-auto md:max-h-[80vh]">
                {/* Loading indicator */}
                {isLoading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="size-3.5 animate-spin" />
                    Loading details...
                  </div>
                )}

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

                {/* Metrics */}
                <AdMetrics
                  likes={currentAd.likes}
                  comments={currentAd.comments}
                  shares={currentAd.shares}
                />

                {/* Ad copy */}
                {currentAd.ad_copy && (
                  <>
                    <Separator />
                    <div className="flex flex-col gap-1.5">
                      <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                        Ad Copy
                      </p>
                      <p className="text-sm leading-relaxed text-foreground/80">
                        {currentAd.ad_copy}
                      </p>
                    </div>
                  </>
                )}

                {/* Ad Script (video only) */}
                {currentAd.media_type === "video" && (
                  <>
                    <Separator />
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                          Ad Script
                        </p>
                        {(!script || script.status === "failed") && (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={handleExtractScript}
                            disabled={isExtracting}
                          >
                            {isExtracting ? (
                              <>
                                <Loader2 className="mr-1 size-3 animate-spin" />
                                추출 중...
                              </>
                            ) : (
                              <>
                                <FileText className="mr-1 size-3" />
                                원고 추출
                              </>
                            )}
                          </Button>
                        )}
                      </div>
                      {script?.status === "completed" && script.script_text && (
                        <p className="whitespace-pre-line text-sm leading-relaxed text-foreground/80">
                          {script.script_text}
                        </p>
                      )}
                      {script?.status === "processing" && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="size-3.5 animate-spin" />
                          원고를 추출하고 있습니다...
                        </div>
                      )}
                      {script?.status === "failed" && (
                        <p className="text-sm text-destructive">
                          추출 실패: {script.error_message || "알 수 없는 오류"}
                        </p>
                      )}
                    </div>
                  </>
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

                {/* Dates */}
                {(currentAd.start_date || currentAd.end_date) && (
                  <>
                    <Separator />
                    <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <Calendar className="mt-0.5 size-3.5 shrink-0" />
                      <span className="leading-relaxed">
                        {formatDate(currentAd.start_date)}
                        {currentAd.end_date && ` \u2014 ${formatDate(currentAd.end_date)}`}
                      </span>
                    </div>
                  </>
                )}

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
                  {isAdmin && (() => {
                    const isFeaturedCurrent = featuredIds?.has(currentAd?.id ?? "") ?? false;
                    return (
                      <Button
                        variant={isFeaturedCurrent ? "default" : "outline"}
                        size="icon"
                        onClick={handleAddToFeatured}
                        disabled={featuredLoading}
                        title="Featured에 추가"
                        className={isFeaturedCurrent ? "bg-amber-400 hover:bg-amber-500 text-white" : ""}
                      >
                        <Star className={isFeaturedCurrent ? "size-4 fill-current" : "size-4"} />
                      </Button>
                    );
                  })()}
                  <Button variant="outline" size="icon" onClick={handleCopyLink}>
                    <Link2 className="size-4" />
                  </Button>
                </div>

                {/* Comments */}
                <div className="border-t pt-4">
                  <AdComments adId={currentAd.id} />
                </div>
              </div>
            </div>

            {/* Similar ads - full width below */}
            {detail?.similar_ads && detail.similar_ads.length > 0 && (
              <div className="border-t px-6 py-5">
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
              </div>
            )}
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

import { useState, useEffect, useCallback, useRef } from "react";
import { Star, X, Heart, MessageCircle, Share2, ImageOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AdDetailModal } from "@/components/ad/AdDetailModal";
import { AddFeaturedModal } from "@/components/featured/AddFeaturedModal";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { Ad, PlatformType } from "@/types/ad";

interface Curator {
  id: string | null;
  name: string | null;
  avatar_url: string | null;
  added_at: string;
}

interface FeaturedItem {
  ad_id: string;
  first_added_at: string;
  curators: Curator[];
  ad: Ad;
}

interface FeaturedResponse {
  items: FeaturedItem[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
}

const platformColors: Record<string, string> = {
  meta: "bg-blue-500/10 text-blue-600",
  google: "bg-green-500/10 text-green-600",
  tiktok: "bg-neutral-900/10 text-neutral-800",
};

const formatLabels: Record<string, string> = {
  image: "Image",
  video: "Video",
  carousel: "Carousel",
  reels: "Reels",
  text: "Text",
};

function formatCount(count: number | null): string {
  if (count === null) return "--";
  if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
  if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
  return String(count);
}

function AdThumbnail({ url, alt, format }: { url: string | null; alt: string; format: string }) {
  const [imgError, setImgError] = useState(false);

  if (!url || imgError) {
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

function CardSkeleton() {
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <Skeleton className="aspect-[4/3] w-full rounded-none" />
      <div className="space-y-3 p-4">
        <div className="flex items-center gap-2">
          <Skeleton className="size-6 rounded-full" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-4 w-full" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-12" />
          <Skeleton className="h-3 w-12" />
        </div>
      </div>
    </div>
  );
}

// Platforms excluding tiktok
const featuredPlatforms: { value: "all" | PlatformType; label: string }[] = [
  { value: "all", label: "All" },
  { value: "meta", label: "Meta" },
  { value: "google", label: "Google" },
];

function FeaturedPlatformTabs({
  activePlatform,
  onPlatformChange,
}: {
  activePlatform: "all" | PlatformType;
  onPlatformChange: (p: "all" | PlatformType) => void;
}) {
  return (
    <div className="flex items-center gap-1 border-b">
      {featuredPlatforms.map((platform) => {
        const isActive = activePlatform === platform.value;
        return (
          <button
            key={platform.value}
            onClick={() => onPlatformChange(platform.value)}
            className={`relative px-4 py-2.5 text-sm font-medium transition-colors ${
              isActive
                ? "text-brand-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {platform.label}
            {isActive && (
              <span className="absolute inset-x-0 bottom-0 h-0.5 rounded-full bg-brand-primary" />
            )}
          </button>
        );
      })}
    </div>
  );
}

export function FeaturedPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [items, setItems] = useState<FeaturedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasNext, setHasNext] = useState(false);
  const [page, setPage] = useState(1);

  const [activePlatform, setActivePlatform] = useState<"all" | PlatformType>("all");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [addModalOpen, setAddModalOpen] = useState(false);

  const sentinelRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchItems = useCallback(
    async (pageNum: number, reset: boolean) => {
      setLoading(true);
      const params: Record<string, string | number | boolean | undefined> = {
        page: pageNum,
        limit: 20,
      };
      if (activePlatform !== "all") params.platform = activePlatform;
      if (debouncedSearch.trim()) params.search = debouncedSearch.trim();

      const data = await api
        .get<FeaturedResponse>("/featured-references", params)
        .finally(() => setLoading(false));

      if (reset) {
        setItems(data.items);
      } else {
        setItems((prev) => [...prev, ...data.items]);
      }
      setHasNext(data.has_next);
    },
    [activePlatform, debouncedSearch],
  );

  // Reset on filter change
  useEffect(() => {
    setPage(1);
    fetchItems(1, true);
  }, [activePlatform, debouncedSearch, fetchItems]);

  // Debounce search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setDebouncedSearch(search);
    }, 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [search]);

  // Infinite scroll sentinel
  useEffect(() => {
    if (!hasNext || loading) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          observer.disconnect();
          const nextPage = page + 1;
          setPage(nextPage);
          fetchItems(nextPage, false);
        }
      },
      { rootMargin: "200px" },
    );
    if (sentinelRef.current) observer.observe(sentinelRef.current);
    return () => observer.disconnect();
  }, [hasNext, loading, page, fetchItems]);

  const handleAdClick = (ad: Ad) => {
    setSelectedAd(ad);
    setDetailOpen(true);
  };

  const handleRemove = async (item: FeaturedItem, e: React.MouseEvent) => {
    e.stopPropagation();
    await api.delete(`/admin/featured-references/${item.ad_id}`);
    toast.success("추천에서 제거되었습니다.");
    setItems((prev) => prev.filter((i) => i.ad_id !== item.ad_id));
  };

  const handleAdded = () => {
    setPage(1);
    fetchItems(1, true);
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Featured References</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            큐레이션된 우수 광고 레퍼런스 모음
          </p>
        </div>
        {isAdmin && (
          <Button onClick={() => setAddModalOpen(true)}>
            <Star className="size-4" />
            Add
          </Button>
        )}
      </div>

      {/* Platform Tabs */}
      <FeaturedPlatformTabs
        activePlatform={activePlatform}
        onPlatformChange={setActivePlatform}
      />

      {/* Search */}
      <div className="relative">
        <Input
          placeholder="광고주명으로 검색..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {/* Grid */}
      {loading && items.length === 0 ? (
        <div className="grid gap-4 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
          {Array.from({ length: 8 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : !loading && items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20">
          <Star className="mb-4 size-12 text-muted-foreground/30" />
          <h3 className="text-lg font-semibold">No featured references</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {isAdmin
              ? "Add button을 눌러 추천 레퍼런스를 추가하세요."
              : "아직 등록된 추천 레퍼런스가 없습니다."}
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
            {items.map((item) => (
              <div key={item.ad_id} className="group relative">
                {/* Remove button (admin only) */}
                {isAdmin && (
                  <button
                    onClick={(e) => handleRemove(item, e)}
                    className="absolute right-2 top-2 z-10 flex size-6 items-center justify-center rounded-full bg-background/90 text-destructive opacity-0 shadow transition-opacity hover:bg-destructive hover:text-destructive-foreground group-hover:opacity-100"
                    title="추천에서 제거"
                  >
                    <X className="size-3.5" />
                  </button>
                )}

                {/* Card */}
                <button
                  onClick={() => handleAdClick(item.ad)}
                  className="group/card w-full overflow-hidden rounded-xl border bg-card text-left transition-shadow hover:shadow-md"
                >
                  {/* Advertiser - 카드 최상단 */}
                  <div className="flex items-center gap-2 px-3.5 pt-3 pb-2">
                    {item.ad.advertiser_avatar_url ? (
                      <img
                        src={item.ad.advertiser_avatar_url}
                        alt={item.ad.advertiser_name}
                        className="size-6 rounded-full object-cover"
                      />
                    ) : (
                      <div className="flex size-6 items-center justify-center rounded-full bg-muted text-[10px] font-medium text-muted-foreground">
                        {item.ad.advertiser_name.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <span className="truncate text-sm font-medium">{item.ad.advertiser_name}</span>
                  </div>

                  {/* Thumbnail */}
                  <div className="relative aspect-[4/3] overflow-hidden bg-muted">
                    <AdThumbnail
                      url={item.ad.thumbnail_url}
                      alt={item.ad.advertiser_name}
                      format={item.ad.format}
                    />
                    <Badge
                      variant="secondary"
                      className={`absolute left-2 top-2 text-[10px] uppercase ${platformColors[item.ad.platform] ?? ""}`}
                    >
                      {item.ad.platform}
                    </Badge>
                    <Badge variant="secondary" className="absolute right-2 top-2 text-[10px]">
                      {formatLabels[item.ad.format] ?? item.ad.format}
                    </Badge>
                  </div>

                  {/* Card body */}
                  <div className="space-y-2.5 p-3.5">
                    {/* Ad copy */}
                    {item.ad.ad_copy && (
                      <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                        {item.ad.ad_copy}
                      </p>
                    )}

                    {/* Engagement stats */}
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <Heart className="size-3" />
                        {formatCount(item.ad.likes)}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <MessageCircle className="size-3" />
                        {formatCount(item.ad.comments)}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Share2 className="size-3" />
                        {formatCount(item.ad.shares)}
                      </span>
                    </div>

                    {/* Curator info */}
                    <div className="flex items-center gap-1.5 border-t pt-2 mt-1 min-w-0">
                      {item.curators[0]?.avatar_url ? (
                        <img
                          src={item.curators[0].avatar_url}
                          alt={item.curators[0].name ?? ""}
                          className="size-4 shrink-0 rounded-full object-cover"
                        />
                      ) : (
                        <div className="flex size-4 shrink-0 items-center justify-center rounded-full bg-muted text-[8px] font-medium text-muted-foreground">
                          {item.curators[0]?.name ? item.curators[0].name.charAt(0).toUpperCase() : "?"}
                        </div>
                      )}
                      <span className="truncate text-[10px] text-muted-foreground">
                        {item.curators.map((c) => c.name ?? "Unknown").join(" · ")} ·{" "}
                        {new Date(item.first_added_at).toLocaleDateString("ko-KR", { month: "short", day: "numeric" })}
                      </span>
                    </div>
                  </div>
                </button>
              </div>
            ))}
          </div>

          {/* Infinite scroll sentinel */}
          <div ref={sentinelRef} />
        </div>
      )}

      {/* Ad detail modal */}
      <AdDetailModal
        ad={selectedAd}
        open={detailOpen}
        onOpenChange={setDetailOpen}
      />

      {/* Add featured modal */}
      {isAdmin && (
        <AddFeaturedModal
          open={addModalOpen}
          onOpenChange={setAddModalOpen}
          onAdded={handleAdded}
        />
      )}
    </div>
  );
}

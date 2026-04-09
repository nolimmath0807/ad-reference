import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { ImageIcon, Film } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api-client";
import { AdDetailModal } from "@/components/ad/AdDetailModal";
import type { Ad } from "@/types/ad";

interface SharedBoardItem {
  id: string;
  ad_id: string;
  ad: Ad;
  added_at: string;
}

interface SharedBoard {
  id: string;
  name: string;
  description: string | null;
  owner_name: string;
  item_count: number;
  items: SharedBoardItem[];
  total: number;
}

function getImageUrl(url: string | null | undefined): string {
  if (!url) return "";
  if (url.startsWith("/static/")) {
    return `${import.meta.env.VITE_API_BASE_URL}${url}`;
  }
  return url;
}

function formatEngagement(value: number | null): string {
  if (!value) return "0";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

interface AdCardProps {
  item: SharedBoardItem;
  onClick: () => void;
}

function AdCard({ item, onClick }: AdCardProps) {
  const { ad } = item;
  const [imgError, setImgError] = useState(false);
  const thumbnailUrl = getImageUrl(ad.thumbnail_url);

  const totalEngagement =
    (ad.likes ?? 0) + (ad.comments ?? 0) + (ad.shares ?? 0);

  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex flex-col overflow-hidden rounded-lg border bg-card text-left shadow-xs transition-shadow hover:shadow-md"
    >
      {/* Thumbnail */}
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-muted">
        {!imgError && thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={ad.advertiser_name}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            {ad.media_type === "video" ? (
              <Film className="size-8 text-muted-foreground/40" />
            ) : (
              <ImageIcon className="size-8 text-muted-foreground/40" />
            )}
          </div>
        )}
        {ad.media_type === "video" && !imgError && thumbnailUrl && (
          <div className="absolute bottom-2 right-2 rounded bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white">
            VIDEO
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex flex-col gap-1 p-3">
        <p className="truncate text-sm font-medium leading-tight">
          {ad.brand_name || ad.advertiser_name}
        </p>
        {ad.ad_copy && (
          <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
            {ad.ad_copy}
          </p>
        )}
        {totalEngagement > 0 && (
          <p className="mt-1 text-xs text-muted-foreground">
            {formatEngagement(totalEngagement)} engagements
          </p>
        )}
      </div>
    </button>
  );
}

export function SharedBoardPage() {
  const { token } = useParams<{ token: string }>();
  const [board, setBoard] = useState<SharedBoard | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    api
      .get<SharedBoard>(`/shared/${token}`)
      .then((data) => {
        setBoard(data);
      })
      .catch(() => {
        setError("잘못된 링크이거나 만료된 공유 링크입니다.");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [token]);

  const handleAdClick = (ad: Ad) => {
    setSelectedAd(ad);
    setModalOpen(true);
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-40" />
        </div>
        <div className="grid gap-4 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="flex flex-col overflow-hidden rounded-lg border">
              <Skeleton className="aspect-[4/3] w-full" />
              <div className="flex flex-col gap-2 p-3">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-2/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error || !board) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 px-6 text-center">
        <p className="text-base font-medium text-foreground">
          {error || "잘못된 링크이거나 만료된 공유 링크입니다."}
        </p>
        <p className="text-sm text-muted-foreground">
          링크가 올바른지 확인하거나, 공유한 사람에게 다시 요청해주세요.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="mx-auto max-w-7xl px-6 py-10">
        {/* Header */}
        <div className="mb-8 flex flex-col gap-1.5">
          <h1 className="text-2xl font-bold tracking-tight">{board.name}</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>{board.owner_name}의 보드</span>
            <span>·</span>
            <span>광고 {board.item_count}개</span>
          </div>
          {board.description && (
            <p className="mt-1 text-sm text-muted-foreground">{board.description}</p>
          )}
        </div>

        {/* Grid */}
        {board.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24 text-center">
            <p className="text-sm text-muted-foreground">아직 저장된 광고가 없습니다.</p>
          </div>
        ) : (
          <div className="grid gap-4 grid-cols-[repeat(auto-fill,minmax(220px,1fr))]">
            {board.items.map((item) => (
              <AdCard
                key={item.id}
                item={item}
                onClick={() => handleAdClick(item.ad)}
              />
            ))}
          </div>
        )}
      </div>

      <AdDetailModal
        ad={selectedAd}
        open={modalOpen}
        onOpenChange={setModalOpen}
      />
    </>
  );
}

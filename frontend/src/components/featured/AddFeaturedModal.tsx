import { useState, useCallback } from "react";
import { Search, ImageOff } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { Ad, PlatformType } from "@/types/ad";

interface AddFeaturedModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAdded: () => void;
}

interface AdSearchResponse {
  items: Ad[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
}

const platformColors: Record<PlatformType, string> = {
  meta: "bg-blue-500/10 text-blue-600",
  google: "bg-green-500/10 text-green-600",
  tiktok: "bg-neutral-900/10 text-neutral-800",
};

function AdThumbnail({ url, alt }: { url: string | null; alt: string }) {
  const [imgError, setImgError] = useState(false);

  if (!url || imgError) {
    return (
      <div className="flex size-full items-center justify-center bg-muted">
        <ImageOff className="size-4 text-muted-foreground/40" />
      </div>
    );
  }

  return (
    <img
      src={url}
      alt={alt}
      onError={() => setImgError(true)}
      className="size-full object-cover"
    />
  );
}

export function AddFeaturedModal({ open, onOpenChange, onAdded }: AddFeaturedModalProps) {
  const [keyword, setKeyword] = useState("");
  const [results, setResults] = useState<Ad[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [memo, setMemo] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSearch = useCallback(async (value: string) => {
    if (!value.trim()) {
      setResults([]);
      return;
    }
    setIsSearching(true);
    const data = await api.get<AdSearchResponse>("/ads/search", {
      keyword: value.trim(),
      limit: 10,
    }).finally(() => setIsSearching(false));
    setResults(data.items);
  }, []);

  const handleKeywordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setKeyword(value);
    handleSearch(value);
  };

  const handleSelect = (ad: Ad) => {
    setSelectedAd(ad);
  };

  const handleSubmit = async () => {
    if (!selectedAd) return;
    setIsSubmitting(true);
    await api.post("/admin/featured-references", {
      ad_id: selectedAd.id,
      memo: memo.trim() || null,
    }).finally(() => setIsSubmitting(false));
    toast.success("추천 레퍼런스에 추가되었습니다.");
    onOpenChange(false);
    onAdded();
    setKeyword("");
    setResults([]);
    setSelectedAd(null);
    setMemo("");
  };

  const handleClose = (open: boolean) => {
    if (!open) {
      setKeyword("");
      setResults([]);
      setSelectedAd(null);
      setMemo("");
    }
    onOpenChange(open);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>추천 레퍼런스 추가</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Search input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="광고주명으로 검색..."
              value={keyword}
              onChange={handleKeywordChange}
              className="pl-9"
            />
          </div>

          {/* Search results */}
          {keyword.trim() && (
            <div className="max-h-60 overflow-y-auto rounded-lg border">
              {isSearching && (
                <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
                  검색 중...
                </div>
              )}
              {!isSearching && results.length === 0 && (
                <div className="flex items-center justify-center py-6 text-sm text-muted-foreground">
                  검색 결과가 없습니다.
                </div>
              )}
              {!isSearching && results.map((ad) => (
                <button
                  key={ad.id}
                  onClick={() => handleSelect(ad)}
                  className={`flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-muted/60 ${
                    selectedAd?.id === ad.id ? "bg-muted" : ""
                  }`}
                >
                  <div className="size-10 shrink-0 overflow-hidden rounded-md">
                    <AdThumbnail url={ad.thumbnail_url} alt={ad.advertiser_name} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{ad.advertiser_name}</p>
                    {ad.ad_copy && (
                      <p className="truncate text-xs text-muted-foreground">{ad.ad_copy}</p>
                    )}
                  </div>
                  <Badge
                    variant="secondary"
                    className={`shrink-0 text-[10px] uppercase ${platformColors[ad.platform] ?? ""}`}
                  >
                    {ad.platform}
                  </Badge>
                </button>
              ))}
            </div>
          )}

          {/* Selected ad */}
          {selectedAd && (
            <div className="rounded-lg border bg-muted/30 p-3">
              <p className="mb-1.5 text-xs font-medium text-muted-foreground">선택된 광고</p>
              <div className="flex items-center gap-3">
                <div className="size-10 shrink-0 overflow-hidden rounded-md">
                  <AdThumbnail url={selectedAd.thumbnail_url} alt={selectedAd.advertiser_name} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{selectedAd.advertiser_name}</p>
                  <Badge
                    variant="secondary"
                    className={`mt-0.5 text-[10px] uppercase ${platformColors[selectedAd.platform] ?? ""}`}
                  >
                    {selectedAd.platform}
                  </Badge>
                </div>
              </div>
            </div>
          )}

          {/* Memo input */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">메모 (선택)</label>
            <Input
              placeholder="추가 메모를 입력하세요..."
              value={memo}
              onChange={(e) => setMemo(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleClose(false)}>
            취소
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!selectedAd || isSubmitting}
          >
            {isSubmitting ? "추가 중..." : "추가"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

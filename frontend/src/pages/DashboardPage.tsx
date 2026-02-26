import { useState, useEffect, useCallback, useRef } from "react";
import { SearchBar } from "@/components/dashboard/SearchBar";
import { PlatformTabs } from "@/components/dashboard/PlatformTabs";
import { FilterBar } from "@/components/dashboard/FilterBar";
import { AdGrid } from "@/components/dashboard/AdGrid";
import { AdDetailModal } from "@/components/ad/AdDetailModal";
import { api } from "@/lib/api-client";
import type { Ad, AdSearchParams, AdSearchResponse, PlatformType, FormatType, SortType } from "@/types/ad";

const DEFAULT_PARAMS: AdSearchParams = {
  platform: "all",
  format: "all",
  sort: "recent",
  limit: 20,
};

export function DashboardPage() {
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [searchParams, setSearchParams] = useState<AdSearchParams>(DEFAULT_PARAMS);
  const [page, setPage] = useState(1);
  const [ads, setAds] = useState<Ad[]>([]);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);

  const requestIdRef = useRef(0);
  const loadingMoreRef = useRef(false);

  const fetchAds = useCallback(async (params: AdSearchParams, append = false) => {
    if (append) {
      if (loadingMoreRef.current) return;
      loadingMoreRef.current = true;
    } else {
      requestIdRef.current++;
    }
    const requestId = requestIdRef.current;

    setLoading(true);

    try {
      const data = await api.get<AdSearchResponse>("/ads/search", params as Record<string, string | number | boolean | undefined>);
      if (requestId !== requestIdRef.current) return;
      setAds((prev) => (append ? [...prev, ...data.items] : data.items));
      setHasNext(data.has_next);
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      console.error("Failed to fetch ads:", err);
      if (!append) setAds([]);
      setHasNext(false);
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
      if (append) {
        loadingMoreRef.current = false;
      }
    }
  }, []);

  useEffect(() => {
    setPage(1);
    fetchAds({ ...searchParams, page: 1 });
  }, [searchParams, fetchAds]);

  const updateParams = (updates: Partial<AdSearchParams>) => {
    setSearchParams((prev) => ({ ...prev, ...updates }));
  };

  const handleSearch = (keyword: string) => {
    updateParams({ keyword: keyword || undefined });
  };

  const handlePlatformChange = (platform: "all" | PlatformType) => {
    updateParams({ platform });
  };

  const handleFormatChange = (format: "all" | FormatType) => {
    updateParams({ format });
  };

  const handleSortChange = (sort: SortType) => {
    updateParams({ sort });
  };

  const handleDateFromChange = (date: string) => {
    updateParams({ date_from: date || undefined });
  };

  const handleDateToChange = (date: string) => {
    updateParams({ date_to: date || undefined });
  };

  const handleIndustryChange = (industry: string) => {
    updateParams({ industry: industry || undefined });
  };

  const handleClearFilters = () => {
    setSearchParams(DEFAULT_PARAMS);
  };

  const handleAdClick = (ad: Ad) => {
    setSelectedAd(ad);
  };

  const handleLoadMore = useCallback(() => {
    if (loadingMoreRef.current || !hasNext) return;
    const nextPage = page + 1;
    setPage(nextPage);
    fetchAds({ ...searchParams, page: nextPage }, true);
  }, [page, searchParams, hasNext, fetchAds]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Ad Library</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Search and discover ad creatives across platforms.
        </p>
      </div>

      <SearchBar onSearch={handleSearch} defaultValue={searchParams.keyword ?? ""} />

      <PlatformTabs
        activePlatform={searchParams.platform ?? "all"}
        onPlatformChange={handlePlatformChange}
      />

      <FilterBar
        format={searchParams.format ?? "all"}
        sort={searchParams.sort ?? "recent"}
        dateFrom={searchParams.date_from ?? ""}
        dateTo={searchParams.date_to ?? ""}
        industry={searchParams.industry ?? ""}
        onFormatChange={handleFormatChange}
        onSortChange={handleSortChange}
        onDateFromChange={handleDateFromChange}
        onDateToChange={handleDateToChange}
        onIndustryChange={handleIndustryChange}
        onClearFilters={handleClearFilters}
      />

      <AdGrid
        ads={ads}
        loading={loading}
        hasNext={hasNext}
        onAdClick={handleAdClick}
        onLoadMore={handleLoadMore}
      />

      <AdDetailModal
        ad={selectedAd}
        open={!!selectedAd}
        onOpenChange={(open) => {
          if (!open) setSelectedAd(null);
        }}
      />
    </div>
  );
}

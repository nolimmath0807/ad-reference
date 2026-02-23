import { useState, useEffect, useCallback } from "react";
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
  page: 1,
  limit: 20,
};

export function DashboardPage() {
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [searchParams, setSearchParams] = useState<AdSearchParams>(DEFAULT_PARAMS);
  const [ads, setAds] = useState<Ad[]>([]);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchAds = useCallback(async (params: AdSearchParams, append = false) => {
    try {
      setLoading(true);
      const data = await api.get<AdSearchResponse>("/ads/search", params as Record<string, string | number | boolean | undefined>);
      setAds((prev) => (append ? [...prev, ...data.items] : data.items));
      setHasNext(data.has_next);
    } catch (err) {
      console.error("Failed to fetch ads:", err);
      if (!append) setAds([]);
      setHasNext(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAds(searchParams);
  }, [searchParams, fetchAds]);

  const updateParams = (updates: Partial<AdSearchParams>) => {
    setSearchParams((prev) => ({ ...prev, ...updates, page: 1 }));
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

  const handleLoadMore = () => {
    const nextPage = (searchParams.page ?? 1) + 1;
    const nextParams = { ...searchParams, page: nextPage };
    setSearchParams(nextParams);
    fetchAds(nextParams, true);
  };

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

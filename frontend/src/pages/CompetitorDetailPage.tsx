import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SearchBar } from "@/components/dashboard/SearchBar";
import { PlatformTabs } from "@/components/dashboard/PlatformTabs";
import { FilterBar } from "@/components/dashboard/FilterBar";
import { AdGrid } from "@/components/dashboard/AdGrid";
import { AdDetailModal } from "@/components/ad/AdDetailModal";
import { api } from "@/lib/api-client";
import type { Ad, AdSearchParams, AdSearchResponse, PlatformType, FormatType, SortType } from "@/types/ad";
import type { CompetitorStats } from "@/types/competitor";

const platformColors: Record<string, string> = {
  google: "bg-red-500 text-white",
  meta: "bg-blue-500 text-white",
  tiktok: "bg-neutral-900 text-white",
  instagram: "bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 text-white",
  all: "bg-neutral-500 text-white",
};

const DEFAULT_PARAMS: AdSearchParams = {
  platform: "all",
  format: "all",
  sort: "recent",
  page: 1,
  limit: 20,
};

export function CompetitorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [stats, setStats] = useState<CompetitorStats | null>(null);
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [searchParams, setSearchParams] = useState<AdSearchParams>(DEFAULT_PARAMS);
  const [ads, setAds] = useState<Ad[]>([]);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fetch competitor stats
  useEffect(() => {
    if (!id) return;
    api.get<CompetitorStats>(`/monitored-domains/${id}/stats`).then(setStats);
  }, [id]);

  // Fetch competitor ads
  const fetchAds = useCallback(
    async (params: AdSearchParams, append = false) => {
      if (!id) return;
      setLoading(true);
      const data = await api.get<AdSearchResponse>(
        `/monitored-domains/${id}/ads`,
        params as Record<string, string | number | boolean | undefined>
      );
      setAds((prev) => (append ? [...prev, ...data.items] : data.items));
      setHasNext(data.has_next);
      setLoading(false);
    },
    [id]
  );

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

  const domain = stats?.domain_info;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate("/competitors")}
          className="mt-0.5 shrink-0"
        >
          <ArrowLeft className="size-4" />
        </Button>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">
              {domain?.domain ?? "Loading..."}
            </h1>
            {domain && (
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${platformColors[domain.platform] ?? platformColors.all}`}
              >
                {domain.platform}
              </span>
            )}
          </div>
          <div className="mt-1.5 flex items-center gap-4">
            {stats && (
              <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <Activity className="size-3.5" />
                <span className="font-medium text-foreground">{stats.total_ads}</span>
                total ads collected
              </div>
            )}
            {stats && stats.total_ads > 0 && (
              <div className="flex items-center gap-1.5">
                {Object.entries(stats.ads_by_format).map(([fmt, count]) => {
                  const isActive = searchParams.format === fmt;
                  return (
                    <Badge
                      key={fmt}
                      variant={isActive ? "default" : "outline"}
                      className={`cursor-pointer text-[10px] font-normal select-none transition-colors ${isActive ? "" : "hover:bg-accent hover:text-accent-foreground"}`}
                      onClick={() => handleFormatChange(isActive ? "all" : (fmt as FormatType))}
                    >
                      {fmt.charAt(0).toUpperCase() + fmt.slice(1)} {count}
                    </Badge>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Search + Filters (same as DashboardPage) */}
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

      {/* Ad grid (same as DashboardPage) */}
      <AdGrid
        ads={ads}
        loading={loading}
        hasNext={hasNext}
        onAdClick={handleAdClick}
        onLoadMore={handleLoadMore}
      />

      {/* Ad detail modal (same as DashboardPage) */}
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

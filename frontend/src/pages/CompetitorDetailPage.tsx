import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { ExternalLink, Pencil, Activity, ImageIcon, Play, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbSeparator,
  BreadcrumbPage,
} from "@/components/ui/breadcrumb";
import { SearchBar } from "@/components/dashboard/SearchBar";
import { FilterBar } from "@/components/dashboard/FilterBar";
import { AdGrid } from "@/components/dashboard/AdGrid";
import { AdDetailModal } from "@/components/ad/AdDetailModal";
import { EditBrandDialog } from "@/components/competitor/EditBrandDialog";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { Ad, AdSearchParams, AdSearchResponse, PlatformType, FormatType, SortType } from "@/types/ad";
import type { BrandStats } from "@/types/competitor";

const PLATFORM_COLORS: Record<string, string> = {
  google: "bg-blue-500/10 text-blue-600",
  meta: "bg-indigo-500/10 text-indigo-600",
  tiktok: "bg-neutral-900/10 text-neutral-800",
};

const PLATFORM_DOT_COLORS: Record<string, string> = {
  google: "bg-blue-500",
  meta: "bg-indigo-500",
  tiktok: "bg-neutral-800",
};

const FORMAT_COLORS: Record<string, string> = {
  image: "#8b5cf6",
  video: "#06b6d4",
  text: "#f59e0b",
};

const DEFAULT_PARAMS: AdSearchParams = {
  platform: "all",
  format: "all",
  sort: "recent",
  page: 1,
  limit: 20,
};

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  const diffMonths = Math.floor(diffDays / 30);
  return `${diffMonths}mo ago`;
}

export function CompetitorDetailPage() {
  const { id } = useParams<{ id: string }>();

  const [stats, setStats] = useState<BrandStats | null>(null);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [searchParams, setSearchParams] = useState<AdSearchParams>(DEFAULT_PARAMS);
  const [ads, setAds] = useState<Ad[]>([]);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);

  // Fetch brand stats
  useEffect(() => {
    if (!id) return;
    api.get<BrandStats>(`/brands/${id}/stats`).then(setStats);
  }, [id]);

  // Fetch brand ads
  const fetchAds = useCallback(
    async (params: AdSearchParams, append = false) => {
      if (!id) return;
      setLoading(true);
      const data = await api.get<AdSearchResponse>(
        `/brands/${id}/ads`,
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

  const brandName = stats?.brand.brand_name ?? "Loading...";
  const imageCount = stats?.ads_by_format?.image ?? 0;
  const videoCount = stats?.ads_by_format?.video ?? 0;
  const totalAds = stats?.total_ads ?? 0;

  const googleSource = stats?.sources.find(
    (s) => s.platform === "google" && s.source_type === "domain"
  );

  return (
    <div className="space-y-8">
      {/* Breadcrumb Navigation */}
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/competitors">Competitors</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{brandName}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      {/* Hero Section */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-violet-600/10 via-purple-600/10 to-indigo-600/10 border border-violet-500/20 p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{brandName}</h1>
              {stats?.brand.is_active && (
                <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600">
                  <span className="relative flex size-2">
                    <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex size-2 rounded-full bg-emerald-500" />
                  </span>
                  Active
                </span>
              )}
            </div>
            {/* Source badges */}
            {stats && stats.sources.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 mt-2">
                {stats.sources.map((source) => (
                  <Badge key={source.id} variant="outline" className="text-xs">
                    <span
                      className={`size-2 rounded-full mr-1.5 ${PLATFORM_DOT_COLORS[source.platform] ?? "bg-neutral-400"}`}
                    />
                    {source.platform === "google"
                      ? source.source_value
                      : `${source.platform}: ${source.source_value}`}
                  </Badge>
                ))}
              </div>
            )}
            {stats?.brand.notes && (
              <p className="text-sm text-muted-foreground">{stats.brand.notes}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowEditDialog(true)}>
              <Pencil className="size-3.5 mr-1.5" /> Edit
            </Button>
            {googleSource && (
              <Button variant="outline" size="sm" asChild>
                <a href={`https://${googleSource.source_value}`} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="size-3.5 mr-1.5" /> Visit site
                </a>
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Stats Dashboard */}
      {stats && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Total Ads */}
            <div className="rounded-2xl border bg-card/80 backdrop-blur-xl shadow-sm p-5 space-y-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Activity className="size-4" />
                <span className="text-xs font-medium">Total Ads</span>
              </div>
              <div className="text-2xl font-bold tabular-nums">{totalAds.toLocaleString()}</div>
            </div>

            {/* Image Ads */}
            <div className="rounded-2xl border bg-card/80 backdrop-blur-xl shadow-sm p-5 space-y-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <ImageIcon className="size-4" />
                <span className="text-xs font-medium">Image Ads</span>
              </div>
              <div className="text-2xl font-bold tabular-nums">{imageCount.toLocaleString()}</div>
              {totalAds > 0 && (
                <p className="text-xs text-muted-foreground">
                  {((imageCount / totalAds) * 100).toFixed(0)}% of total
                </p>
              )}
            </div>

            {/* Video Ads */}
            <div className="rounded-2xl border bg-card/80 backdrop-blur-xl shadow-sm p-5 space-y-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Play className="size-4" />
                <span className="text-xs font-medium">Video Ads</span>
              </div>
              <div className="text-2xl font-bold tabular-nums">{videoCount.toLocaleString()}</div>
              {totalAds > 0 && (
                <p className="text-xs text-muted-foreground">
                  {((videoCount / totalAds) * 100).toFixed(0)}% of total
                </p>
              )}
            </div>

            {/* Last Collected */}
            <div className="rounded-2xl border bg-card/80 backdrop-blur-xl shadow-sm p-5 space-y-2">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="size-4" />
                <span className="text-xs font-medium">Last Collected</span>
              </div>
              <div className="text-2xl font-bold tabular-nums">
                {formatRelativeTime(stats.last_collected_at)}
              </div>
            </div>
          </div>

          {/* Format Distribution Bar */}
          {totalAds > 0 && Object.keys(stats.ads_by_format).length > 0 && (
            <div>
              <div className="flex items-center gap-1 h-3 rounded-full overflow-hidden">
                {Object.entries(stats.ads_by_format).map(([format, count]) => (
                  <div
                    key={format}
                    style={{
                      width: `${(count / totalAds) * 100}%`,
                      backgroundColor: FORMAT_COLORS[format] ?? "#a3a3a3",
                    }}
                    className="h-full first:rounded-l-full last:rounded-r-full"
                  />
                ))}
              </div>
              <div className="flex items-center gap-4 mt-2">
                {Object.entries(stats.ads_by_format).map(([format, count]) => (
                  <div key={format} className="flex items-center gap-1.5 text-xs">
                    <span
                      className="size-2 rounded-full"
                      style={{ backgroundColor: FORMAT_COLORS[format] ?? "#a3a3a3" }}
                    />
                    <span className="capitalize">{format}</span>
                    <span className="text-muted-foreground">{count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Search */}
      <SearchBar onSearch={handleSearch} defaultValue={searchParams.keyword ?? ""} />

      {/* Platform Tabs with Count Badges */}
      {stats && (
        <div className="flex items-center gap-1 rounded-full bg-muted/50 p-1">
          {[
            { key: "all", label: "All", count: stats.total_ads },
            ...Object.entries(stats.ads_by_platform).map(([platform, count]) => ({
              key: platform,
              label: platform.charAt(0).toUpperCase() + platform.slice(1),
              count,
            })),
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => handlePlatformChange(tab.key as "all" | PlatformType)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
                searchParams.platform === tab.key
                  ? "bg-background shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label}
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[10px] tabular-nums",
                  searchParams.platform === tab.key
                    ? "bg-primary/10 text-primary"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      )}

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

      {/* Ad grid */}
      <AdGrid
        ads={ads}
        loading={loading}
        hasNext={hasNext}
        onAdClick={handleAdClick}
        onLoadMore={handleLoadMore}
      />

      {/* Edit brand dialog */}
      {stats && (
        <EditBrandDialog
          stats={stats}
          open={showEditDialog}
          onOpenChange={setShowEditDialog}
          onSuccess={() => {
            api.get<BrandStats>(`/brands/${id}/stats`).then(setStats);
          }}
        />
      )}

      {/* Ad detail modal */}
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

import { useState, useEffect, useCallback, useMemo } from "react";
import { Plus, Globe, Users, Activity, Zap, Pause } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CompetitorCard } from "@/components/competitor/CompetitorCard";
import { AddCompetitorDialog } from "@/components/competitor/AddCompetitorDialog";
import { api } from "@/lib/api-client";
import type { Brand, BrandStats } from "@/types/competitor";

type StatusFilter = "all" | "active" | "paused";
type SortOption = "recent" | "name" | "most-ads";

export function CompetitorsPage() {
  const [stats, setStats] = useState<BrandStats[]>([]);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [loading, setLoading] = useState(true);

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [platformFilter, setPlatformFilter] = useState("all");
  const [sortOption, setSortOption] = useState<SortOption>("recent");

  const fetchCompetitors = useCallback(async () => {
    setLoading(true);
    const res = await api.get<{ brands: { brand: Brand; sources: unknown[] }[] }>("/brands");
    const brands = res.brands;
    const statsPromises = brands.map((entry) =>
      api.get<BrandStats>(`/brands/${entry.brand.id}/stats`)
    );
    const allStats = await Promise.all(statsPromises);
    setStats(allStats);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchCompetitors();
  }, [fetchCompetitors]);

  const totalAds = useMemo(() => stats.reduce((sum, s) => sum + s.total_ads, 0), [stats]);
  const activeCount = useMemo(() => stats.filter((s) => s.brand.is_active).length, [stats]);
  const pausedCount = useMemo(() => stats.filter((s) => !s.brand.is_active).length, [stats]);

  const platforms = useMemo(() => {
    const set = new Set<string>();
    stats.forEach((s) => {
      s.sources.forEach((source) => set.add(source.platform));
    });
    return Array.from(set).sort();
  }, [stats]);

  const filteredStats = useMemo(() => {
    let result = [...stats];

    if (statusFilter === "active") {
      result = result.filter((s) => s.brand.is_active);
    } else if (statusFilter === "paused") {
      result = result.filter((s) => !s.brand.is_active);
    }

    if (platformFilter !== "all") {
      result = result.filter((s) =>
        s.sources.some((source) => source.platform === platformFilter)
      );
    }

    switch (sortOption) {
      case "name":
        result.sort((a, b) => a.brand.brand_name.localeCompare(b.brand.brand_name));
        break;
      case "most-ads":
        result.sort((a, b) => b.total_ads - a.total_ads);
        break;
      case "recent":
      default:
        result.sort((a, b) => {
          const dateA = a.brand.updated_at || a.brand.created_at;
          const dateB = b.brand.updated_at || b.brand.created_at;
          return new Date(dateB).getTime() - new Date(dateA).getTime();
        });
        break;
    }

    return result;
  }, [stats, statusFilter, platformFilter, sortOption]);

  const summaryCards = [
    { label: "Total Competitors", value: stats.length, icon: Users, color: "text-violet-500" },
    { label: "Total Ads Tracked", value: totalAds, icon: Activity, color: "text-cyan-500" },
    { label: "Active", value: activeCount, icon: Zap, color: "text-emerald-500" },
    { label: "Paused", value: pausedCount, icon: Pause, color: "text-amber-500" },
  ];

  const formatNumber = (n: number): string => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  };

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Competitors</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Monitor and analyze competitor ad strategies.
          </p>
        </div>
        <Button onClick={() => setShowAddDialog(true)}>
          <Plus />
          Add competitor
        </Button>
      </div>

      {/* Summary Stats Row */}
      {!loading && stats.length > 0 && (
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          {summaryCards.map((card) => (
            <div
              key={card.label}
              className="rounded-2xl border bg-card/80 p-5 shadow-sm backdrop-blur-xl"
            >
              <div className="flex items-center gap-3">
                <div className={`${card.color}`}>
                  <card.icon className="size-5" />
                </div>
                <div>
                  <p className="text-2xl font-bold tabular-nums">{formatNumber(card.value)}</p>
                  <p className="text-sm text-muted-foreground">{card.label}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Filter / View Controls */}
      {!loading && stats.length > 0 && (
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <Tabs
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as StatusFilter)}
          >
            <TabsList className="rounded-full bg-muted/50 p-1">
              <TabsTrigger value="all" className="rounded-full">
                All
              </TabsTrigger>
              <TabsTrigger value="active" className="rounded-full">
                Active ({activeCount})
              </TabsTrigger>
              <TabsTrigger value="paused" className="rounded-full">
                Paused ({pausedCount})
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="ml-auto flex items-center gap-3">
            <Select value={platformFilter} onValueChange={setPlatformFilter}>
              <SelectTrigger size="sm">
                <SelectValue placeholder="All Platforms" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Platforms</SelectItem>
                {platforms.map((p) => (
                  <SelectItem key={p} value={p} className="capitalize">
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sortOption} onValueChange={(v) => setSortOption(v as SortOption)}>
              <SelectTrigger size="sm">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recent">Recently Updated</SelectItem>
                <SelectItem value="name">Name A-Z</SelectItem>
                <SelectItem value="most-ads">Most Ads</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Competitor grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-[260px] animate-pulse rounded-2xl border bg-muted/30"
            />
          ))}
        </div>
      ) : filteredStats.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredStats.map((s) => (
            <CompetitorCard
              key={s.brand.id}
              stats={s}
              onDeleted={fetchCompetitors}
            />
          ))}

          {/* Add new competitor card */}
          <button
            onClick={() => setShowAddDialog(true)}
            className="flex h-full min-h-[260px] flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-muted-foreground/20 bg-card/80 backdrop-blur-xl transition-colors hover:border-muted-foreground/40 hover:bg-accent/50"
          >
            <div className="flex size-10 items-center justify-center rounded-full bg-muted">
              <Plus className="size-5 text-muted-foreground" />
            </div>
            <span className="text-sm font-medium text-muted-foreground">
              Add new competitor
            </span>
          </button>
        </div>
      ) : stats.length > 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-24">
          <Globe className="mb-4 size-12 text-muted-foreground/40" />
          <h3 className="text-lg font-semibold">No matches found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Try adjusting your filters to see more competitors.
          </p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => {
              setStatusFilter("all");
              setPlatformFilter("all");
            }}
          >
            Clear filters
          </Button>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-24">
          <Globe className="mb-4 size-12 text-muted-foreground/40" />
          <h3 className="text-lg font-semibold">No competitors monitored yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Add your first competitor to start monitoring their ad activity.
          </p>
          <Button className="mt-4" onClick={() => setShowAddDialog(true)}>
            <Plus />
            Add first competitor
          </Button>
        </div>
      )}

      <AddCompetitorDialog
        open={showAddDialog}
        onOpenChange={setShowAddDialog}
        onSuccess={fetchCompetitors}
      />
    </div>
  );
}

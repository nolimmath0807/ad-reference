import { useState, useEffect, useCallback } from "react";
import { Plus, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CompetitorCard } from "@/components/competitor/CompetitorCard";
import { AddCompetitorDialog } from "@/components/competitor/AddCompetitorDialog";
import { api } from "@/lib/api-client";
import type { MonitoredDomain, CompetitorStats } from "@/types/competitor";

export function CompetitorsPage() {
  const [stats, setStats] = useState<CompetitorStats[]>([]);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchCompetitors = useCallback(async () => {
    setLoading(true);
    const res = await api.get<{ domains: MonitoredDomain[] }>("/monitored-domains");
    const domains = res.domains;
    const statsPromises = domains.map((domain) =>
      api.get<CompetitorStats>(`/monitored-domains/${domain.id}/stats`)
    );
    const allStats = await Promise.all(statsPromises);
    setStats(allStats);
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchCompetitors();
  }, [fetchCompetitors]);

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

      {/* Competitor grid */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-[200px] animate-pulse rounded-xl border bg-muted/30"
            />
          ))}
        </div>
      ) : stats.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {stats.map((s) => (
            <CompetitorCard
              key={s.domain_info.id}
              stats={s}
              onDeleted={fetchCompetitors}
            />
          ))}

          {/* Add new competitor card */}
          <button
            onClick={() => setShowAddDialog(true)}
            className="flex h-full min-h-[200px] flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-muted-foreground/20 bg-card transition-colors hover:border-muted-foreground/40 hover:bg-accent/50"
          >
            <div className="flex size-10 items-center justify-center rounded-full bg-muted">
              <Plus className="size-5 text-muted-foreground" />
            </div>
            <span className="text-sm font-medium text-muted-foreground">
              Add new competitor
            </span>
          </button>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24">
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

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Bell,
  X,
  Download,
  TrendingUp,
  Settings,
  Loader2,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardAction, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api-client";
import { timeAgo } from "@/lib/utils";
import type { ActivityLog, ActivityLogsResponse } from "@/types/activity";

const EVENT_CONFIG = {
  collection: { icon: Download, color: "text-blue-500", bg: "bg-blue-500/10" },
  ad_change: { icon: TrendingUp, color: "text-green-500", bg: "bg-green-500/10" },
  system: { icon: Settings, color: "text-orange-500", bg: "bg-orange-500/10" },
} as const;

const FILTERS = [
  { label: "All", value: null },
  { label: "Collection", value: "collection" },
  { label: "Changes", value: "ad_change" },
] as const;

const PAGE_SIZE = 20;
const POLL_INTERVAL = 60_000;
const LAST_SEEN_KEY = "activity-last-seen";

function formatDateTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const MM = String(date.getMonth() + 1).padStart(2, "0");
  const DD = String(date.getDate()).padStart(2, "0");
  const HH = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  if (date.getFullYear() === now.getFullYear()) {
    return `${MM}/${DD} ${HH}:${mm}`;
  }
  return `${date.getFullYear()}/${MM}/${DD} ${HH}:${mm}`;
}

export function ActivityPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchLogs = useCallback(
    async (pageNum: number, append: boolean) => {
      setLoading(true);
      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        page: pageNum,
      };
      if (filter) {
        params.event_type = filter;
      }
      const data = await api.get<ActivityLogsResponse>("/activity-logs", params);
      setTotal(data.total);
      setLogs((prev) => (append ? [...prev, ...data.items] : data.items));
      setLoading(false);

      if (!append && data.items.length > 0) {
        updateUnreadCount(data.items);
      }
    },
    [filter],
  );

  const updateUnreadCount = (items: ActivityLog[]) => {
    const lastSeen = localStorage.getItem(LAST_SEEN_KEY);
    if (!lastSeen) {
      setUnreadCount(items.length);
      return;
    }
    const lastSeenTime = new Date(lastSeen).getTime();
    const unread = items.filter(
      (item) => new Date(item.created_at).getTime() > lastSeenTime,
    ).length;
    setUnreadCount(unread);
  };

  const markAsSeen = useCallback(() => {
    localStorage.setItem(LAST_SEEN_KEY, new Date().toISOString());
    setUnreadCount(0);
  }, []);

  const handleOpen = useCallback(() => {
    setIsOpen(true);
    markAsSeen();
  }, [markAsSeen]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, []);

  const handleFilterChange = useCallback((value: string | null) => {
    setFilter(value);
    setPage(1);
    setLogs([]);
  }, []);

  const handleLoadMore = useCallback(() => {
    const nextPage = page + 1;
    setPage(nextPage);
    fetchLogs(nextPage, true);
  }, [page, fetchLogs]);

  // Fetch on open and when filter changes
  useEffect(() => {
    if (isOpen) {
      fetchLogs(1, false);
    }
  }, [isOpen, filter, fetchLogs]);

  // Polling while open
  useEffect(() => {
    if (isOpen) {
      pollRef.current = setInterval(() => {
        fetchLogs(1, false);
      }, POLL_INTERVAL);
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [isOpen, fetchLogs]);

  // Initial unread count check
  useEffect(() => {
    api
      .get<ActivityLogsResponse>("/activity-logs", { limit: PAGE_SIZE, page: 1 })
      .then((data) => updateUnreadCount(data.items))
      .catch(() => {});
  }, []);

  const hasMore = logs.length < total;

  if (!isOpen) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <Button
          size="icon-lg"
          className="size-12 rounded-full shadow-lg"
          onClick={handleOpen}
        >
          <Bell className="size-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 size-5 p-0 text-[10px]"
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </Badge>
          )}
        </Button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <Card className="w-[400px] rounded-xl border shadow-2xl py-0">
        <CardHeader className="border-b px-4 py-3">
          <CardTitle className="text-sm">Activity</CardTitle>
          <CardAction>
            <Button variant="ghost" size="icon-xs" onClick={handleClose}>
              <X className="size-4" />
            </Button>
          </CardAction>
        </CardHeader>

        <div className="flex gap-1 border-b px-4 py-2">
          {FILTERS.map((f) => (
            <Button
              key={f.label}
              variant={filter === f.value ? "secondary" : "ghost"}
              size="xs"
              onClick={() => handleFilterChange(f.value)}
            >
              {f.label}
            </Button>
          ))}
        </div>

        <CardContent className="p-0">
          <ScrollArea className="max-h-[360px] overflow-auto">
            {logs.length === 0 && !loading && (
              <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                No activity yet
              </div>
            )}

            {logs.map((log, index) => {
              const config = EVENT_CONFIG[log.event_type];
              const Icon = config.icon;
              return (
                <div
                  key={log.id}
                  className={`flex items-start gap-3 px-4 py-3 ${
                    index < logs.length - 1 ? "border-b" : ""
                  }`}
                >
                  <div
                    className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full ${config.bg}`}
                  >
                    <Icon className={`size-3.5 ${config.color}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium leading-tight">
                      {log.title}
                    </p>
                    {log.message && (
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">
                        {log.message}
                      </p>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-xs text-muted-foreground">{timeAgo(log.created_at)}</p>
                    <p className="text-[10px] text-muted-foreground/60">{formatDateTime(log.created_at)}</p>
                  </div>
                </div>
              );
            })}

            {loading && (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="size-4 animate-spin text-muted-foreground" />
              </div>
            )}
          </ScrollArea>

          {hasMore && !loading && (
            <div className="border-t px-4 py-2">
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-xs"
                onClick={handleLoadMore}
              >
                Load more
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

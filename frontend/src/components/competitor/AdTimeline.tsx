import { useRef, useEffect, useMemo } from "react";
import {
  eachDayOfInterval,
  format,
  differenceInCalendarDays,
  differenceInDays,
  startOfDay,
  isToday,
  isSaturday,
  isSunday,
  parseISO,
} from "date-fns";
import { ko } from "date-fns/locale";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import type { TimelineAd } from "@/types/ad";

const COL_WIDTH = 40;
const ROW_HEIGHT = 60;
const LEFT_COL_WIDTH = 300;
const WEEKDAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

interface AdTimelineProps {
  items: TimelineAd[];
  dateRangeStart: string;
  dateRangeEnd: string;
  onAdClick?: (ad: TimelineAd) => void;
  loading?: boolean;
}

function getAdStatus(ad: TimelineAd): { active: boolean; days: number; effectiveEnd: Date } {
  const today = startOfDay(new Date());
  if (!ad.start_date) return { active: false, days: 0, effectiveEnd: today };
  const start = startOfDay(parseISO(ad.start_date));
  const end = ad.end_date ? startOfDay(parseISO(ad.end_date)) : today;

  // end_date(last_seen_at)가 1일 이내면 아직 게재중
  const daysSinceLastSeen = differenceInDays(today, end);
  const active = !ad.end_date || daysSinceLastSeen <= 1;

  // 게재 일수 = end_date - start_date + 1
  const effectiveEnd = active ? today : end;
  const days = differenceInDays(effectiveEnd, start) + 1;

  return { active, days: Math.max(days, 1), effectiveEnd };
}

export function AdTimeline({
  items,
  dateRangeStart,
  dateRangeEnd,
  onAdClick,
  loading,
}: AdTimelineProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const days = useMemo(() => {
    const start = parseISO(dateRangeStart);
    const end = parseISO(dateRangeEnd);
    return eachDayOfInterval({ start, end });
  }, [dateRangeStart, dateRangeEnd]);

  // Group days by month for the month header row
  const monthGroups = useMemo(() => {
    const groups: { label: string; span: number }[] = [];
    let currentLabel = "";
    let currentSpan = 0;

    for (const day of days) {
      const label = format(day, "yyyy년 M월", { locale: ko });
      if (label === currentLabel) {
        currentSpan++;
      } else {
        if (currentLabel) {
          groups.push({ label: currentLabel, span: currentSpan });
        }
        currentLabel = label;
        currentSpan = 1;
      }
    }
    if (currentLabel) {
      groups.push({ label: currentLabel, span: currentSpan });
    }
    return groups;
  }, [days]);

  // Auto-scroll to today on mount
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container || days.length === 0) return;

    const todayIndex = days.findIndex((d) => isToday(d));
    if (todayIndex >= 0) {
      const scrollTarget = todayIndex * COL_WIDTH - container.clientWidth / 2 + LEFT_COL_WIDTH;
      container.scrollLeft = Math.max(0, scrollTarget);
    }
  }, [days]);

  if (loading) {
    return (
      <div className="rounded-2xl border bg-card/80 backdrop-blur-xl shadow-sm overflow-hidden">
        <div className="p-4 space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="size-10 rounded-lg shrink-0" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-3.5 w-32" />
                <Skeleton className="h-3 w-24" />
              </div>
              <Skeleton className="h-6 flex-1 max-w-[400px] rounded-md" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="rounded-2xl border bg-card/80 backdrop-blur-xl shadow-sm p-12 text-center">
        <p className="text-muted-foreground text-sm">
          날짜 데이터가 있는 광고가 없습니다
        </p>
      </div>
    );
  }

  const totalGridWidth = days.length * COL_WIDTH;

  return (
    <div className="space-y-3">
      <div
        ref={scrollContainerRef}
        className="rounded-2xl border bg-card/80 backdrop-blur-xl shadow-sm overflow-auto max-h-[600px] relative"
      >
        <div
          className="relative"
          style={{ minWidth: LEFT_COL_WIDTH + totalGridWidth }}
        >
          {/* Sticky Header */}
          <div className="sticky top-0 z-20 bg-card border-b">
            {/* Month header row */}
            <div className="flex">
              <div
                className="sticky left-0 z-30 bg-card border-r shrink-0"
                style={{ width: LEFT_COL_WIDTH, minWidth: LEFT_COL_WIDTH }}
              />
              <div className="flex">
                {monthGroups.map((group, i) => (
                  <div
                    key={i}
                    className="text-xs font-semibold text-foreground border-r border-border/30 flex items-center px-2"
                    style={{ width: group.span * COL_WIDTH }}
                  >
                    {group.label}
                  </div>
                ))}
              </div>
            </div>

            {/* Weekday row */}
            <div className="flex">
              <div
                className="sticky left-0 z-30 bg-card border-r shrink-0"
                style={{ width: LEFT_COL_WIDTH, minWidth: LEFT_COL_WIDTH }}
              />
              <div className="flex">
                {days.map((day, i) => {
                  const dayOfWeek = day.getDay();
                  return (
                    <div
                      key={i}
                      className={cn(
                        "text-[10px] text-center border-r border-border/30",
                        isSunday(day) && "text-red-500",
                        isSaturday(day) && "text-blue-500",
                        !isSunday(day) && !isSaturday(day) && "text-muted-foreground"
                      )}
                      style={{ width: COL_WIDTH, minWidth: COL_WIDTH }}
                    >
                      {WEEKDAY_LABELS[dayOfWeek]}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Date number row */}
            <div className="flex border-b">
              <div
                className="sticky left-0 z-30 bg-card border-r shrink-0 flex items-center px-4"
                style={{ width: LEFT_COL_WIDTH, minWidth: LEFT_COL_WIDTH }}
              >
                <span className="text-xs font-medium text-muted-foreground">광고</span>
              </div>
              <div className="flex">
                {days.map((day, i) => {
                  const dateNum = day.getDate();
                  const today = isToday(day);
                  return (
                    <div
                      key={i}
                      className={cn(
                        "text-xs text-center border-r border-border/30 py-1 flex items-center justify-center",
                        isSunday(day) && !today && "text-red-500",
                        isSaturday(day) && !today && "text-blue-500",
                        !isSunday(day) && !isSaturday(day) && !today && "text-muted-foreground"
                      )}
                      style={{ width: COL_WIDTH, minWidth: COL_WIDTH }}
                    >
                      {today ? (
                        <span className="inline-flex items-center justify-center size-6 rounded-full bg-primary text-primary-foreground text-xs font-bold">
                          {dateNum}
                        </span>
                      ) : (
                        <span className={cn(
                          dateNum === 1 && "font-semibold"
                        )}>
                          {dateNum}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Body rows */}
          {items.map((ad) => {
            const { active, days: adDays, effectiveEnd } = getAdStatus(ad);
            const startDate = ad.start_date ? parseISO(ad.start_date) : null;
            const rangeStart = parseISO(dateRangeStart);
            const rangeEnd = parseISO(dateRangeEnd);
            const endDate = effectiveEnd;

            // Calculate bar position within the grid
            let barLeftIndex = 0;
            let barWidth = 0;

            if (startDate) {
              const clippedStart = startDate < rangeStart ? rangeStart : startDate;
              const clippedEnd = endDate > rangeEnd ? rangeEnd : endDate;

              barLeftIndex = differenceInCalendarDays(clippedStart, rangeStart);
              const barDays = differenceInCalendarDays(clippedEnd, clippedStart) + 1;
              barWidth = Math.max(barDays, 1);
            }

            return (
              <div
                key={ad.id}
                className="flex border-b border-border/30 hover:bg-muted/30 transition-colors cursor-pointer"
                style={{ height: ROW_HEIGHT }}
                onClick={() => onAdClick?.(ad)}
              >
                {/* Left column - ad info */}
                <div
                  className="sticky left-0 z-10 bg-card hover:bg-muted/30 border-r shrink-0 flex items-center gap-3 px-4"
                  style={{ width: LEFT_COL_WIDTH, minWidth: LEFT_COL_WIDTH }}
                >
                  {ad.thumbnail_url ? (
                    <img
                      src={ad.thumbnail_url}
                      alt=""
                      className="size-10 rounded-lg object-cover shrink-0"
                    />
                  ) : (
                    <div className="size-10 rounded-lg bg-muted shrink-0 flex items-center justify-center">
                      <span className="text-muted-foreground text-xs">N/A</span>
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">
                      {ad.ad_copy || ad.advertiser_name}
                    </p>
                    <p className="text-xs mt-0.5">
                      {active ? (
                        <span className="text-emerald-600">
                          게재중 · {adDays}일간 게재
                        </span>
                      ) : (
                        <span className="text-muted-foreground">
                          게재 종료 · {adDays}일간 게재
                        </span>
                      )}
                    </p>
                  </div>
                </div>

                {/* Right column - timeline bar */}
                <div className="relative flex-1">
                  {/* Grid lines */}
                  <div className="absolute inset-0 flex">
                    {days.map((day, i) => (
                      <div
                        key={i}
                        className={cn(
                          "border-r border-border/30 shrink-0",
                          isToday(day) && "bg-primary/5"
                        )}
                        style={{ width: COL_WIDTH, minWidth: COL_WIDTH }}
                      />
                    ))}
                  </div>

                  {/* Bar */}
                  {startDate && barWidth > 0 && (
                    <div
                      className={cn(
                        "absolute top-1/2 -translate-y-1/2 rounded-md flex items-center justify-center overflow-hidden",
                        active ? "bg-emerald-400" : "bg-neutral-300"
                      )}
                      style={{
                        left: barLeftIndex * COL_WIDTH + 2,
                        width: barWidth * COL_WIDTH - 4,
                        height: 28,
                      }}
                    >
                      {barWidth * COL_WIDTH - 4 > 30 && (
                        <span
                          className={cn(
                            "text-xs font-bold",
                            active ? "text-white" : "text-neutral-600"
                          )}
                        >
                          {adDays}일
                        </span>
                      )}
                      {/* Fade hint on the right edge for ongoing ads */}
                      {active && (
                        <div
                          className="absolute right-0 top-0 bottom-0 w-6 bg-gradient-to-r from-transparent to-emerald-300/60"
                        />
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 px-1">
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="size-2.5 rounded-full bg-emerald-400" />
          게재중
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="size-2.5 rounded-full bg-neutral-300" />
          종료
        </div>
      </div>
    </div>
  );
}

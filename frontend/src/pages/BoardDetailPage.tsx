import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { BoardHeader } from "@/components/board/BoardHeader";
import { BoardItemGrid } from "@/components/board/BoardItemGrid";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import type { BoardDetailResponse } from "@/types/board";
import type { Ad, PlatformType } from "@/types/ad";
import { AdDetailModal } from "@/components/ad/AdDetailModal";

type FilterTab = "all" | PlatformType;

const PLATFORM_TABS: { value: FilterTab; label: string }[] = [
  { value: "all", label: "All" },
  { value: "meta", label: "Meta" },
  { value: "google", label: "Google" },
  { value: "tiktok", label: "TikTok" },
];

export function BoardDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [board, setBoard] = useState<BoardDetailResponse | null>(null);
  const [activeTab, setActiveTab] = useState<FilterTab>("all");
  const [selectedAd, setSelectedAd] = useState<Ad | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchBoard = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.get<BoardDetailResponse>(`/boards/${id}`, {
        page: 1,
        limit: 50,
      });
      setBoard(data);
    } catch (err: unknown) {
      const message =
        typeof err === "object" && err !== null && "error" in err
          ? (err as { error?: { message?: string } }).error?.message
          : undefined;
      setError(message || "보드를 불러올 수 없습니다.");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchBoard();
  }, [fetchBoard]);

  const filteredItems = useMemo(() => {
    if (!board) return [];
    if (activeTab === "all") return board.items;
    return board.items.filter((item) => item.ad.platform === activeTab);
  }, [board, activeTab]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !board) {
    return (
      <div className="mx-auto w-full px-6 py-8">
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24">
          <p className="text-sm text-muted-foreground">{error || "보드를 찾을 수 없습니다."}</p>
          <Button variant="outline" className="mt-4" asChild>
            <Link to="/boards">보드 목록으로 돌아가기</Link>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full px-6 py-8">
      <BoardHeader board={board} />

      <div className="mt-6">
        <Tabs
          value={activeTab}
          onValueChange={(v) => setActiveTab(v as FilterTab)}
        >
          <TabsList variant="line">
            {PLATFORM_TABS.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {PLATFORM_TABS.map((tab) => (
            <TabsContent key={tab.value} value={tab.value} className="mt-6">
              <BoardItemGrid
                boardId={id!}
                items={filteredItems}
                onItemRemoved={fetchBoard}
                onAdClick={(ad) => setSelectedAd(ad)}
              />
            </TabsContent>
          ))}
        </Tabs>
      </div>

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

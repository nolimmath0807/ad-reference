import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams } from "react-router-dom";
import { BoardHeader } from "@/components/board/BoardHeader";
import { BoardItemGrid } from "@/components/board/BoardItemGrid";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { api } from "@/lib/api-client";
import type { BoardDetailResponse } from "@/types/board";
import type { PlatformType } from "@/types/ad";

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

  const fetchBoard = useCallback(async () => {
    if (!id) return;
    const data = await api.get<BoardDetailResponse>(`/boards/${id}`, {
      page: 1,
      limit: 100,
    });
    setBoard(data);
  }, [id]);

  useEffect(() => {
    fetchBoard();
  }, [fetchBoard]);

  const filteredItems = useMemo(() => {
    if (!board) return [];
    if (activeTab === "all") return board.items;
    return board.items.filter((item) => item.ad.platform === activeTab);
  }, [board, activeTab]);

  if (!board) return null;

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
              />
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </div>
  );
}

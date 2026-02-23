import { useState, useEffect, useCallback } from "react";
import { Plus, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BoardCard } from "@/components/board/BoardCard";
import { CreateBoardDialog } from "@/components/board/CreateBoardDialog";
import { api } from "@/lib/api-client";
import type { BoardListResponse } from "@/types/board";

export function BoardsPage() {
  const [boards, setBoards] = useState<BoardListResponse | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const fetchBoards = useCallback(async () => {
    const data = await api.get<BoardListResponse>("/boards", { page: 1, limit: 50 });
    setBoards(data);
  }, []);

  useEffect(() => {
    fetchBoards();
  }, [fetchBoards]);

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">My Boards</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Organize and manage your saved ads.
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus />
          New board
        </Button>
      </div>

      {/* Board grid */}
      {boards && boards.items.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {boards.items.map((board) => (
            <BoardCard key={board.id} board={board} onDeleted={fetchBoards} />
          ))}

          {/* Create new board card */}
          <button
            onClick={() => setShowCreateDialog(true)}
            className="flex aspect-[16/10] flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-muted-foreground/20 bg-card transition-colors hover:border-muted-foreground/40 hover:bg-accent/50"
          >
            <div className="flex size-10 items-center justify-center rounded-full bg-muted">
              <Plus className="size-5 text-muted-foreground" />
            </div>
            <span className="text-sm font-medium text-muted-foreground">
              Create new board
            </span>
          </button>
        </div>
      ) : boards && boards.items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24">
          <FolderOpen className="mb-4 size-12 text-muted-foreground/40" />
          <h3 className="text-lg font-semibold">No boards yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Create your first board to start organizing ads.
          </p>
          <Button className="mt-4" onClick={() => setShowCreateDialog(true)}>
            <Plus />
            Create first board
          </Button>
        </div>
      ) : null}

      <CreateBoardDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onCreated={fetchBoards}
      />
    </div>
  );
}

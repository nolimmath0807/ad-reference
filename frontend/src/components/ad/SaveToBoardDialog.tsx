import { useState, useEffect } from "react";
import { Plus, FolderOpen, Check, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { Board, BoardListResponse, BoardCreateRequest } from "@/types/board";

interface SaveToBoardDialogProps {
  adId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved?: () => void;
}

export function SaveToBoardDialog({ adId, open, onOpenChange, onSaved }: SaveToBoardDialogProps) {
  const [boards, setBoards] = useState<Board[]>([]);
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showNewBoard, setShowNewBoard] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    if (open) {
      setSelectedBoardId(null);
      setShowNewBoard(false);
      setNewBoardName("");
      fetchBoards();
    }
  }, [open]);

  const fetchBoards = async () => {
    setIsLoading(true);
    const data = await api.get<BoardListResponse>("/boards", { page: 1, limit: 50 });
    setBoards(data.items);
    setIsLoading(false);
  };

  const handleSave = async () => {
    if (!selectedBoardId) return;
    setIsSaving(true);
    await api.post(`/boards/${selectedBoardId}/items`, { ad_id: adId });
    toast.success("Ad saved to board.");
    setIsSaving(false);
    onOpenChange(false);
    onSaved?.();
  };

  const handleCreateBoard = async () => {
    if (!newBoardName.trim()) return;
    setIsCreating(true);
    const created = await api.post<Board>("/boards", {
      name: newBoardName.trim(),
    } satisfies BoardCreateRequest);
    setBoards((prev) => [created, ...prev]);
    setSelectedBoardId(created.id);
    setShowNewBoard(false);
    setNewBoardName("");
    setIsCreating(false);
    toast.success("Board created.");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Save to Board</DialogTitle>
          <DialogDescription>
            Choose a board to save this ad, or create a new one.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          {/* Board list */}
          <ScrollArea className="max-h-[280px]">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="size-5 animate-spin text-muted-foreground" />
              </div>
            ) : boards.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <FolderOpen className="size-8 text-muted-foreground/40" />
                <p className="text-sm text-muted-foreground">No boards yet</p>
              </div>
            ) : (
              <div className="flex flex-col gap-1">
                {boards.map((board) => (
                  <button
                    key={board.id}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors",
                      selectedBoardId === board.id
                        ? "bg-brand-primary/10 ring-1 ring-brand-primary/30"
                        : "hover:bg-muted"
                    )}
                    onClick={() => setSelectedBoardId(board.id)}
                  >
                    <div className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted">
                      {board.cover_image_url ? (
                        <img
                          src={board.cover_image_url}
                          alt={board.name}
                          className="size-full rounded-md object-cover"
                        />
                      ) : (
                        <FolderOpen className="size-4 text-muted-foreground" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{board.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {board.item_count} {board.item_count === 1 ? "item" : "items"}
                      </p>
                    </div>
                    {selectedBoardId === board.id && (
                      <Check className="size-4 shrink-0 text-brand-primary" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </ScrollArea>

          <Separator />

          {/* Create new board */}
          {showNewBoard ? (
            <div className="flex items-center gap-2">
              <Input
                placeholder="Board name"
                value={newBoardName}
                onChange={(e) => setNewBoardName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreateBoard();
                }}
                autoFocus
              />
              <Button
                size="sm"
                onClick={handleCreateBoard}
                disabled={!newBoardName.trim() || isCreating}
              >
                {isCreating ? <Loader2 className="size-4 animate-spin" /> : "Create"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setShowNewBoard(false);
                  setNewBoardName("");
                }}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={() => setShowNewBoard(true)}
            >
              <Plus className="size-4" />
              New Board
            </Button>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!selectedBoardId || isSaving}
            className="bg-brand-primary text-brand-primary-foreground hover:bg-brand-primary/90"
          >
            {isSaving ? <Loader2 className="size-4 animate-spin" /> : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";
import { MoreHorizontal, Pencil, Trash2, FolderOpen, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { Board, BoardUpdateRequest } from "@/types/board";

interface BoardCardProps {
  board: Board;
  onDeleted: () => void;
  onUpdated: () => void;
}

export function BoardCard({ board, onDeleted, onUpdated }: BoardCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editForm, setEditForm] = useState<BoardUpdateRequest>({
    name: board.name,
    description: board.description || "",
  });
  const [isUpdating, setIsUpdating] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.delete(`/boards/${board.id}`);
      toast.success("Board deleted successfully.");
      setShowDeleteDialog(false);
      onDeleted();
    } catch (err: any) {
      toast.error(err?.error?.message || "삭제에 실패했습니다.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdating(true);
    try {
      await api.put<Board>(`/boards/${board.id}`, {
        name: editForm.name,
        description: editForm.description || undefined,
      });
      toast.success("Board updated successfully.");
      setShowEditDialog(false);
      onUpdated();
    } catch (err: any) {
      toast.error(err?.error?.message || "수정에 실패했습니다.");
    } finally {
      setIsUpdating(false);
    }
  };

  const openEditDialog = () => {
    setEditForm({
      name: board.name,
      description: board.description || "",
    });
    setShowEditDialog(true);
  };

  const updatedAt = new Date(board.updated_at).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <>
      <Link to={`/boards/${board.id}`} className="group block">
        <Card className="overflow-hidden transition-shadow hover:shadow-md">
          <div className="relative h-40 bg-muted">
            {board.cover_image_url ? (
              <img
                src={board.cover_image_url}
                alt={board.name}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full w-full items-center justify-center">
                <FolderOpen className="size-10 text-muted-foreground/40" />
              </div>
            )}
            <div className="absolute right-2 top-2 opacity-0 transition-opacity group-hover:opacity-100">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="secondary"
                    size="icon-xs"
                    className="shadow-sm"
                    onClick={(e) => e.preventDefault()}
                  >
                    <MoreHorizontal className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onClick={(e) => {
                      e.preventDefault();
                      openEditDialog();
                    }}
                  >
                    <Pencil />
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    variant="destructive"
                    onClick={(e) => {
                      e.preventDefault();
                      setShowDeleteDialog(true);
                    }}
                  >
                    <Trash2 />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
          <div className="flex flex-col gap-1 px-4 py-3">
            <h3 className="truncate text-sm font-semibold">{board.name}</h3>
            <div className="flex items-center justify-between">
              <Badge variant="secondary" className="text-xs">
                {board.item_count} items
              </Badge>
              <span className="text-xs text-muted-foreground">{updatedAt}</span>
            </div>
          </div>
        </Card>
      </Link>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete board</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{board.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <form onSubmit={handleEdit}>
            <DialogHeader>
              <DialogTitle>Edit board</DialogTitle>
              <DialogDescription>
                Update the name or description of this board.
              </DialogDescription>
            </DialogHeader>

            <div className="mt-4 flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <Label htmlFor={`edit-board-name-${board.id}`}>Name</Label>
                <Input
                  id={`edit-board-name-${board.id}`}
                  placeholder="e.g. Campaign Inspiration"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  required
                />
              </div>

              <div className="flex flex-col gap-2">
                <Label htmlFor={`edit-board-description-${board.id}`}>Description (optional)</Label>
                <textarea
                  id={`edit-board-description-${board.id}`}
                  placeholder="What is this board about?"
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  rows={3}
                  className="border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 w-full rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-[3px]"
                />
              </div>
            </div>

            <DialogFooter className="mt-6">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowEditDialog(false)}
                disabled={isUpdating}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isUpdating || !editForm.name?.trim()}>
                {isUpdating && <Loader2 className="animate-spin" />}
                Save
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";
import { MoreHorizontal, Pencil, Trash2, FolderOpen } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { Board } from "@/types/board";

interface BoardCardProps {
  board: Board;
  onDeleted: () => void;
}

export function BoardCard({ board, onDeleted }: BoardCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    await api.delete(`/boards/${board.id}`);
    toast.success("Board deleted successfully.");
    setIsDeleting(false);
    setShowDeleteDialog(false);
    onDeleted();
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
          <div className="relative aspect-[16/10] bg-muted">
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
    </>
  );
}

import { useState } from "react";
import { ExternalLink, Trash2, Heart, MessageCircle, Share2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import type { BoardItem } from "@/types/board";

interface BoardItemGridProps {
  boardId: string;
  items: BoardItem[];
  onItemRemoved: () => void;
}

function InlineAdCard({
  item,
  onRemove,
}: {
  item: BoardItem;
  onRemove: () => void;
}) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const ad = item.ad;

  const handleDelete = async () => {
    setIsDeleting(true);
    onRemove();
    setIsDeleting(false);
    setShowDeleteDialog(false);
  };

  const platformColors: Record<string, string> = {
    meta: "bg-blue-100 text-blue-700",
    google: "bg-green-100 text-green-700",
    tiktok: "bg-pink-100 text-pink-700",
    instagram: "bg-purple-100 text-purple-700",
  };

  return (
    <>
      <Card className="group overflow-hidden transition-shadow hover:shadow-md">
        <div className="relative aspect-[4/3] bg-muted">
          <img
            src={ad.thumbnail_url}
            alt={ad.advertiser_name}
            className="h-full w-full object-cover"
          />
          <div className="absolute left-2 top-2">
            <Badge className={platformColors[ad.platform] || "bg-muted text-foreground"}>
              {ad.platform}
            </Badge>
          </div>
          <div className="absolute right-2 top-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100">
            {ad.landing_page_url && (
              <Button
                variant="secondary"
                size="icon-xs"
                className="shadow-sm"
                asChild
              >
                <a href={ad.landing_page_url} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="size-3" />
                </a>
              </Button>
            )}
            <Button
              variant="destructive"
              size="icon-xs"
              className="shadow-sm"
              onClick={() => setShowDeleteDialog(true)}
            >
              <Trash2 className="size-3" />
            </Button>
          </div>
        </div>

        <div className="flex flex-col gap-2 px-4 py-3">
          <div className="flex items-center gap-2">
            {ad.advertiser_avatar_url && (
              <img
                src={ad.advertiser_avatar_url}
                alt=""
                className="size-5 rounded-full"
              />
            )}
            <span className="truncate text-sm font-medium">{ad.advertiser_name}</span>
          </div>

          {ad.ad_copy && (
            <p className="line-clamp-2 text-xs text-muted-foreground">{ad.ad_copy}</p>
          )}

          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {ad.likes !== null && (
              <span className="flex items-center gap-1">
                <Heart className="size-3" /> {ad.likes.toLocaleString()}
              </span>
            )}
            {ad.comments !== null && (
              <span className="flex items-center gap-1">
                <MessageCircle className="size-3" /> {ad.comments.toLocaleString()}
              </span>
            )}
            {ad.shares !== null && (
              <span className="flex items-center gap-1">
                <Share2 className="size-3" /> {ad.shares.toLocaleString()}
              </span>
            )}
          </div>

          <Badge variant="outline" className="w-fit text-xs">
            {ad.format}
          </Badge>
        </div>
      </Card>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove from board</AlertDialogTitle>
            <AlertDialogDescription>
              Remove this ad from the board? The ad itself will not be deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export function BoardItemGrid({ boardId, items, onItemRemoved }: BoardItemGridProps) {
  const handleRemoveItem = async (itemId: string) => {
    await api.delete(`/boards/${boardId}/items/${itemId}`);
    toast.success("Ad removed from board.");
    onItemRemoved();
  };

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-sm text-muted-foreground">No ads saved in this board yet.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Browse ads and save them to this board.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {items.map((item) => (
        <InlineAdCard
          key={item.id}
          item={item}
          onRemove={() => handleRemoveItem(item.id)}
        />
      ))}
    </div>
  );
}

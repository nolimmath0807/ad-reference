import { Link } from "react-router-dom";
import { Share2, Download, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import type { BoardDetailResponse } from "@/types/board";

interface BoardHeaderProps {
  board: BoardDetailResponse;
}

export function BoardHeader({ board }: BoardHeaderProps) {
  const updatedAt = new Date(board.updated_at).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    toast.success("Link copied to clipboard.");
  };

  const handleExport = () => {
    toast.info("Export feature coming soon.");
  };

  return (
    <div className="flex flex-col gap-4">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link to="/boards">Boards</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{board.name}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-bold tracking-tight">{board.name}</h1>
          {board.description && (
            <p className="text-sm text-muted-foreground">{board.description}</p>
          )}
          <div className="flex items-center gap-3">
            <Badge variant="secondary">{board.item_count} ads</Badge>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Calendar className="size-3" />
              <span>Updated {updatedAt}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleShare}>
            <Share2 />
            Share
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download />
            Export
          </Button>
        </div>
      </div>

      <Separator />
    </div>
  );
}

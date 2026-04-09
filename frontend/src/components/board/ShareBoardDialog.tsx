import { useState } from "react";
import { Link2, Copy, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api-client";
import { toast } from "sonner";

interface ShareBoardDialogProps {
  boardId: string;
  shareToken: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onShareChange: (token: string | null) => void;
}

export function ShareBoardDialog({
  boardId,
  shareToken,
  open,
  onOpenChange,
  onShareChange,
}: ShareBoardDialogProps) {
  const [isLoading, setIsLoading] = useState(false);

  const shareUrl = shareToken
    ? `${window.location.origin}/shared/${shareToken}`
    : null;

  const handleCreateLink = async () => {
    setIsLoading(true);
    const data = await api.post<{ share_token: string }>(`/boards/${boardId}/share`);
    onShareChange(data.share_token);
    setIsLoading(false);
  };

  const handleRevokeLink = async () => {
    setIsLoading(true);
    await api.delete(`/boards/${boardId}/share`);
    onShareChange(null);
    setIsLoading(false);
  };

  const handleCopy = () => {
    if (!shareUrl) return;
    navigator.clipboard.writeText(shareUrl);
    toast.success("링크가 복사되었습니다.");
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>보드 공유</DialogTitle>
          <DialogDescription>
            {shareToken
              ? "아래 링크를 통해 누구든지 이 보드를 볼 수 있습니다."
              : "이 보드를 팀원과 공유하세요."}
          </DialogDescription>
        </DialogHeader>

        <div className="mt-2">
          {shareToken ? (
            <div className="flex items-center gap-2">
              <Input
                value={shareUrl ?? ""}
                readOnly
                className="flex-1 text-sm text-muted-foreground"
              />
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={handleCopy}
                title="링크 복사"
              >
                <Copy className="size-4" />
              </Button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed py-8 text-center">
              <Link2 className="size-8 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                공유 링크가 생성되면 누구나 이 보드를 볼 수 있습니다.
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="mt-4 flex-col gap-2 sm:flex-row">
          {shareToken ? (
            <>
              <Button
                type="button"
                variant="destructive"
                onClick={handleRevokeLink}
                disabled={isLoading}
                className="w-full sm:w-auto"
              >
                {isLoading && <Loader2 className="animate-spin" />}
                공유 중단
              </Button>
              <Button
                type="button"
                onClick={handleCopy}
                className="w-full sm:w-auto"
              >
                <Copy className="size-4" />
                링크 복사
              </Button>
            </>
          ) : (
            <Button
              type="button"
              onClick={handleCreateLink}
              disabled={isLoading}
              className="w-full sm:w-auto"
            >
              {isLoading ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Link2 className="size-4" />
              )}
              링크 생성
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

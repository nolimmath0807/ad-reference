import { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/contexts/AuthContext";
import type { Comment, CommentListResponse } from "@/types/comment";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { X } from "lucide-react";

interface AdCommentsProps {
  adId: string;
}

export function AdComments({ adId }: AdCommentsProps) {
  const { user } = useAuth();
  const [comments, setComments] = useState<Comment[]>([]);
  const [total, setTotal] = useState(0);
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const loadComments = async () => {
    const data = await api.get<CommentListResponse>(`/ads/${adId}/comments`);
    setComments(data.items);
    setTotal(data.total);
  };

  useEffect(() => {
    loadComments();
  }, [adId]);

  const handleSubmit = async () => {
    if (isSubmitting) return;
    const trimmed = content.trim();
    if (!trimmed) return;

    setIsSubmitting(true);
    await api.post(`/ads/${adId}/comments`, { content: trimmed });
    setContent("");
    await loadComments();
    setIsSubmitting(false);
    toast.success("댓글이 등록되었습니다.");
  };

  const handleDelete = async (commentId: string) => {
    // optimistic update: 즉시 로컬에서 제거
    setComments(prev => prev.filter(c => c.id !== commentId));
    setTotal(prev => prev - 1);
    try {
      await api.delete(`/ads/${adId}/comments/${commentId}`);
      toast.success("댓글이 삭제되었습니다.");
    } catch {
      // 실패 시 원복
      await loadComments();
      toast.error("삭제에 실패했습니다.");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString("ko-KR", { month: "short", day: "numeric" });

  const getInitials = (name: string) =>
    name
      .split(" ")
      .map((part) => part[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);

  const canDelete = (comment: Comment) =>
    !!user && (user.id === comment.user_id || user.role === "admin");

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm font-medium text-foreground">댓글 {total}개</p>

      <Separator />

      {comments.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">
          아직 댓글이 없습니다. 첫 댓글을 남겨보세요.
        </p>
      ) : (
        <div className="flex flex-col gap-4">
          {comments.map((comment) => (
            <div key={comment.id} className="flex gap-3">
              <Avatar className="h-8 w-8 shrink-0">
                {comment.user_avatar_url && (
                  <AvatarImage src={comment.user_avatar_url} alt={comment.user_name} />
                )}
                <AvatarFallback className="text-xs">
                  {getInitials(comment.user_name)}
                </AvatarFallback>
              </Avatar>

              <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium leading-none">{comment.user_name}</span>
                  <span className="text-xs text-muted-foreground">{formatDate(comment.created_at)}</span>
                </div>
                <p className="text-sm text-foreground break-words whitespace-pre-wrap">
                  {comment.content}
                </p>
              </div>

              {canDelete(comment) && (
                <button
                  onClick={() => handleDelete(comment.id)}
                  className="shrink-0 self-start rounded p-0.5 text-muted-foreground transition-colors hover:text-destructive"
                  aria-label="댓글 삭제"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <Separator />

      <div className="flex flex-col gap-2">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="댓글을 남겨보세요..."
          rows={2}
          className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <div className="flex justify-end">
          <Button
            size="sm"
            onClick={handleSubmit}
            disabled={isSubmitting || !content.trim()}
          >
            작성
          </Button>
        </div>
      </div>
    </div>
  );
}

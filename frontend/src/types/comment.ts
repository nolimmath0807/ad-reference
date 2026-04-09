export interface Comment {
  id: string;
  ad_id: string;
  user_id: string;
  user_name: string;
  user_avatar_url: string | null;
  content: string;
  created_at: string;
}

export interface CommentListResponse {
  items: Comment[];
  total: number;
}

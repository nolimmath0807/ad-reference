import type { Ad } from "./ad";

export interface Board {
  id: string;
  name: string;
  description: string | null;
  cover_image_url: string | null;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface BoardCreateRequest {
  name: string;
  description?: string;
}

export interface BoardItem {
  id: string;
  board_id: string;
  ad_id: string;
  ad: Ad;
  added_at: string;
}

export interface BoardItemAddRequest {
  ad_id: string;
}

export interface BoardListResponse {
  items: Board[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
}

export interface BoardDetailResponse {
  id: string;
  name: string;
  description: string | null;
  cover_image_url: string | null;
  item_count: number;
  created_at: string;
  updated_at: string;
  items: BoardItem[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
}

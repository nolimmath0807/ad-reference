export type PlatformType = "meta" | "google" | "tiktok";
export type FormatType = "image" | "video" | "carousel" | "reels" | "text";
export type MediaType = "image" | "video" | "text";
export type SortType = "recent" | "popular" | "engagement";

export interface Ad {
  id: string;
  platform: PlatformType;
  format: FormatType;
  advertiser_name: string;
  advertiser_handle: string | null;
  advertiser_avatar_url: string | null;
  thumbnail_url: string;
  preview_url: string | null;
  media_type: MediaType;
  ad_copy: string | null;
  cta_text: string | null;
  likes: number | null;
  comments: number | null;
  shares: number | null;
  start_date: string | null;
  end_date: string | null;
  tags: string[];
  landing_page_url: string | null;
  created_at: string;
  saved_at: string | null;
}

export interface AdSearchParams {
  keyword?: string;
  platform?: "all" | PlatformType;
  format?: "all" | FormatType;
  sort?: SortType;
  date_from?: string;
  date_to?: string;
  industry?: string;
  page?: number;
  limit?: number;
}

export interface AdSearchResponse {
  items: Ad[];
  total: number;
  page: number;
  limit: number;
  has_next: boolean;
}

export interface AdDetailResponse {
  ad: Ad;
  similar_ads: Ad[];
}

export interface TimelineAd {
  id: string;
  advertiser_name: string;
  thumbnail_url: string | null;
  platform: PlatformType;
  format: FormatType;
  media_type: MediaType;
  start_date: string | null;
  end_date: string | null;
  ad_copy: string | null;
}

export interface TimelineResponse {
  items: TimelineAd[];
  date_range_start: string;
  date_range_end: string;
  total: number;
}

export interface AdSaveRequest {
  platform: PlatformType;
  format: FormatType;
  advertiser_name: string;
  advertiser_handle?: string;
  advertiser_avatar_url?: string;
  thumbnail_url: string;
  preview_url?: string;
  media_type: MediaType;
  ad_copy?: string;
  cta_text?: string;
  likes?: number;
  comments?: number;
  shares?: number;
  start_date?: string;
  end_date?: string;
  tags?: string[];
  landing_page_url?: string;
}

export interface AdScriptResponse {
  ad_id: string;
  script_text: string | null;
  status: "pending" | "processing" | "completed" | "failed" | "not_found";
  error_message: string | null;
}

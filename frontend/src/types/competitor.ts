export interface MonitoredDomain {
  id: string;
  domain: string;
  platform: string;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompetitorStats {
  domain_info: MonitoredDomain;
  total_ads: number;
  ads_by_format: Record<string, number>;
  ads_by_platform: Record<string, number>;
  last_collected_at: string | null;
}

export interface MonitoredDomainCreateRequest {
  domain: string;
  platform?: string;
  notes?: string;
}

export interface Brand {
  id: string;
  brand_name: string;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface BrandSource {
  id: string;
  brand_id: string;
  platform: string;        // 'google' | 'meta' | 'tiktok'
  source_type: string;     // 'domain' | 'keyword' | 'page_id'
  source_value: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BrandStats {
  brand: Brand;
  sources: BrandSource[];
  total_ads: number;
  ads_by_format: Record<string, number>;
  ads_by_platform: Record<string, number>;
  last_collected_at: string | null;
}

export interface BrandSourceCreateRequest {
  platform: string;
  source_type: string;
  source_value: string;
}

export interface BrandCreateRequest {
  brand_name: string;
  notes?: string;
  sources: BrandSourceCreateRequest[];
}

export interface BrandUpdateRequest {
  brand_name?: string;
  is_active?: boolean;
  notes?: string;
}

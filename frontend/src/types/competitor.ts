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

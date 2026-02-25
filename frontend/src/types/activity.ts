export interface ActivityLog {
  id: string;
  event_type: "collection" | "system" | "ad_change";
  event_subtype: string | null;
  title: string;
  message: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ActivityLogsResponse {
  items: ActivityLog[];
  total: number;
}

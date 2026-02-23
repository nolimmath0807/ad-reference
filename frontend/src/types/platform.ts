import type { PlatformType } from "./ad";

export type PlatformStatusType = "active" | "limited" | "unavailable";

export interface PlatformStatus {
  platform: PlatformType;
  status: PlatformStatusType;
  message: string | null;
  last_synced_at: string | null;
}

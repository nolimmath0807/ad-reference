import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";
import { AdDetailModal } from "@/components/ad/AdDetailModal";
import type { Ad, AdDetailResponse } from "@/types/ad";

export function AdDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [ad, setAd] = useState<Ad | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setIsLoading(true);
    api.get<AdDetailResponse>(`/ads/${id}`).then((data) => {
      setAd(data.ad);
      setIsLoading(false);
    });
  }, [id]);

  if (isLoading) {
    return (
      <div className="flex h-full min-h-[60vh] items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <AdDetailModal
      ad={ad}
      open={true}
      onOpenChange={(open) => {
        if (!open) navigate("/dashboard");
      }}
    />
  );
}

import { useState } from "react";
import { Loader2, Plus, X } from "lucide-react";
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
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { Brand, BrandCreateRequest } from "@/types/competitor";

interface SourceRow {
  platform: string;
  source_value: string;
}

interface AddCompetitorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

const PLATFORM_INPUT_CONFIG: Record<string, { label: string; placeholder: string }> = {
  google: { label: "Domain", placeholder: "nike.com" },
  meta: { label: "Page ID", placeholder: "112245377924307 또는 Ad Library URL 붙여넣기" },
  tiktok: { label: "Search Keyword", placeholder: "Nike" },
};

function parseMetaPageId(input: string): string {
  const trimmed = input.trim();
  if (/^\d+$/.test(trimmed)) return trimmed;
  try {
    const url = new URL(trimmed);
    const pageId = url.searchParams.get("view_all_page_id") || url.searchParams.get("id");
    if (pageId) return pageId;
  } catch {
    // not a URL, return as-is
  }
  return trimmed;
}

function makeEmptySource(): SourceRow {
  return { platform: "google", source_value: "" };
}

export function AddCompetitorDialog({ open, onOpenChange, onSuccess }: AddCompetitorDialogProps) {
  const [brandName, setBrandName] = useState("");
  const [notes, setNotes] = useState("");
  const [sources, setSources] = useState<SourceRow[]>([makeEmptySource()]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const addSource = () => {
    setSources((prev) => [...prev, makeEmptySource()]);
  };

  const removeSource = (index: number) => {
    setSources((prev) => prev.filter((_, i) => i !== index));
  };

  const updateSource = (index: number, updates: Partial<SourceRow>) => {
    setSources((prev) =>
      prev.map((s, i) => (i === index ? { ...s, ...updates } : s))
    );
  };

  const isValid =
    brandName.trim().length > 0 &&
    sources.length > 0 &&
    sources.every((s) => s.source_value.trim().length > 0);

  const resetForm = () => {
    setBrandName("");
    setNotes("");
    setSources([makeEmptySource()]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const payload: BrandCreateRequest = {
      brand_name: brandName.trim(),
      notes: notes.trim() || undefined,
      sources: sources.map((s) => ({
        platform: s.platform,
        source_type: s.platform === "google" ? "domain" : s.platform === "meta" ? "page_id" : "keyword",
        source_value: s.source_value.trim(),
      })),
    };

    try {
      await api.post<Brand>("/brands", payload);
      toast.success(`"${brandName.trim()}" has been added to monitoring.`);
      resetForm();
      onOpenChange(false);
      onSuccess();
    } catch (err: unknown) {
      const error = err as { status?: number };
      if (error.status === 409) {
        toast.error("This brand is already being monitored.");
      } else {
        toast.error("Failed to add competitor. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add competitor</DialogTitle>
            <DialogDescription>
              Add a brand and its tracking sources to monitor ad activity across platforms.
            </DialogDescription>
          </DialogHeader>

          <div className="mt-4 flex flex-col gap-5">
            {/* Brand Name */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="brand-name">Brand Name</Label>
              <Input
                id="brand-name"
                placeholder="e.g. Nike, Adidas"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                required
              />
            </div>

            {/* Sources */}
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <Label>Tracking Sources</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 text-xs"
                  onClick={addSource}
                >
                  <Plus className="size-3" />
                  Add Source
                </Button>
              </div>

              <div className="flex flex-col gap-2">
                {sources.map((source, index) => {
                  const config = PLATFORM_INPUT_CONFIG[source.platform] ?? PLATFORM_INPUT_CONFIG.google;
                  return (
                    <div key={index} className="flex items-end gap-2">
                      <div className="w-[130px] shrink-0">
                        {index === 0 && (
                          <Label className="mb-1.5 block text-xs text-muted-foreground">Platform</Label>
                        )}
                        <Select
                          value={source.platform}
                          onValueChange={(value) =>
                            updateSource(index, { platform: value, source_value: "" })
                          }
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="google">Google</SelectItem>
                            <SelectItem value="meta">Meta</SelectItem>
                            <SelectItem value="tiktok">TikTok</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="flex-1">
                        {index === 0 && (
                          <Label className="mb-1.5 block text-xs text-muted-foreground">
                            {config.label}
                          </Label>
                        )}
                        <Input
                          placeholder={config.placeholder}
                          value={source.source_value}
                          onChange={(e) => {
                            const value = source.platform === "meta" ? parseMetaPageId(e.target.value) : e.target.value;
                            updateSource(index, { source_value: value });
                          }}
                        />
                      </div>

                      {sources.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-xs"
                          className="mb-0.5 shrink-0"
                          onClick={() => removeSource(index)}
                        >
                          <X className="size-3.5 text-muted-foreground" />
                        </Button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Notes */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="brand-notes">Notes (optional)</Label>
              <textarea
                id="brand-notes"
                placeholder="Why are you monitoring this competitor?"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                className="border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 w-full rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs outline-none focus-visible:ring-[3px]"
              />
            </div>
          </div>

          <DialogFooter className="mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !isValid}>
              {isSubmitting && <Loader2 className="animate-spin" />}
              Add competitor
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

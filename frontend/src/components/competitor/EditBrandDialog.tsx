import { useState, useEffect } from "react";
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
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type {
  BrandStats,
  BrandSource,
  BrandUpdateRequest,
  BrandSourceCreateRequest,
} from "@/types/competitor";

interface EditBrandDialogProps {
  stats: BrandStats;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

const PLATFORM_COLORS: Record<string, string> = {
  google: "bg-blue-500/10 text-blue-600",
  meta: "bg-indigo-500/10 text-indigo-600",
  tiktok: "bg-neutral-900/10 text-neutral-800",
};

const PLATFORM_INPUT_CONFIG: Record<string, { label: string; placeholder: string }> = {
  google: { label: "Domain", placeholder: "nike.com" },
  meta: { label: "Page ID", placeholder: "112245377924307 또는 Ad Library URL 붙여넣기" },
  tiktok: { label: "Search Keyword", placeholder: "Nike" },
};

export function EditBrandDialog({ stats, open, onOpenChange, onSuccess }: EditBrandDialogProps) {
  const [brandName, setBrandName] = useState(stats.brand.brand_name);
  const [notes, setNotes] = useState(stats.brand.notes ?? "");
  const [isActive, setIsActive] = useState(stats.brand.is_active);
  const [sources, setSources] = useState<BrandSource[]>(stats.sources);
  const [isSaving, setIsSaving] = useState(false);

  // New source form
  const [newPlatform, setNewPlatform] = useState("google");
  const [newSourceValue, setNewSourceValue] = useState("");
  const [isAddingSource, setIsAddingSource] = useState(false);
  const [removingSourceId, setRemovingSourceId] = useState<string | null>(null);

  // Sync state when stats prop changes (e.g. after re-fetch)
  useEffect(() => {
    setBrandName(stats.brand.brand_name);
    setNotes(stats.brand.notes ?? "");
    setIsActive(stats.brand.is_active);
    setSources(stats.sources);
  }, [stats]);

  const newConfig = PLATFORM_INPUT_CONFIG[newPlatform] ?? PLATFORM_INPUT_CONFIG.google;
  const canAddSource = newSourceValue.trim().length > 0;
  const isValid = brandName.trim().length > 0;

  const handleAddSource = async () => {
    setIsAddingSource(true);
    const payload: BrandSourceCreateRequest = {
      platform: newPlatform,
      source_type: newPlatform === "google" ? "domain" : newPlatform === "meta" ? "page_id" : "keyword",
      source_value: newSourceValue.trim(),
    };

    try {
      const created = await api.post<BrandSource>(
        `/brands/${stats.brand.id}/sources`,
        payload
      );
      setSources((prev) => [...prev, created]);
      setNewSourceValue("");
      toast.success("Source added.");
    } catch {
      toast.error("Failed to add source.");
    } finally {
      setIsAddingSource(false);
    }
  };

  const handleRemoveSource = async (sourceId: string) => {
    setRemovingSourceId(sourceId);

    // Optimistic removal
    const prev = sources;
    setSources((s) => s.filter((src) => src.id !== sourceId));

    try {
      await api.delete(`/brands/${stats.brand.id}/sources/${sourceId}`);
      toast.success("Source removed.");
    } catch {
      // Revert on failure
      setSources(prev);
      toast.error("Failed to remove source.");
    } finally {
      setRemovingSourceId(null);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    const payload: BrandUpdateRequest = {
      brand_name: brandName.trim(),
      is_active: isActive,
      notes: notes.trim() || undefined,
    };

    try {
      await api.put(`/brands/${stats.brand.id}`, payload);
      toast.success("Brand updated.");
      onOpenChange(false);
      onSuccess();
    } catch {
      toast.error("Failed to update brand.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = (nextOpen: boolean) => {
    onOpenChange(nextOpen);
    if (!nextOpen) {
      onSuccess();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit brand</DialogTitle>
          <DialogDescription>
            Update brand details and manage tracking sources.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4 flex flex-col gap-5">
          {/* Brand Name */}
          <div className="flex flex-col gap-2">
            <Label htmlFor="edit-brand-name">Brand Name</Label>
            <Input
              id="edit-brand-name"
              placeholder="e.g. Nike, Adidas"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
            />
          </div>

          {/* Active Toggle */}
          <div className="flex items-center justify-between">
            <div className="flex flex-col gap-0.5">
              <Label htmlFor="edit-brand-active">Active monitoring</Label>
              <span className="text-xs text-muted-foreground">
                {isActive ? "Currently collecting ads" : "Monitoring paused"}
              </span>
            </div>
            <Switch
              id="edit-brand-active"
              checked={isActive}
              onCheckedChange={setIsActive}
            />
          </div>

          {/* Existing Sources */}
          <div className="flex flex-col gap-3">
            <Label>Tracking Sources</Label>
            <div className="flex flex-col gap-2">
              {sources.map((source) => (
                <div
                  key={source.id}
                  className="flex items-center justify-between rounded-lg border bg-muted/30 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="secondary"
                      className={`text-[10px] ${PLATFORM_COLORS[source.platform] ?? "bg-neutral-500/10 text-neutral-600"}`}
                    >
                      {source.platform}
                    </Badge>
                    <span className="text-sm">{source.source_value}</span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    disabled={sources.length <= 1 || removingSourceId === source.id}
                    onClick={() => handleRemoveSource(source.id)}
                  >
                    {removingSourceId === source.id ? (
                      <Loader2 className="size-3 animate-spin text-muted-foreground" />
                    ) : (
                      <X className="size-3.5 text-muted-foreground" />
                    )}
                  </Button>
                </div>
              ))}
            </div>
          </div>

          {/* Add New Source */}
          <div className="flex flex-col gap-2">
            <Label className="text-xs text-muted-foreground">Add new source</Label>
            <div className="flex items-end gap-2">
              <div className="w-[130px] shrink-0">
                <Select
                  value={newPlatform}
                  onValueChange={(value) => {
                    setNewPlatform(value);
                    setNewSourceValue("");
                  }}
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
                <Input
                  placeholder={newConfig.placeholder}
                  value={newSourceValue}
                  onChange={(e) => setNewSourceValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && canAddSource && !isAddingSource) {
                      e.preventDefault();
                      handleAddSource();
                    }
                  }}
                />
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="shrink-0"
                disabled={!canAddSource || isAddingSource}
                onClick={handleAddSource}
              >
                {isAddingSource ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  <Plus className="size-3.5" />
                )}
              </Button>
            </div>
          </div>

          {/* Notes */}
          <div className="flex flex-col gap-2">
            <Label htmlFor="edit-brand-notes">Notes</Label>
            <textarea
              id="edit-brand-notes"
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
            onClick={() => handleClose(false)}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button
            type="button"
            disabled={isSaving || !isValid}
            onClick={handleSave}
          >
            {isSaving && <Loader2 className="animate-spin" />}
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

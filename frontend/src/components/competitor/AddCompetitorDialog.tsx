import { useState } from "react";
import { Loader2 } from "lucide-react";
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
import type { MonitoredDomain, MonitoredDomainCreateRequest } from "@/types/competitor";

interface AddCompetitorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function AddCompetitorDialog({ open, onOpenChange, onSuccess }: AddCompetitorDialogProps) {
  const [form, setForm] = useState<MonitoredDomainCreateRequest>({
    domain: "",
    platform: "google",
    notes: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await api.post<MonitoredDomain>("/monitored-domains", {
        domain: form.domain,
        platform: form.platform,
        notes: form.notes || undefined,
      });
      toast.success(`"${form.domain}" has been added to monitoring.`);
      setForm({ domain: "", platform: "google", notes: "" });
      onOpenChange(false);
      onSuccess();
    } catch (err: unknown) {
      const error = err as { status?: number };
      if (error.status === 409) {
        toast.error("This domain is already being monitored.");
      } else {
        toast.error("Failed to add competitor. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add competitor</DialogTitle>
            <DialogDescription>
              Add a domain to monitor their ad activity across platforms.
            </DialogDescription>
          </DialogHeader>

          <div className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="competitor-domain">Domain</Label>
              <Input
                id="competitor-domain"
                placeholder="e.g. example.com"
                value={form.domain}
                onChange={(e) => setForm({ ...form, domain: e.target.value })}
                required
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="competitor-platform">Platform</Label>
              <Select
                value={form.platform ?? "google"}
                onValueChange={(value) => setForm({ ...form, platform: value })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select platform" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="google">Google</SelectItem>
                  <SelectItem value="meta">Meta</SelectItem>
                  <SelectItem value="tiktok">TikTok</SelectItem>
                  <SelectItem value="instagram">Instagram</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <Label htmlFor="competitor-notes">Notes (optional)</Label>
              <textarea
                id="competitor-notes"
                placeholder="Why are you monitoring this competitor?"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
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
            <Button type="submit" disabled={isSubmitting || !form.domain.trim()}>
              {isSubmitting && <Loader2 className="animate-spin" />}
              Add competitor
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

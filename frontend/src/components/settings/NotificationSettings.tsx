import { useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";

interface NotificationPrefs {
  emailNotifications: boolean;
  newAdAlerts: boolean;
  weeklyReport: boolean;
  marketingEmails: boolean;
}

export function NotificationSettings() {
  const [prefs, setPrefs] = useState<NotificationPrefs>({
    emailNotifications: true,
    newAdAlerts: true,
    weeklyReport: false,
    marketingEmails: false,
  });
  const [isSaving, setIsSaving] = useState(false);

  const toggle = (key: keyof NotificationPrefs) => {
    setPrefs((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    // Mock API call
    await new Promise((resolve) => setTimeout(resolve, 500));
    toast.success("Notification preferences saved.");
    setIsSaving(false);
  };

  const items: { key: keyof NotificationPrefs; label: string; description: string }[] = [
    {
      key: "emailNotifications",
      label: "Email notifications",
      description: "Receive important updates and alerts via email.",
    },
    {
      key: "newAdAlerts",
      label: "New ad collection alerts",
      description: "Get notified when new ads matching your interests are collected.",
    },
    {
      key: "weeklyReport",
      label: "Weekly report",
      description: "Receive a weekly summary of ad trends and insights.",
    },
    {
      key: "marketingEmails",
      label: "Marketing updates",
      description: "News about product updates and features.",
    },
  ];

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h3 className="text-lg font-semibold">Notifications</h3>
        <p className="text-sm text-muted-foreground">
          Choose what notifications you want to receive.
        </p>
      </div>

      <div className="flex flex-col gap-1">
        {items.map((item, index) => (
          <div key={item.key}>
            <div className="flex items-center justify-between py-4">
              <div className="flex flex-col gap-1">
                <Label className="text-sm font-medium">{item.label}</Label>
                <p className="text-xs text-muted-foreground">{item.description}</p>
              </div>
              <Switch
                checked={prefs[item.key]}
                onCheckedChange={() => toggle(item.key)}
              />
            </div>
            {index < items.length - 1 && <Separator />}
          </div>
        ))}
      </div>

      <div>
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving && <Loader2 className="animate-spin" />}
          Save preferences
        </Button>
      </div>
    </div>
  );
}

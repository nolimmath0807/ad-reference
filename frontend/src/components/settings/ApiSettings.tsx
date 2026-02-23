import { useState } from "react";
import { Copy, Eye, EyeOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";

export function ApiSettings() {
  const [showKey, setShowKey] = useState(false);

  // Mock data
  const apiKey = "sk-adr-xxxxxxxxxxxxxxxxxxxxxxxxxxxx1234";
  const maskedKey = "sk-adr-xxxx...xxxx1234";
  const usagePercent = 42;
  const usedCalls = 4200;
  const totalCalls = 10000;

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey);
    toast.success("API key copied to clipboard.");
  };

  const handleRegenerate = () => {
    toast.success("New API key generated.");
  };

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h3 className="text-lg font-semibold">API Settings</h3>
        <p className="text-sm text-muted-foreground">
          Manage your API key and monitor usage.
        </p>
      </div>

      {/* API Key */}
      <div className="flex flex-col gap-4">
        <Label>API Key</Label>
        <div className="flex items-center gap-2">
          <Input
            value={showKey ? apiKey : maskedKey}
            readOnly
            className="max-w-md font-mono text-sm"
          />
          <Button
            variant="outline"
            size="icon"
            onClick={() => setShowKey(!showKey)}
          >
            {showKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </Button>
          <Button variant="outline" size="icon" onClick={handleCopy}>
            <Copy className="size-4" />
          </Button>
        </div>

        <div>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="sm">
                <RefreshCw className="size-3.5" />
                Regenerate key
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Regenerate API key</AlertDialogTitle>
                <AlertDialogDescription>
                  This will invalidate your current key. Any applications using it will
                  stop working immediately.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={handleRegenerate}>
                  Regenerate
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {/* Usage */}
      <div className="flex flex-col gap-4">
        <div>
          <h4 className="text-sm font-medium">API Usage</h4>
          <p className="text-xs text-muted-foreground">Current billing cycle</p>
        </div>

        <div className="max-w-md">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              {usedCalls.toLocaleString()} / {totalCalls.toLocaleString()} calls
            </span>
            <span className="font-medium">{usagePercent}%</span>
          </div>
          <Progress value={usagePercent} />
        </div>

        <p className="text-xs text-muted-foreground">
          Resets on the 1st of each month. Upgrade your plan for higher limits.
        </p>
      </div>
    </div>
  );
}

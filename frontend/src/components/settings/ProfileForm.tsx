import { useState, useEffect } from "react";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import type { User } from "@/types/user";
import type { UserUpdateRequest } from "@/types/user";

export function ProfileForm() {
  const { user } = useAuth();

  const [name, setName] = useState("");
  const [company, setCompany] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSavingPassword, setIsSavingPassword] = useState(false);

  useEffect(() => {
    if (user) {
      setName(user.name || "");
      setCompany(user.company || "");
      setJobTitle(user.job_title || "");
    }
  }, [user]);

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "?";

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    const payload: UserUpdateRequest = { name, company, job_title: jobTitle };
    await api.put<User>("/users/me", payload);
    toast.success("Profile updated successfully.");
    setIsSavingProfile(false);
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      toast.error("New passwords do not match.");
      return;
    }

    if (newPassword.length < 8) {
      toast.error("Password must be at least 8 characters.");
      return;
    }

    setIsSavingPassword(true);
    const payload: UserUpdateRequest = {
      current_password: currentPassword,
      new_password: newPassword,
    };
    await api.put<User>("/users/me", payload);
    toast.success("Password changed successfully.");
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setIsSavingPassword(false);
  };

  return (
    <div className="flex flex-col gap-8">
      {/* Profile section */}
      <form onSubmit={handleSaveProfile} className="flex flex-col gap-6">
        <div>
          <h3 className="text-lg font-semibold">Profile</h3>
          <p className="text-sm text-muted-foreground">
            Manage your personal information.
          </p>
        </div>

        <div className="flex items-center gap-4">
          <Avatar className="size-16">
            <AvatarImage src={user?.avatar_url || undefined} />
            <AvatarFallback className="text-lg">{initials}</AvatarFallback>
          </Avatar>
          <div>
            <p className="text-sm font-medium">{user?.name}</p>
            <p className="text-xs text-muted-foreground">{user?.email}</p>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <Label htmlFor="profile-name">Name</Label>
            <Input
              id="profile-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your name"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="profile-email">Email</Label>
            <Input
              id="profile-email"
              value={user?.email || ""}
              readOnly
              className="opacity-60"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="profile-company">Company</Label>
            <Input
              id="profile-company"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Company name"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="profile-job-title">Job title</Label>
            <Input
              id="profile-job-title"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="Your role"
            />
          </div>
        </div>

        <div>
          <Button type="submit" disabled={isSavingProfile}>
            {isSavingProfile && <Loader2 className="animate-spin" />}
            Save changes
          </Button>
        </div>
      </form>

      <Separator />

      {/* Password section */}
      <form onSubmit={handleChangePassword} className="flex flex-col gap-6">
        <div>
          <h3 className="text-lg font-semibold">Change password</h3>
          <p className="text-sm text-muted-foreground">
            Update your password to keep your account secure.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-2 sm:col-span-2">
            <Label htmlFor="current-password">Current password</Label>
            <Input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Enter current password"
              required
              className="sm:max-w-sm"
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-password">New password</Label>
            <Input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="At least 8 characters"
              required
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="confirm-password">Confirm new password</Label>
            <Input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm new password"
              required
            />
          </div>
        </div>

        <div>
          <Button type="submit" disabled={isSavingPassword}>
            {isSavingPassword && <Loader2 className="animate-spin" />}
            Change password
          </Button>
        </div>
      </form>
    </div>
  );
}

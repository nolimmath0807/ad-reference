import { useState, useEffect } from "react";
import { Loader2, Copy, KeyRound } from "lucide-react";
import { api } from "@/lib/api-client";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";

interface AdminUser {
  id: string;
  email: string;
  name: string;
  company: string | null;
  job_title: string | null;
  role: string;
  created_at: string;
}

interface ResetPasswordResponse {
  user_id: string;
  email: string;
  temp_password: string;
}

export function UserManagement() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [confirmTarget, setConfirmTarget] = useState<AdminUser | null>(null);
  const [isResetting, setIsResetting] = useState(false);

  const [tempPasswordResult, setTempPasswordResult] = useState<ResetPasswordResponse | null>(null);

  useEffect(() => {
    api
      .get<AdminUser[]>("/admin/users")
      .then((data) => setUsers(data))
      .finally(() => setIsLoading(false));
  }, []);

  const handleResetConfirm = async () => {
    if (!confirmTarget) return;
    setIsResetting(true);
    const result = await api.post<ResetPasswordResponse>("/admin/reset-password", {
      user_id: confirmTarget.id,
    });
    setConfirmTarget(null);
    setIsResetting(false);
    setTempPasswordResult(result);
  };

  const handleCopyPassword = () => {
    if (!tempPasswordResult) return;
    navigator.clipboard.writeText(tempPasswordResult.temp_password);
    toast.success("임시 비밀번호가 복사되었습니다.");
  };

  const formatDate = (iso: string) => {
    return new Date(iso).toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="text-lg font-semibold">유저 관리</h3>
        <p className="text-sm text-muted-foreground">
          전체 유저 목록을 조회하고 비밀번호를 재설정할 수 있습니다.
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="size-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">이름</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">이메일</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">역할</th>
                <th className="px-4 py-3 text-left font-medium text-muted-foreground">가입일</th>
                <th className="px-4 py-3 text-right font-medium text-muted-foreground"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((user, index) => (
                <tr
                  key={user.id}
                  className={index < users.length - 1 ? "border-b" : ""}
                >
                  <td className="px-4 py-3 font-medium">{user.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">{user.email}</td>
                  <td className="px-4 py-3">
                    <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                      {user.role}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {formatDate(user.created_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setConfirmTarget(user)}
                    >
                      <KeyRound className="size-3.5" />
                      비밀번호 재설정
                    </Button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-muted-foreground">
                    유저가 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Confirm reset dialog */}
      <Dialog open={!!confirmTarget} onOpenChange={(open) => !open && setConfirmTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>비밀번호 재설정</DialogTitle>
            <DialogDescription>
              정말 <span className="font-semibold text-foreground">{confirmTarget?.name}</span>의
              비밀번호를 재설정하시겠습니까?
              <br />
              새로운 임시 비밀번호가 생성됩니다.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmTarget(null)}
              disabled={isResetting}
            >
              취소
            </Button>
            <Button onClick={handleResetConfirm} disabled={isResetting}>
              {isResetting && <Loader2 className="animate-spin" />}
              재설정
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Temp password result dialog */}
      <Dialog
        open={!!tempPasswordResult}
        onOpenChange={(open) => !open && setTempPasswordResult(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>임시 비밀번호 발급 완료</DialogTitle>
            <DialogDescription>
              <span className="font-semibold text-foreground">{tempPasswordResult?.email}</span>
              의 임시 비밀번호가 생성되었습니다. 아래 비밀번호를 유저에게 전달하세요.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2 rounded-md border bg-muted px-4 py-3">
            <code className="flex-1 font-mono text-base tracking-wider">
              {tempPasswordResult?.temp_password}
            </code>
            <Button variant="ghost" size="icon" onClick={handleCopyPassword}>
              <Copy className="size-4" />
            </Button>
          </div>
          <DialogFooter>
            <Button onClick={() => setTempPasswordResult(null)}>확인</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

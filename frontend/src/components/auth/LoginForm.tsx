import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import type { LoginRequest } from "@/types/auth";

export function LoginForm() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState<LoginRequest>({ email: "", password: "" });
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(form);
      navigate("/dashboard");
    } catch (err: unknown) {
      const e = err as Record<string, unknown>;
      const detail = e?.detail as Record<string, unknown> | string | undefined;
      const detailError =
        typeof detail === "object" && detail !== null
          ? (detail.error as Record<string, unknown> | undefined)
          : undefined;

      // NOT_APPROVED 에러 처리
      if (e?.status === 403 && detailError?.code === "NOT_APPROVED") {
        setError("관리자 승인 대기 중입니다. 승인 후 로그인할 수 있습니다.");
      } else {
        const message =
          detailError?.message ||
          (typeof detail === "string" ? detail : null) ||
          "Login failed. Please check your credentials.";
        setError(String(message));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-4">
      {error && (
        <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <Label htmlFor="login-email">Email</Label>
        <Input
          id="login-email"
          type="email"
          placeholder="name@example.com"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          required
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="login-password">Password</Label>
        <Input
          id="login-password"
          type="password"
          placeholder="Password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
        />
      </div>

      <div className="flex items-center gap-2">
        <Checkbox
          id="remember-me"
          checked={rememberMe}
          onCheckedChange={(checked) => setRememberMe(checked === true)}
        />
        <Label htmlFor="remember-me" className="text-sm font-normal text-muted-foreground">
          Remember me
        </Label>
      </div>

      <Button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-full bg-[#334FFF] hover:bg-[#334FFF]/90"
      >
        {isSubmitting && <Loader2 className="animate-spin" />}
        Log in
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Don't have an account?{" "}
        <Link to="/register" className="font-medium text-[#334FFF] hover:underline">
          Sign up
        </Link>
      </p>
    </form>
  );
}

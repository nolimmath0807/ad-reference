import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { RegisterRequest } from "@/types/auth";

export function RegisterForm() {
  const { register } = useAuth();
  const [form, setForm] = useState<RegisterRequest & { passwordConfirm: string }>({
    name: "",
    email: "",
    password: "",
    passwordConfirm: "",
  });
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMessage("");

    if (form.password !== form.passwordConfirm) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const message = await register({ name: form.name, email: form.email, password: form.password });
      setSuccessMessage(message || "회원가입이 완료되었습니다. 관리자 승인 후 로그인할 수 있습니다.");
    } catch (err: unknown) {
      const e = err as Record<string, unknown>;
      const detail = e?.detail as Record<string, unknown> | string | undefined;
      const message =
        (typeof detail === "object" && detail !== null
          ? (detail.error as Record<string, unknown>)?.message
          : detail) ||
        (e?.error as Record<string, unknown>)?.message ||
        "Registration failed. Please try again.";
      setError(String(message));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (successMessage) {
    return (
      <div className="flex w-full flex-col items-center gap-4">
        <CheckCircle2 className="size-12 text-emerald-500" />
        <p className="text-center text-sm text-muted-foreground">{successMessage}</p>
        <Link to="/login" className="w-full">
          <Button className="w-full rounded-full bg-[#334FFF] hover:bg-[#334FFF]/90">
            로그인 페이지로 이동
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full flex-col gap-4">
      {error && (
        <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <Label htmlFor="register-name">Name</Label>
        <Input
          id="register-name"
          type="text"
          placeholder="Your name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="register-email">Email</Label>
        <Input
          id="register-email"
          type="email"
          placeholder="name@example.com"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          required
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="register-password">Password</Label>
        <Input
          id="register-password"
          type="password"
          placeholder="Password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          required
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="register-password-confirm">Confirm Password</Label>
        <Input
          id="register-password-confirm"
          type="password"
          placeholder="Confirm password"
          value={form.passwordConfirm}
          onChange={(e) => setForm({ ...form, passwordConfirm: e.target.value })}
          required
        />
      </div>

      <Button
        type="submit"
        disabled={isSubmitting}
        className="w-full rounded-full bg-[#334FFF] hover:bg-[#334FFF]/90"
      >
        {isSubmitting && <Loader2 className="animate-spin" />}
        Create Account
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-[#334FFF] hover:underline">
          Log in
        </Link>
      </p>
    </form>
  );
}

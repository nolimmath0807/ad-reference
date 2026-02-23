import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading) return null;

  return (
    <section className="flex min-h-screen items-center justify-center bg-[#fdfdfe]">
      <div className="flex w-full max-w-sm flex-col items-center gap-6 px-4">
        <img src="/logos/logo-en-blue.svg" alt="Ad Reference" className="h-10" />
        <div className="w-full rounded-xl border border-border bg-card px-6 py-8 shadow-sm">
          <h1 className="mb-6 text-center text-xl font-semibold text-foreground">Log in</h1>
          <LoginForm />
        </div>
      </div>
    </section>
  );
}

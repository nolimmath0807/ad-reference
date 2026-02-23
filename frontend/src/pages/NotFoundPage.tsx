import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { FileQuestion } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <FileQuestion className="h-16 w-16 text-muted-foreground" />
      <h1 className="text-4xl font-bold tracking-tight">404</h1>
      <p className="text-lg text-muted-foreground">
        Page not found. The page you are looking for does not exist.
      </p>
      <div className="flex gap-3">
        <Button asChild>
          <Link to="/">Go Home</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link to="/dashboard">Dashboard</Link>
        </Button>
      </div>
    </div>
  );
}

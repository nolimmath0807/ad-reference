import { useState } from "react"
import { Link } from "react-router-dom"
import { Menu, X } from "lucide-react"

import { Button } from "@/components/ui/button"

const navLinks = [
  { label: "탐색", href: "#features" },
  { label: "기능", href: "#capabilities" },
  { label: "요금제", href: "#pricing" },
  { label: "블로그", href: "#blog" },
]

function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <img
            src="/logos/logo-en-blue.svg"
            alt="snipit"
            className="h-7"
          />
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden items-center gap-1 md:flex">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className="rounded-lg px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Desktop Auth Buttons */}
        <div className="hidden items-center gap-2 md:flex">
          <Button variant="ghost" size="sm" asChild>
            <Link to="/login">로그인</Link>
          </Button>
          <Button
            size="sm"
            className="rounded-full bg-brand-primary text-brand-primary-foreground hover:bg-brand-primary/90"
            asChild
          >
            <Link to="/register">시작하기</Link>
          </Button>
        </div>

        {/* Mobile Menu Toggle */}
        <button
          className="inline-flex items-center justify-center rounded-md p-2 text-muted-foreground hover:text-foreground md:hidden"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="border-t bg-background md:hidden">
          <div className="mx-auto max-w-7xl space-y-1 px-4 py-4">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="block rounded-lg px-4 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <div className="flex flex-col gap-2 pt-4">
              <Button variant="outline" asChild>
                <Link to="/login">로그인</Link>
              </Button>
              <Button
                className="rounded-full bg-brand-primary text-brand-primary-foreground hover:bg-brand-primary/90"
                asChild
              >
                <Link to="/register">시작하기</Link>
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}

export { Navbar }

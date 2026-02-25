import { Link } from "react-router-dom"
import { ArrowRight } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

function HeroSection() {
  return (
    <section className="relative overflow-hidden py-20 lg:py-32">
      {/* Background gradient glow */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-0 -translate-x-1/2 h-[600px] w-[800px] rounded-full bg-brand-primary/5 blur-3xl" />
      </div>

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col items-center text-center">
          {/* Badge */}
          <Badge
            variant="outline"
            className="mb-6 gap-1.5 rounded-full border-brand-primary/20 bg-brand-primary/5 px-4 py-1.5 text-sm font-medium text-brand-primary"
          >
            AI 광고 레퍼런스 플랫폼
          </Badge>

          {/* Heading */}
          <h1 className="mb-6 max-w-4xl text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            찾고 싶을 때 찾아지는
            <br />
            <span className="bg-gradient-to-r from-[#334fff] to-[#ec458d] bg-clip-text text-transparent">
              콘텐츠 레퍼런스
            </span>
          </h1>

          {/* Description */}
          <p className="mb-10 max-w-2xl text-lg text-muted-foreground lg:text-xl">
            Meta, Google, TikTok 광고 크리에이티브를
            <br className="hidden sm:block" />
            AI가 자동으로 수집하고 정리합니다
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col items-center gap-3 sm:flex-row">
            <Button
              size="lg"
              className="rounded-full bg-brand-primary px-8 text-base font-semibold text-brand-primary-foreground hover:bg-brand-primary/90"
              asChild
            >
              <Link to="/register">무료로 시작하기</Link>
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="rounded-full px-8 text-base font-medium"
              asChild
            >
              <a href="#features">
                데모 보기
                <ArrowRight className="ml-1 size-4" />
              </a>
            </Button>
          </div>

          {/* Hero Image / App Screenshot */}
          <div className="mt-16 w-full max-w-5xl">
            <div className="overflow-hidden rounded-xl border bg-gradient-to-b from-muted/50 to-muted shadow-2xl shadow-brand-primary/10">
              <div className="aspect-video w-full bg-muted/30 p-4 sm:p-8">
                <div className="flex h-full flex-col gap-3 rounded-lg border bg-background p-4 shadow-sm">
                  {/* Mock app header */}
                  <div className="flex items-center gap-2">
                    <div className="size-3 rounded-full bg-red-400" />
                    <div className="size-3 rounded-full bg-yellow-400" />
                    <div className="size-3 rounded-full bg-green-400" />
                    <div className="ml-4 h-6 w-48 rounded-md bg-muted" />
                  </div>
                  {/* Mock content grid */}
                  <div className="grid flex-1 grid-cols-2 gap-3 sm:grid-cols-4">
                    {Array.from({ length: 8 }).map((_, i) => (
                      <div
                        key={i}
                        className="rounded-lg bg-muted/60"
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export { HeroSection }

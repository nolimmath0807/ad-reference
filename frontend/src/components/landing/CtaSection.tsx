import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"

function CtaSection() {
  return (
    <section className="py-20 lg:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#334fff] to-[#ec458d] px-6 py-16 text-center sm:px-12 lg:px-20 lg:py-24">
          {/* Decorative elements */}
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute -left-20 -top-20 size-72 rounded-full bg-white/10 blur-3xl" />
            <div className="absolute -bottom-20 -right-20 size-72 rounded-full bg-white/10 blur-3xl" />
          </div>

          <div className="relative z-10">
            <h2 className="mb-4 text-3xl font-bold tracking-tight text-white lg:text-4xl">
              지금 바로 경쟁사 광고를 분석해보세요
            </h2>
            <p className="mx-auto mb-10 max-w-xl text-lg text-white/80">
              무료로 시작하고, 필요할 때 업그레이드하세요.
              <br />
              신용카드 없이 바로 이용할 수 있습니다.
            </p>
            <Button
              size="lg"
              className="rounded-full bg-white px-10 text-base font-semibold text-[#334fff] shadow-lg hover:bg-white/90"
              asChild
            >
              <Link to="/register">무료로 시작하기</Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}

export { CtaSection }

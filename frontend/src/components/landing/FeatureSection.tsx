import { Globe, Sparkles, SlidersHorizontal, LayoutGrid } from "lucide-react"

const features = [
  {
    icon: Globe,
    title: "멀티 플랫폼",
    description:
      "Meta, Google, TikTok, Instagram 등 주요 광고 플랫폼의 크리에이티브를 한 곳에서 확인하세요.",
  },
  {
    icon: Sparkles,
    title: "AI 자동 수집",
    description:
      "AI가 자동으로 광고 크리에이티브를 수집하고 분류합니다. 더 이상 수동으로 레퍼런스를 모을 필요 없습니다.",
  },
  {
    icon: SlidersHorizontal,
    title: "스마트 필터",
    description:
      "산업, 포맷, 성과 등 다양한 필터로 원하는 레퍼런스를 빠르게 찾아보세요.",
  },
  {
    icon: LayoutGrid,
    title: "개인 보드",
    description:
      "마음에 드는 광고를 보드에 저장하고 팀과 공유하세요. 프로젝트별로 체계적으로 관리할 수 있습니다.",
  },
]

function FeatureSection() {
  return (
    <section id="capabilities" className="py-20 lg:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="mb-16 text-center">
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-foreground lg:text-4xl">
            AI로 더 빠르게, 더 정확하게
            <br />
            레퍼런스를 찾으세요
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
            반복적인 리서치 작업은 AI에게 맡기고 크리에이티브에 집중하세요
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => {
            const Icon = feature.icon
            return (
              <div
                key={feature.title}
                className="group relative overflow-hidden rounded-2xl border bg-background p-6 transition-all hover:shadow-lg hover:shadow-brand-primary/5"
              >
                {/* Gradient overlay on hover */}
                <div className="absolute inset-0 -z-10 bg-gradient-to-br from-[#334fff]/5 to-[#ec458d]/5 opacity-0 transition-opacity group-hover:opacity-100" />

                <div className="mb-4 inline-flex rounded-xl bg-brand-primary/10 p-3">
                  <Icon className="size-6 text-brand-primary" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-foreground">
                  {feature.title}
                </h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

export { FeatureSection }

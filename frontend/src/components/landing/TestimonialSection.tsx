import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"

const platforms = [
  { name: "Meta", color: "#1877F2" },
  { name: "Google", color: "#4285F4" },
  { name: "TikTok", color: "#000000" },
  { name: "Instagram", color: "#E4405F" },
]

const testimonials = [
  {
    name: "김지수",
    role: "퍼포먼스 마케터",
    company: "테크스타트업",
    avatar: "",
    content:
      "레퍼런스 찾는 시간을 70% 줄였습니다. 이전에는 경쟁사 광고를 하나하나 찾아다녔는데, 이제는 snipit에서 바로 확인할 수 있어요.",
  },
  {
    name: "박현우",
    role: "크리에이티브 디렉터",
    company: "광고대행사",
    avatar: "",
    content:
      "경쟁사 광고를 한눈에 볼 수 있어서 기획이 훨씬 빨라졌어요. 특히 AI 필터 기능이 정말 유용합니다.",
  },
]

function TestimonialSection() {
  return (
    <section id="features" className="bg-muted/30 py-20 lg:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="mb-12 text-center">
          <h2 className="mb-4 text-3xl font-bold tracking-tight text-foreground lg:text-4xl">
            지원 플랫폼 & 연동
          </h2>
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
            주요 광고 플랫폼의 크리에이티브를 실시간으로 수집합니다
          </p>
        </div>

        {/* Platform Logos */}
        <div className="mb-16 flex flex-wrap items-center justify-center gap-8 lg:gap-16">
          {platforms.map((platform) => (
            <div
              key={platform.name}
              className="flex flex-col items-center gap-2"
            >
              <div className="flex size-14 items-center justify-center rounded-2xl bg-background shadow-sm ring-1 ring-border">
                <span
                  className="text-lg font-bold"
                  style={{ color: platform.color }}
                >
                  {platform.name.charAt(0)}
                </span>
              </div>
              <span className="text-sm font-medium text-muted-foreground">
                {platform.name}
              </span>
            </div>
          ))}
        </div>

        {/* Testimonials Grid */}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {testimonials.map((testimonial) => (
            <Card
              key={testimonial.name}
              className="border-0 bg-background shadow-sm"
            >
              <CardContent className="px-6 pt-6">
                <p className="text-base leading-relaxed text-foreground/80">
                  &ldquo;{testimonial.content}&rdquo;
                </p>
              </CardContent>
              <CardFooter className="px-6 pb-6">
                <div className="flex items-center gap-3">
                  <Avatar className="size-10 ring-1 ring-border">
                    <AvatarImage
                      src={testimonial.avatar}
                      alt={testimonial.name}
                    />
                    <AvatarFallback className="bg-brand-primary/10 text-sm font-semibold text-brand-primary">
                      {testimonial.name.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {testimonial.name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {testimonial.role} @ {testimonial.company}
                    </p>
                  </div>
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

export { TestimonialSection }

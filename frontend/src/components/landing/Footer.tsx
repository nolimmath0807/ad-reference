import { Link } from "react-router-dom"

import { Separator } from "@/components/ui/separator"

const footerSections = [
  {
    title: "제품",
    links: [
      { name: "기능", href: "#capabilities" },
      { name: "요금제", href: "#pricing" },
      { name: "업데이트", href: "#" },
    ],
  },
  {
    title: "회사",
    links: [
      { name: "소개", href: "#" },
      { name: "블로그", href: "#blog" },
      { name: "채용", href: "#" },
    ],
  },
  {
    title: "지원",
    links: [
      { name: "도움말", href: "#" },
      { name: "문의하기", href: "#" },
      { name: "FAQ", href: "#" },
    ],
  },
]

function Footer() {
  return (
    <footer className="border-t bg-muted/30 py-12 lg:py-16">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
          {/* Logo & Description */}
          <div className="col-span-2 md:col-span-1">
            <Link to="/" className="inline-block">
              <img
                src="/logos/logo-en-blue.svg"
                alt="snipit"
                className="h-7"
              />
            </Link>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
              AI가 수집하고 정리하는 광고 크리에이티브 레퍼런스 플랫폼
            </p>
          </div>

          {/* Footer Links */}
          {footerSections.map((section) => (
            <div key={section.title}>
              <h3 className="mb-4 text-sm font-semibold text-foreground">
                {section.title}
              </h3>
              <ul className="space-y-3">
                {section.links.map((link) => (
                  <li key={link.name}>
                    <a
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.name}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <Separator className="my-8" />

        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} snipit. All rights reserved.
          </p>
          <div className="flex items-center gap-6">
            <a
              href="#"
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              이용약관
            </a>
            <a
              href="#"
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              개인정보처리방침
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}

export { Footer }

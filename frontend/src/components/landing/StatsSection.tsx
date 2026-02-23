const stats = [
  {
    value: "1,000+",
    label: "광고주 분석",
  },
  {
    value: "50,000+",
    label: "광고 수집",
  },
  {
    value: "4개",
    label: "플랫폼 지원",
  },
]

function StatsSection() {
  return (
    <section className="border-y bg-muted/30 py-16 lg:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-3">
          {stats.map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="text-4xl font-bold tracking-tight text-foreground lg:text-5xl">
                {stat.value}
              </p>
              <p className="mt-2 text-sm font-medium text-muted-foreground lg:text-base">
                {stat.label}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export { StatsSection }

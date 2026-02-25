import { Area, AreaChart } from "recharts"
import { useId } from "react"

interface SparklineChartProps {
  data: number[]
  color?: string
  width?: number
  height?: number
}

export function SparklineChart({
  data,
  color = "hsl(var(--chart-1))",
  width = 80,
  height = 32,
}: SparklineChartProps) {
  const gradientId = `sparkline-gradient-${useId().replace(/:/g, "")}`
  const chartData = data.map((value) => ({ value }))

  return (
    <AreaChart
      width={width}
      height={height}
      data={chartData}
      margin={{ top: 2, right: 2, bottom: 2, left: 2 }}
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor={color} stopOpacity={0.3} />
          <stop offset="95%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>
      <Area
        type="monotone"
        dataKey="value"
        stroke={color}
        strokeWidth={1.5}
        fill={`url(#${gradientId})`}
        dot={false}
        isAnimationActive={false}
      />
    </AreaChart>
  )
}

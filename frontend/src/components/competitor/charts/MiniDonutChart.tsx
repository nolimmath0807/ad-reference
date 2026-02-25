import { Pie, PieChart } from "recharts"

interface DonutDataItem {
  name: string
  value: number
  fill: string
}

interface MiniDonutChartProps {
  data: DonutDataItem[]
  size?: number
}

export function MiniDonutChart({ data, size = 80 }: MiniDonutChartProps) {
  return (
    <PieChart width={size} height={size}>
      <Pie
        data={data}
        dataKey="value"
        nameKey="name"
        cx="50%"
        cy="50%"
        innerRadius={size * 0.35}
        outerRadius={size * 0.45}
        cornerRadius={4}
        paddingAngle={3}
        strokeWidth={0}
      />
    </PieChart>
  )
}

import { useMemo } from "react"
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts"
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"

interface DataKey {
  key: string
  color: string
  label: string
}

interface TrendAreaChartProps {
  data: { label: string; [key: string]: string | number }[]
  dataKeys: DataKey[]
}

export function TrendAreaChart({ data, dataKeys }: TrendAreaChartProps) {
  const chartConfig = useMemo(() => {
    const config: ChartConfig = {}
    for (const dk of dataKeys) {
      config[dk.key] = {
        label: dk.label,
        color: dk.color,
      }
    }
    return config
  }, [dataKeys])

  return (
    <ChartContainer config={chartConfig} className="aspect-auto h-[250px] w-full">
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis
          dataKey="label"
          tickLine={false}
          axisLine={false}
          tickMargin={8}
          className="text-xs"
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          tickMargin={4}
          className="text-xs"
        />
        <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
        <defs>
          {dataKeys.map((dk) => (
            <linearGradient
              key={dk.key}
              id={`gradient-${dk.key}`}
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop
                offset="5%"
                stopColor={`var(--color-${dk.key})`}
                stopOpacity={0.4}
              />
              <stop
                offset="95%"
                stopColor={`var(--color-${dk.key})`}
                stopOpacity={0.05}
              />
            </linearGradient>
          ))}
        </defs>
        {dataKeys.map((dk) => (
          <Area
            key={dk.key}
            type="monotone"
            dataKey={dk.key}
            stroke={`var(--color-${dk.key})`}
            strokeWidth={1.5}
            fill={`url(#gradient-${dk.key})`}
            fillOpacity={1}
            dot={false}
          />
        ))}
      </AreaChart>
    </ChartContainer>
  )
}

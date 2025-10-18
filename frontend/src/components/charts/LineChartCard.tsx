import { ResponsiveContainer, LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend } from 'recharts'
import Card from '../ui/Card'

type SeriesLine = {
  dataKey: string
  name: string
  color?: string
}

type LineChartCardProps<T> = {
  title: string
  subtitle?: string
  data: T[]
  xKey: keyof T
  lines: SeriesLine[]
  height?: number
}

export function LineChartCard<T extends Record<string, any>>({
  title,
  subtitle,
  data,
  xKey,
  lines,
  height = 280,
}: LineChartCardProps<T>) {
  return (
    <Card title={title} subtitle={subtitle}>
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 16, right: 24, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey={xKey as string} stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip />
            <Legend />
            {lines.map((line) => (
              <Line
                key={line.dataKey}
                type="monotone"
                dataKey={line.dataKey}
                name={line.name}
                stroke={line.color || '#2563eb'}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

export default LineChartCard

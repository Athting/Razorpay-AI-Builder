import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { MetricsOverview } from '../../api/types'

const SLICES = [
  { key: 'cases_recovered', label: 'Recovered', color: '#22C55E' },
  { key: 'cases_in_progress', label: 'In Progress', color: '#F59E0B' },
  { key: 'cases_escalated', label: 'Escalated', color: '#EF4444' },
  { key: 'cases_human_pending', label: 'Human Review', color: '#8B5CF6' },
  { key: 'cases_open', label: 'Open', color: '#94A3B8' },
  { key: 'cases_written_off', label: 'Written Off', color: '#64748B' },
]

export function RecoveryPieChart({ overview }: { overview?: MetricsOverview }) {
  if (!overview) return null
  const data = SLICES
    .map(s => ({ name: s.label, value: (overview as any)[s.key] || 0, color: s.color }))
    .filter(d => d.value > 0)

  return (
    <ResponsiveContainer width="100%" height={250}>
      <PieChart>
        <Pie data={data} cx="50%" cy="45%" outerRadius={80} dataKey="value" strokeWidth={2} stroke="white">
          {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
        </Pie>
        <Tooltip formatter={(v) => [`${v} cases`, '']} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ResponsiveContainer } from 'recharts'
import { Box, Typography } from '@mui/material'
import type { FunnelStage } from '../../api/types'

const formatINR = (p: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0, notation: 'compact' }).format(p / 100)

export function FunnelChart({ data }: { data: FunnelStage[] }) {
  const chartData = data.map(d => ({ name: d.label, count: d.count, paise: d.paise, color: d.color }))

  return (
    <ResponsiveContainer width="100%" height={250}>
      <BarChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748B' }} />
        <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload?.length) {
              const d = payload[0].payload
              return (
                <Box sx={{ background: 'white', border: '1px solid #E2E8F0', borderRadius: 2, p: 1.5 }}>
                  <Typography variant="caption" fontWeight={700}>{d.name}</Typography>
                  <Typography variant="body2" sx={{ fontFamily: '"JetBrains Mono", monospace' }}>{d.count} cases</Typography>
                  <Typography variant="body2" color="text.secondary">{formatINR(d.paise)}</Typography>
                </Box>
              )
            }
            return null
          }}
        />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {chartData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

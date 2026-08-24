import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { Box, Typography } from '@mui/material'
import type { TrendPoint } from '../../api/types'

const formatINR = (paise: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(paise / 100)

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <Box sx={{ background: 'white', border: '1px solid #E2E8F0', borderRadius: 2, p: 1.5 }}>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
        <Typography variant="body2" fontWeight={700} color="success.main" sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
          {formatINR(payload[0].value)}
        </Typography>
      </Box>
    )
  }
  return null
}

export function TrendChart({ data }: { data: TrendPoint[] }) {
  const chartData = data.map(d => ({ date: d.date.slice(5), value: d.recovered_paise }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
        <defs>
          <linearGradient id="recoveryGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3395FF" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#3395FF" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94A3B8' }} />
        <YAxis tickFormatter={v => `₹${(v / 100000).toFixed(0)}L`} tick={{ fontSize: 11, fill: '#94A3B8' }} />
        <Tooltip content={<CustomTooltip />} />
        <Area type="monotone" dataKey="value" stroke="#3395FF" strokeWidth={2}
          fill="url(#recoveryGrad)" dot={false} activeDot={{ r: 5, fill: '#3395FF' }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

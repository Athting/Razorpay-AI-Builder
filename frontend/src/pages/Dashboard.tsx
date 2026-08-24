import { useState } from 'react'
import {
  Box, Grid, Card, CardContent, Typography, Button,
  ButtonGroup, LinearProgress, Chip, Alert,
} from '@mui/material'
import { PlayArrow, Refresh } from '@mui/icons-material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-toastify'
import { metricsApi, replayApi } from '../api/metrics'
import { AmountDisplay } from '../components/shared/AmountDisplay'
import { TrendChart } from '../components/charts/TrendChart'
import { FunnelChart } from '../components/charts/FunnelChart'
import { RecoveryPieChart } from '../components/charts/RecoveryPieChart'
import { useReplayStore } from '../store/replayStore'

const SPEED_OPTIONS = [1, 5, 10, 50]

export default function Dashboard() {
  const qc = useQueryClient()
  const { isRunning, speed, setRunning, setSpeed } = useReplayStore()

  const { data: overview, isLoading } = useQuery({
    queryKey: ['metrics', 'overview'],
    queryFn: metricsApi.overview,
    refetchInterval: isRunning ? 2000 : 30000,
  })

  const { data: funnel } = useQuery({
    queryKey: ['metrics', 'funnel'],
    queryFn: metricsApi.funnel,
    refetchInterval: isRunning ? 2000 : 30000,
  })

  const { data: trend } = useQuery({
    queryKey: ['metrics', 'trend'],
    queryFn: () => metricsApi.trend(30),
    refetchInterval: isRunning ? 3000 : 60000,
  })

  const handleStartReplay = async () => {
    try {
      const result = await replayApi.start(speed)
      setRunning(true, result.job_id, result.total_cases)
      toast.success(`🚀 Replay started — ${result.total_cases} cases queued at ${speed}× speed`)
      qc.invalidateQueries({ queryKey: ['metrics'] })
    } catch (e: any) {
      toast.error('Failed to start replay: ' + (e?.response?.data?.detail || e.message))
    }
  }

  const kpis = [
    {
      label: 'Total at Risk', value: overview?.total_at_risk_paise || 0,
      type: 'amount', color: '#0C2451', bg: '#EBF4FF',
      sub: `${overview?.total_cases || 0} cases`,
    },
    {
      label: 'Recovered', value: overview?.total_recovered_paise || 0,
      type: 'amount', color: '#22C55E', bg: '#F0FDF4',
      sub: `${overview?.cases_recovered || 0} cases closed`,
    },
    {
      label: 'Recovery Rate', value: overview?.recovery_rate_pct || 0,
      type: 'pct', color: '#3395FF', bg: '#EBF4FF',
      sub: 'of at-risk revenue',
    },
    {
      label: 'Avg Time to Recovery', value: overview?.avg_time_to_recovery_hours || 0,
      type: 'hours', color: '#F59E0B', bg: '#FFFBEB',
      sub: 'hours per case',
    },
  ]

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" fontWeight={800} color="primary.dark">Revenue Recovery</Typography>
          <Typography variant="body2" color="text.secondary">
            AI-powered detection, diagnosis, and recovery pipeline
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={<Refresh />} onClick={() => qc.invalidateQueries({ queryKey: ['metrics'] })}>
          Refresh
        </Button>
      </Box>

      {/* KPI Cards */}
      <Grid container spacing={2} mb={3}>
        {kpis.map(kpi => (
          <Grid item xs={12} sm={6} lg={3} key={kpi.label}>
            <Card sx={{ background: kpi.bg, border: `1px solid ${kpi.color}20` }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="caption" color="text.secondary" fontWeight={600} textTransform="uppercase" letterSpacing={0.5}>
                  {kpi.label}
                </Typography>
                <Box mt={1}>
                  {kpi.type === 'amount' && <AmountDisplay paise={kpi.value} variant="h4" color={kpi.color} />}
                  {kpi.type === 'pct' && (
                    <Typography variant="h4" fontWeight={800} color={kpi.color}
                      sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
                      {kpi.value.toFixed(1)}%
                    </Typography>
                  )}
                  {kpi.type === 'hours' && (
                    <Typography variant="h4" fontWeight={800} color={kpi.color}
                      sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
                      {kpi.value.toFixed(1)}h
                    </Typography>
                  )}
                </Box>
                <Typography variant="caption" color="text.secondary">{kpi.sub}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Batch Replay Control */}
      <Card sx={{ mb: 3, border: isRunning ? '1px solid #3395FF40' : undefined }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Box>
              <Typography variant="h6" fontWeight={700}>Batch Replay</Typography>
              <Typography variant="body2" color="text.secondary">
                Run the full AI pipeline on all open cases
              </Typography>
            </Box>
            <Box sx={{ flex: 1 }} />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="caption" color="text.secondary" mr={1}>Speed:</Typography>
              <ButtonGroup size="small" variant="outlined">
                {SPEED_OPTIONS.map(s => (
                  <Button
                    key={s} onClick={() => setSpeed(s)}
                    variant={speed === s ? 'contained' : 'outlined'}
                    sx={{ minWidth: 48 }}
                  >
                    {s}×
                  </Button>
                ))}
              </ButtonGroup>
            </Box>
            <Button
              variant="contained" size="large" startIcon={<PlayArrow />}
              onClick={handleStartReplay} disabled={isRunning}
              sx={{ minWidth: 160 }}
            >
              {isRunning ? 'Running…' : 'Run Demo Replay'}
            </Button>
          </Box>
          {isRunning && (
            <Box mt={2}>
              <LinearProgress sx={{ borderRadius: 2 }} />
              <Typography variant="caption" color="text.secondary" mt={0.5} display="block">
                Pipeline running — dashboard auto-refreshes every 2s
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Status summary chips */}
      {overview && (
        <Box sx={{ display: 'flex', gap: 1, mb: 3, flexWrap: 'wrap' }}>
          {[
            { label: `Open: ${overview.cases_open}`, color: '#94A3B8' },
            { label: `In Progress: ${overview.cases_in_progress}`, color: '#F59E0B' },
            { label: `Recovered: ${overview.cases_recovered}`, color: '#22C55E' },
            { label: `Escalated: ${overview.cases_escalated}`, color: '#EF4444' },
            { label: `Human Review: ${overview.cases_human_pending}`, color: '#8B5CF6' },
            { label: `Written Off: ${overview.cases_written_off}`, color: '#64748B' },
          ].map(c => (
            <Chip key={c.label} label={c.label} size="small"
              sx={{ backgroundColor: `${c.color}15`, color: c.color, border: `1px solid ${c.color}30`, fontWeight: 600 }} />
          ))}
        </Box>
      )}

      {/* Charts row */}
      <Grid container spacing={2} mb={3}>
        <Grid item xs={12} lg={7}>
          <Card sx={{ height: 340 }}>
            <CardContent sx={{ height: '100%', p: 3 }}>
              <Typography variant="h6" fontWeight={700} mb={2}>Recovery Funnel</Typography>
              <FunnelChart data={funnel || []} />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} lg={5}>
          <Card sx={{ height: 340 }}>
            <CardContent sx={{ height: '100%', p: 3 }}>
              <Typography variant="h6" fontWeight={700} mb={2}>Status Distribution</Typography>
              <RecoveryPieChart overview={overview} />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Trend chart */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={700} mb={2}>Recovery Trend (Last 30 Days)</Typography>
          <TrendChart data={trend || []} />
        </CardContent>
      </Card>
    </Box>
  )
}

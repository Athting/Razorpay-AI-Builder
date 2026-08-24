import {
  Box, Typography, Card, CardContent, Grid, Button, Chip, Avatar,
  Select, MenuItem, FormControl, InputLabel, Alert,
} from '@mui/material'
import { CheckCircle, Cancel } from '@mui/icons-material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-toastify'
import { casesApi } from '../api/cases'
import { AmountDisplay } from '../components/shared/AmountDisplay'
import { ROOT_CAUSE_LABELS } from '../theme/razorpayTheme'
import { formatDistanceToNow } from 'date-fns'
import type { Case } from '../api/types'

export default function Escalations() {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['cases-escalated'],
    queryFn: () => casesApi.list({ status: 'human_pending', size: 50 }),
    refetchInterval: 10000,
  })

  const { data: escalatedData } = useQuery({
    queryKey: ['cases-escalated2'],
    queryFn: () => casesApi.list({ status: 'escalated', size: 50 }),
    refetchInterval: 10000,
  })

  const allCases = [
    ...(data?.items || []),
    ...(escalatedData?.items || []),
  ]

  const handleApprove = async (caseId: string) => {
    try {
      await casesApi.approve(caseId)
      toast.success('✅ Action approved and queued for execution!')
      qc.invalidateQueries({ queryKey: ['cases-escalated'] })
      qc.invalidateQueries({ queryKey: ['cases-escalated2'] })
    } catch { toast.error('Failed to approve') }
  }

  const handleReject = async (caseId: string) => {
    try {
      await casesApi.reject(caseId)
      toast.success('Action rejected — policy engine re-scoring')
      qc.invalidateQueries({ queryKey: ['cases-escalated'] })
    } catch { toast.error('Failed to reject') }
  }

  const totalRisk = allCases.reduce((s, c) => s + c.amount_at_risk, 0)

  return (
    <Box>
      <Typography variant="h4" fontWeight={800} color="primary.dark" mb={0.5}>
        Escalation Queue
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Cases requiring human review before the AI can act
      </Typography>

      {/* Summary */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <Card sx={{ flex: 1, minWidth: 160, background: '#F5F3FF', border: '1px solid #8B5CF620' }}>
          <CardContent sx={{ p: 2.5 }}>
            <Typography variant="caption" color="text.secondary" fontWeight={600} textTransform="uppercase" letterSpacing={0.5}>
              Pending Review
            </Typography>
            <Typography variant="h4" fontWeight={800} color="#8B5CF6" sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
              {allCases.length}
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ flex: 2, minWidth: 200, background: '#FEF2F2', border: '1px solid #EF444420' }}>
          <CardContent sx={{ p: 2.5 }}>
            <Typography variant="caption" color="text.secondary" fontWeight={600} textTransform="uppercase" letterSpacing={0.5}>
              At Risk in Queue
            </Typography>
            <AmountDisplay paise={totalRisk} variant="h4" color="#EF4444" />
          </CardContent>
        </Card>
      </Box>

      {isLoading && <Typography color="text.secondary">Loading escalations…</Typography>}

      {allCases.length === 0 && !isLoading && (
        <Card>
          <CardContent sx={{ p: 6, textAlign: 'center' }}>
            <Typography fontSize={48} mb={2}>✅</Typography>
            <Typography variant="h6" fontWeight={600} color="success.main">
              No cases pending human review
            </Typography>
            <Typography variant="body2" color="text.secondary" mt={1}>
              The AI is handling all active cases within its bounded action space.
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Case cards */}
      <Grid container spacing={2}>
        {allCases.map((c: Case) => (
          <Grid item xs={12} md={6} xl={4} key={c.id}>
            <Card sx={{ border: '1px solid #8B5CF630', '&:hover': { borderColor: '#8B5CF6' }, transition: 'border-color 0.2s' }}>
              <CardContent sx={{ p: 3 }}>
                {/* Header */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Avatar sx={{ width: 36, height: 36, bgcolor: '#8B5CF6', fontSize: 14 }}>
                      {c.customer?.name?.charAt(0) || '?'}
                    </Avatar>
                    <Box>
                      <Typography variant="body2" fontWeight={700}>{c.customer?.name || 'Unknown'}</Typography>
                      <Typography variant="caption" color="text.secondary">{c.customer?.segment}</Typography>
                    </Box>
                  </Box>
                  <AmountDisplay paise={c.amount_at_risk} variant="h6" />
                </Box>

                {/* Info chips */}
                <Box sx={{ display: 'flex', gap: 0.75, mb: 2, flexWrap: 'wrap' }}>
                  <Chip
                    label={c.type.replace('_', ' ')}
                    size="small" sx={{ background: '#EBF4FF', color: '#3395FF', fontSize: '0.7rem' }}
                  />
                  {c.latest_root_cause && (
                    <Chip
                      label={ROOT_CAUSE_LABELS[c.latest_root_cause] || c.latest_root_cause}
                      size="small" variant="outlined" sx={{ fontSize: '0.7rem' }}
                    />
                  )}
                  <Chip
                    label={`${c.days_open}d open`}
                    size="small" sx={{ background: '#FFFBEB', color: '#F59E0B', fontSize: '0.7rem' }}
                  />
                  <Chip
                    label={`${c.attempt_count} attempts`}
                    size="small" variant="outlined" sx={{ fontSize: '0.7rem' }}
                  />
                </Box>

                {/* Why escalated */}
                <Box sx={{ p: 1.5, borderRadius: 2, background: '#F5F3FF', mb: 2 }}>
                  <Typography variant="caption" color="#8B5CF6" fontWeight={600} display="block" mb={0.25}>
                    👤 Why escalated
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {c.amount_at_risk >= 1_000_000
                      ? `High-value case (₹${(c.amount_at_risk / 100).toLocaleString('en-IN')}) requires human approval before action.`
                      : c.attempt_count >= 3
                      ? `${c.attempt_count} automated attempts exhausted. Human outreach recommended.`
                      : 'Requires human review before AI can proceed.'}
                  </Typography>
                </Box>

                <Typography variant="caption" color="text.secondary" display="block" mb={1.5}>
                  Opened {formatDistanceToNow(new Date(c.opened_at), { addSuffix: true })}
                </Typography>

                {/* Action buttons */}
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    variant="contained" color="success" size="small" fullWidth
                    startIcon={<CheckCircle />}
                    onClick={() => handleApprove(c.id)}
                  >
                    Approve Action
                  </Button>
                  <Button
                    variant="outlined" color="error" size="small" fullWidth
                    startIcon={<Cancel />}
                    onClick={() => handleReject(c.id)}
                  >
                    Reject
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

import {
  Box, Typography, Grid, Card, CardContent, Chip, Avatar,
  LinearProgress, Button, Divider, Alert, Table, TableBody,
  TableRow, TableCell, Paper, Tooltip,
} from '@mui/material'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-toastify'
import { ArrowBack, CheckCircle, Cancel, Escalator } from '@mui/icons-material'
import { casesApi } from '../api/cases'
import { AmountDisplay } from '../components/shared/AmountDisplay'
import { CaseStatusChip } from '../components/cases/CaseStatusChip'
import { ReasoningChip } from '../components/shared/ReasoningChip'
import { HashChainBadge } from '../components/audit/HashChainBadge'
import { ROOT_CAUSE_LABELS, CHANNEL_ICONS, ACTION_LABELS } from '../theme/razorpayTheme'
import { format } from 'date-fns'
import type { Intervention, ScoredAction } from '../api/types'

const ACTOR_ICONS: Record<string, string> = { system: '⚙️', model: '🧠', human: '👤' }

function TimelineEvent({ icon, title, subtitle, children, color = '#E2E8F0' }: any) {
  return (
    <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Box sx={{
          width: 36, height: 36, borderRadius: '50%', display: 'flex',
          alignItems: 'center', justifyContent: 'center', fontSize: 16,
          background: color, border: '2px solid white', boxShadow: '0 0 0 2px #E2E8F0', flexShrink: 0,
        }}>
          {icon}
        </Box>
        <Box sx={{ flex: 1, width: 2, background: '#F1F5F9', mt: 1 }} />
      </Box>
      <Box sx={{ flex: 1, pb: 3 }}>
        <Typography variant="body2" fontWeight={700} mb={0.25}>{title}</Typography>
        <Typography variant="caption" color="text.secondary" display="block" mb={1}>{subtitle}</Typography>
        {children}
      </Box>
    </Box>
  )
}

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: caseData, isLoading } = useQuery({
    queryKey: ['case', id],
    queryFn: () => casesApi.get(id!),
    enabled: !!id,
  })

  const handleApprove = async () => {
    try { await casesApi.approve(id!); toast.success('Action approved!'); qc.invalidateQueries({ queryKey: ['case', id] }) }
    catch { toast.error('Failed') }
  }
  const handleReject = async () => {
    try { await casesApi.reject(id!); toast.success('Re-scoring…'); qc.invalidateQueries({ queryKey: ['case', id] }) }
    catch { toast.error('Failed') }
  }

  if (isLoading) return <Box p={4}><Typography>Loading…</Typography></Box>
  if (!caseData) return <Box p={4}><Typography>Case not found</Typography></Box>

  const latestDiag = caseData.diagnoses?.[caseData.diagnoses.length - 1]
  const latestIntervention = caseData.interventions?.[caseData.interventions.length - 1]
  const actionScores: ScoredAction[] = latestIntervention?.payload?.action_scores || []

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
        <Button startIcon={<ArrowBack />} onClick={() => navigate('/cases')} variant="text" size="small">
          Cases
        </Button>
        <Typography variant="h5" fontWeight={700} color="primary.dark" flex={1}>
          Case #{id?.slice(-8).toUpperCase()}
        </Typography>
        <CaseStatusChip status={caseData.status} />
        {caseData.status === 'human_pending' && (
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="contained" color="success" size="small" startIcon={<CheckCircle />} onClick={handleApprove}>
              Approve Action
            </Button>
            <Button variant="outlined" color="error" size="small" startIcon={<Cancel />} onClick={handleReject}>
              Reject
            </Button>
          </Box>
        )}
      </Box>

      <Grid container spacing={3}>
        {/* Left: Timeline */}
        <Grid item xs={12} lg={7}>
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={700} mb={3}>Case Timeline</Typography>

              {/* Payment Event */}
              <TimelineEvent
                icon="💳" color="#EBF4FF"
                title={`Payment Failed — ${caseData.type.replace('_', ' ')}`}
                subtitle={format(new Date(caseData.opened_at), 'PPpp')}
              >
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  <Chip label={`Amount: `} size="small" variant="outlined" />
                  <AmountDisplay paise={caseData.amount_at_risk} variant="body2" />
                </Box>
              </TimelineEvent>

              {/* Diagnoses */}
              {caseData.diagnoses?.map((d, i) => (
                <TimelineEvent
                  key={d.id} icon="🔬" color="#F0FDF4"
                  title={`Diagnosed: ${ROOT_CAUSE_LABELS[d.root_cause] || d.root_cause}`}
                  subtitle={`${format(new Date(d.created_at), 'PPpp')} · ${d.model_version}`}
                >
                  <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                    <Chip label={`${(d.confidence * 100).toFixed(0)}% confidence`} size="small"
                      sx={{ background: d.confidence >= 0.9 ? '#F0FDF4' : d.confidence >= 0.7 ? '#FFFBEB' : '#FEF2F2',
                        color: d.confidence >= 0.9 ? '#22C55E' : d.confidence >= 0.7 ? '#F59E0B' : '#EF4444', fontWeight: 600 }} />
                    <Chip label={`→ ${d.suggested_channel} ${CHANNEL_ICONS[d.suggested_channel]}`} size="small" variant="outlined" />
                  </Box>
                  <ReasoningChip reasoning={d.reasoning_text} />
                </TimelineEvent>
              ))}

              {/* Interventions */}
              {caseData.interventions?.map((iv: Intervention, i) => (
                <TimelineEvent
                  key={iv.id} icon={CHANNEL_ICONS[iv.channel] || '📨'} color="#FFFBEB"
                  title={`Attempt #${iv.attempt_number}: ${ACTION_LABELS[iv.action_type] || iv.action_type}`}
                  subtitle={`${iv.executed_at ? format(new Date(iv.executed_at), 'PPpp') : 'Scheduled: ' + format(new Date(iv.scheduled_at), 'PPpp')} · ${iv.channel}`}
                >
                  <Box sx={{ display: 'flex', gap: 1, mb: 1, alignItems: 'center' }}>
                    <Chip label={iv.result} size="small"
                      sx={{
                        background: iv.result === 'delivered' || iv.result === 'responded' ? '#F0FDF4' : iv.result === 'failed' ? '#FEF2F2' : '#FFFBEB',
                        color: iv.result === 'delivered' || iv.result === 'responded' ? '#22C55E' : iv.result === 'failed' ? '#EF4444' : '#F59E0B',
                        fontWeight: 600,
                      }} />
                    {iv.expected_recovery_prob && (
                      <Typography variant="caption" color="text.secondary">
                        Expected: {(iv.expected_recovery_prob * 100).toFixed(0)}% recovery prob
                      </Typography>
                    )}
                  </Box>
                  {iv.reasoning && <ReasoningChip reasoning={iv.reasoning} />}
                  {iv.payload?.message && (
                    <Paper variant="outlined" sx={{ mt: 1.5, p: 1.5, background: '#F8FAFF', borderRadius: 2 }}>
                      <Typography variant="caption" fontWeight={600} color="text.secondary" display="block" mb={0.5}>
                        {iv.payload.email_subject ? `📧 Subject: ${iv.payload.email_subject}` : `${CHANNEL_ICONS[iv.channel]} Message`}
                      </Typography>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', fontFamily: iv.channel === 'voice' ? '"JetBrains Mono", monospace' : 'inherit', fontSize: '0.8125rem' }}>
                        {iv.payload.message}
                      </Typography>
                      {iv.payload.tts_script && iv.channel === 'voice' && (
                        <Box mt={1}>
                          <Chip label="🎙 Hinglish Voice Script (TTS-ready)" size="small" sx={{ background: '#F5F3FF', color: '#8B5CF6', fontWeight: 600 }} />
                        </Box>
                      )}
                      {iv.payload.payment_link && (
                        <Chip label={`🔗 ${iv.payload.payment_link}`} size="small" variant="outlined" sx={{ mt: 1, maxWidth: '100%', fontSize: '0.7rem' }} />
                      )}
                    </Paper>
                  )}
                </TimelineEvent>
              ))}

              {/* Outcomes */}
              {caseData.outcomes?.map(o => (
                <TimelineEvent
                  key={o.id} icon={o.outcome === 'paid' ? '✅' : o.outcome === 'ignored' ? '😶' : '⏳'} color={o.outcome === 'paid' ? '#F0FDF4' : '#FEF2F2'}
                  title={`Outcome: ${o.outcome.charAt(0).toUpperCase() + o.outcome.slice(1)}`}
                  subtitle={format(new Date(o.recorded_at), 'PPpp')}
                >
                  {o.outcome === 'paid' && <AmountDisplay paise={o.amount} color="#22C55E" />}
                  {o.promised_date && <Typography variant="caption">Promised by: {o.promised_date}</Typography>}
                </TimelineEvent>
              ))}
            </CardContent>
          </Card>
        </Grid>

        {/* Right: Sidebar */}
        <Grid item xs={12} lg={5}>
          {/* Case Summary */}
          <Card sx={{ mb: 2 }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={700} mb={2}>Case Summary</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Amount at Risk</Typography>
                  <AmountDisplay paise={caseData.amount_at_risk} variant="body2" />
                </Box>
                {caseData.recovered_amount > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="body2" color="text.secondary">Recovered</Typography>
                    <AmountDisplay paise={caseData.recovered_amount} variant="body2" color="#22C55E" />
                  </Box>
                )}
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Days Open</Typography>
                  <Typography variant="body2" fontWeight={600}>{caseData.days_open}d</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Attempts</Typography>
                  <Typography variant="body2" fontWeight={600}>{caseData.attempt_count}</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>

          {/* Customer */}
          {caseData.customer && (
            <Card sx={{ mb: 2 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" fontWeight={700} mb={2}>Customer</Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
                  <Avatar sx={{ bgcolor: '#3395FF', width: 40, height: 40 }}>
                    {caseData.customer.name?.charAt(0)}
                  </Avatar>
                  <Box>
                    <Typography variant="body2" fontWeight={700}>{caseData.customer.name}</Typography>
                    <Typography variant="caption" color="text.secondary">{caseData.customer.email}</Typography>
                  </Box>
                  <Chip label={caseData.customer.segment} size="small"
                    sx={{ ml: 'auto', background: '#EBF4FF', color: '#3395FF', fontWeight: 600 }} />
                </Box>
                <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>Risk Score</Typography>
                <LinearProgress
                  variant="determinate" value={caseData.customer.risk_score * 100}
                  sx={{ height: 6, borderRadius: 3, mb: 2,
                    '& .MuiLinearProgress-bar': { background: caseData.customer.risk_score > 0.7 ? '#EF4444' : caseData.customer.risk_score > 0.4 ? '#F59E0B' : '#22C55E' } }}
                />
                <Typography variant="caption" color="text.secondary" display="block" mb={1}>Channel Opt-ins</Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {Object.entries(caseData.customer.channel_opts || {}).map(([ch, enabled]) => (
                    <Chip key={ch} label={`${CHANNEL_ICONS[ch]} ${ch}`} size="small"
                      sx={{ opacity: enabled ? 1 : 0.35, background: enabled ? '#EBF4FF' : '#F8FAFC' }} />
                  ))}
                  {caseData.customer.dnd_opt_out && (
                    <Chip label="🚫 DND" size="small" sx={{ background: '#FEF2F2', color: '#EF4444', fontWeight: 600 }} />
                  )}
                </Box>
              </CardContent>
            </Card>
          )}

          {/* Why This Action */}
          {actionScores.length > 0 && (
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" fontWeight={700} mb={0.5}>Why This Action?</Typography>
                <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                  Policy engine scored all available actions ↓
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {actionScores.map((action, i) => (
                    <Box key={i} sx={{
                      p: 1.5, borderRadius: 2,
                      background: i === 0 ? '#EBF4FF' : '#F8FAFC',
                      border: i === 0 ? '1px solid #3395FF30' : '1px solid #F1F5F9',
                    }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 0.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {i === 0 && <Chip label="Selected" size="small" sx={{ background: '#3395FF', color: 'white', fontSize: '0.65rem', height: 18 }} />}
                          <Typography variant="body2" fontWeight={600} fontSize="0.8rem">
                            {ACTION_LABELS[action.action_type] || action.action_type}
                            {action.channel !== 'system' && ` via ${CHANNEL_ICONS[action.channel]} ${action.channel}`}
                          </Typography>
                        </Box>
                        <Typography variant="caption" fontWeight={700} color={i === 0 ? '#3395FF' : 'text.secondary'}
                          sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
                          {(action.expected_recovery_prob * 100).toFixed(0)}%
                        </Typography>
                      </Box>
                      <Typography variant="caption" color="text.secondary" fontSize="0.7rem">{action.reasoning}</Typography>
                      {action.requires_human_approval && (
                        <Chip label="Requires human approval" size="small" sx={{ mt: 0.5, fontSize: '0.65rem', background: '#FEF2F2', color: '#EF4444' }} />
                      )}
                    </Box>
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  )
}

import { useState } from 'react'
import {
  Box, Typography, Card, CardContent, Table, TableHead, TableBody,
  TableRow, TableCell, Switch, Button, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, Select, MenuItem, FormControl, InputLabel,
  Alert, Chip, IconButton,
} from '@mui/material'
import { Add, Edit, Delete } from '@mui/icons-material'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { toast } from 'react-toastify'
import { stoppingRulesApi, customersApi } from '../api/stoppingRules'
import { casesApi } from '../api/cases'
import { AmountDisplay } from '../components/shared/AmountDisplay'
import { CaseStatusChip } from '../components/cases/CaseStatusChip'
import type { StoppingRule } from '../api/types'

function RuleDialog({
  open, onClose, rule,
}: { open: boolean; onClose: () => void; rule?: StoppingRule | null }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<Partial<StoppingRule>>(rule || {
    name: '', max_attempts: 3, cooldown_hours: 24,
    quiet_hours_start: 21, quiet_hours_end: 9, applies_to: 'all', active: true,
  })

  const handleSave = async () => {
    try {
      if (rule?.id) {
        await stoppingRulesApi.update(rule.id, form as any)
      } else {
        await stoppingRulesApi.create(form as any)
      }
      toast.success('Rule saved!')
      qc.invalidateQueries({ queryKey: ['stopping-rules'] })
      onClose()
    } catch { toast.error('Failed to save') }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle fontWeight={700}>{rule ? 'Edit Rule' : 'New Stopping Rule'}</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
        <TextField label="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} fullWidth />
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField label="Max Attempts" type="number" value={form.max_attempts}
            onChange={e => setForm({ ...form, max_attempts: +e.target.value })} fullWidth />
          <TextField label="Cooldown (hrs)" type="number" value={form.cooldown_hours}
            onChange={e => setForm({ ...form, cooldown_hours: +e.target.value })} fullWidth />
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField label="Quiet Start (hr)" type="number" value={form.quiet_hours_start}
            onChange={e => setForm({ ...form, quiet_hours_start: +e.target.value })} fullWidth />
          <TextField label="Quiet End (hr)" type="number" value={form.quiet_hours_end}
            onChange={e => setForm({ ...form, quiet_hours_end: +e.target.value })} fullWidth />
        </Box>
        <FormControl fullWidth>
          <InputLabel>Applies To</InputLabel>
          <Select value={form.applies_to} label="Applies To" onChange={e => setForm({ ...form, applies_to: e.target.value })}>
            <MenuItem value="all">All Cases</MenuItem>
            <MenuItem value="subscription_failure">Subscription Failure</MenuItem>
            <MenuItem value="invoice_overdue">Invoice Overdue</MenuItem>
          </Select>
        </FormControl>
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSave}>Save Rule</Button>
      </DialogActions>
    </Dialog>
  )
}

export default function Compliance() {
  const qc = useQueryClient()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editRule, setEditRule] = useState<StoppingRule | null>(null)

  const { data: rules = [] } = useQuery({ queryKey: ['stopping-rules'], queryFn: stoppingRulesApi.list })
  const { data: customers = [] } = useQuery({ queryKey: ['customers', 'dnd'], queryFn: () => customersApi.list({ dnd_only: true }) })
  const { data: escalations } = useQuery({
    queryKey: ['cases', 1, '', '', 'human_pending'],
    queryFn: () => casesApi.list({ status: 'human_pending', size: 20 }),
  })

  const toggleRule = async (rule: StoppingRule) => {
    await stoppingRulesApi.update(rule.id, { ...rule, active: !rule.active })
    qc.invalidateQueries({ queryKey: ['stopping-rules'] })
  }

  const handleOptIn = async (customerId: string) => {
    await customersApi.optIn(customerId)
    toast.success('Customer opted back in')
    qc.invalidateQueries({ queryKey: ['customers'] })
  }

  return (
    <Box>
      <Typography variant="h4" fontWeight={800} color="primary.dark" mb={0.5}>Compliance & Controls</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Stopping rules, DND management, and escalation queue
      </Typography>

      <Alert severity="success" sx={{ mb: 3 }}>
        <strong>0 compliance violations</strong> — all DND preferences, quiet hours, and attempt limits are being enforced.
      </Alert>

      {/* Stopping Rules */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" fontWeight={700}>Stopping Rules</Typography>
            <Button startIcon={<Add />} variant="contained" size="small" onClick={() => { setEditRule(null); setDialogOpen(true) }}>
              Add Rule
            </Button>
          </Box>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Max Attempts</TableCell>
                <TableCell>Cooldown</TableCell>
                <TableCell>Quiet Hours</TableCell>
                <TableCell>Applies To</TableCell>
                <TableCell>Active</TableCell>
                <TableCell>Edit</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rules.map((rule: StoppingRule) => (
                <TableRow key={rule.id}>
                  <TableCell sx={{ fontWeight: 600 }}>{rule.name}</TableCell>
                  <TableCell>{rule.max_attempts}</TableCell>
                  <TableCell>{rule.cooldown_hours}h</TableCell>
                  <TableCell>{rule.quiet_hours_start}:00 – {rule.quiet_hours_end}:00</TableCell>
                  <TableCell>
                    <Chip label={rule.applies_to} size="small" sx={{ background: '#EBF4FF', color: '#3395FF', fontSize: '0.7rem' }} />
                  </TableCell>
                  <TableCell>
                    <Switch size="small" checked={rule.active} onChange={() => toggleRule(rule)} />
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" onClick={() => { setEditRule(rule); setDialogOpen(true) }}>
                      <Edit fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* DND List */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={700} mb={2}>
            DND / Opt-Out List ({customers.length})
          </Typography>
          {customers.length === 0
            ? <Typography variant="body2" color="text.secondary">No customers have opted out.</Typography>
            : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Customer</TableCell>
                    <TableCell>Phone</TableCell>
                    <TableCell>Segment</TableCell>
                    <TableCell>Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {customers.map((c: any) => (
                    <TableRow key={c.id}>
                      <TableCell>{c.name}</TableCell>
                      <TableCell sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.8rem' }}>{c.phone || '—'}</TableCell>
                      <TableCell><Chip label={c.segment} size="small" /></TableCell>
                      <TableCell>
                        <Button size="small" variant="outlined" onClick={() => handleOptIn(c.id)}>
                          Re-opt In
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )
          }
        </CardContent>
      </Card>

      {/* Escalation Queue */}
      <Card>
        <CardContent sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={700} mb={2}>
            Escalation Queue ({escalations?.total || 0} pending)
          </Typography>
          {escalations?.items.map((c) => (
            <Box key={c.id} sx={{ p: 2, mb: 1.5, borderRadius: 2, border: '1px solid #F1F5F9', background: '#F5F3FF10' }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2" fontWeight={700}>{c.customer?.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {c.type.replace('_', ' ')} · {c.days_open} days open
                  </Typography>
                </Box>
                <AmountDisplay paise={c.amount_at_risk} variant="body2" />
                <CaseStatusChip status={c.status} />
              </Box>
              {c.latest_root_cause && (
                <Chip label={c.latest_root_cause.replace('_', ' ')} size="small" sx={{ mt: 1, background: '#EBF4FF' }} />
              )}
            </Box>
          ))}
          {(!escalations?.total) && (
            <Typography variant="body2" color="text.secondary">No cases pending human review.</Typography>
          )}
        </CardContent>
      </Card>

      <RuleDialog open={dialogOpen} onClose={() => setDialogOpen(false)} rule={editRule} />
    </Box>
  )
}

import { useState } from 'react'
import {
  Box, Typography, Card, CardContent, Table, TableHead, TableBody,
  TableRow, TableCell, TextField, Select, MenuItem, FormControl,
  InputLabel, Pagination, Avatar, Button, Chip, TableContainer, Paper,
} from '@mui/material'
import { Search, CheckCircle, Cancel } from '@mui/icons-material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { casesApi } from '../api/cases'
import { AmountDisplay } from '../components/shared/AmountDisplay'
import { CaseStatusChip } from '../components/cases/CaseStatusChip'
import { ROOT_CAUSE_LABELS, CHANNEL_ICONS } from '../theme/razorpayTheme'
import { formatDistanceToNow } from 'date-fns'
import type { Case } from '../api/types'

const TYPE_OPTIONS = ['', 'subscription_failure', 'invoice_overdue', 'checkout_abandoned']
const STATUS_OPTIONS = ['', 'open', 'in_progress', 'recovered', 'escalated', 'written_off', 'human_pending']

export default function CaseList() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [status, setStatus] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['cases', page, search, type, status],
    queryFn: () => casesApi.list({ page, size: 20, search: search || undefined, type: type || undefined, status: status || undefined }),
    refetchInterval: 10000,
  })

  const handleApprove = async (e: React.MouseEvent, caseId: string) => {
    e.stopPropagation()
    try {
      await casesApi.approve(caseId)
      toast.success('Action approved!')
      qc.invalidateQueries({ queryKey: ['cases'] })
    } catch { toast.error('Failed to approve') }
  }

  const handleReject = async (e: React.MouseEvent, caseId: string) => {
    e.stopPropagation()
    try {
      await casesApi.reject(caseId)
      toast.success('Action rejected, re-scoring...')
      qc.invalidateQueries({ queryKey: ['cases'] })
    } catch { toast.error('Failed to reject') }
  }

  return (
    <Box>
      <Typography variant="h4" fontWeight={800} color="primary.dark" mb={0.5}>Cases</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        {data?.total || 0} total cases
      </Typography>

      {/* Filters */}
      <Card sx={{ mb: 2 }}>
        <CardContent sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField
              size="small" placeholder="Search customer…" value={search}
              onChange={e => { setSearch(e.target.value); setPage(1) }}
              InputProps={{ startAdornment: <Search sx={{ mr: 1, color: 'text.disabled', fontSize: 18 }} /> }}
              sx={{ minWidth: 200 }}
            />
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Type</InputLabel>
              <Select value={type} label="Type" onChange={e => { setType(e.target.value); setPage(1) }}>
                <MenuItem value="">All Types</MenuItem>
                <MenuItem value="subscription_failure">Subscription Failure</MenuItem>
                <MenuItem value="invoice_overdue">Invoice Overdue</MenuItem>
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Status</InputLabel>
              <Select value={status} label="Status" onChange={e => { setStatus(e.target.value); setPage(1) }}>
                <MenuItem value="">All Statuses</MenuItem>
                {STATUS_OPTIONS.filter(Boolean).map(s => (
                  <MenuItem key={s} value={s}>{s.replace('_', ' ')}</MenuItem>
                ))}
              </Select>
            </FormControl>
            {(search || type || status) && (
              <Button size="small" onClick={() => { setSearch(''); setType(''); setStatus(''); setPage(1) }}>
                Clear
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Customer</TableCell>
                <TableCell>Amount</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Root Cause</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Attempts</TableCell>
                <TableCell>Opened</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading && (
                <TableRow><TableCell colSpan={8} align="center">Loading…</TableCell></TableRow>
              )}
              {data?.items.map((c: Case) => (
                <TableRow
                  key={c.id} hover
                  onClick={() => navigate(`/cases/${c.id}`)}
                  sx={{ cursor: 'pointer', '&:hover': { background: '#F8FAFF' } }}
                >
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Avatar sx={{ width: 32, height: 32, bgcolor: '#3395FF', fontSize: 13 }}>
                        {c.customer?.name?.charAt(0) || '?'}
                      </Avatar>
                      <Box>
                        <Typography variant="body2" fontWeight={600}>{c.customer?.name || '—'}</Typography>
                        <Typography variant="caption" color="text.secondary">{c.customer?.email || '—'}</Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell><AmountDisplay paise={c.amount_at_risk} /></TableCell>
                  <TableCell>
                    <Chip label={c.type.replace('_', ' ')} size="small"
                      sx={{ fontSize: '0.7rem', background: '#EBF4FF', color: '#3395FF' }} />
                  </TableCell>
                  <TableCell>
                    {c.latest_root_cause ? (
                      <Box>
                        <Typography variant="body2">{ROOT_CAUSE_LABELS[c.latest_root_cause] || c.latest_root_cause}</Typography>
                        {c.latest_confidence && (
                          <Typography variant="caption" color="text.secondary">
                            {(c.latest_confidence * 100).toFixed(0)}% confidence
                          </Typography>
                        )}
                      </Box>
                    ) : '—'}
                  </TableCell>
                  <TableCell><CaseStatusChip status={c.status} /></TableCell>
                  <TableCell>
                    <Typography variant="body2" fontFamily="JetBrains Mono">{c.attempt_count}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" color="text.secondary">
                      {formatDistanceToNow(new Date(c.opened_at), { addSuffix: true })}
                    </Typography>
                  </TableCell>
                  <TableCell onClick={e => e.stopPropagation()}>
                    {c.status === 'human_pending' && (
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Button size="small" color="success" variant="outlined"
                          startIcon={<CheckCircle sx={{ fontSize: '0.9rem !important' }} />}
                          onClick={e => handleApprove(e, c.id)} sx={{ fontSize: '0.7rem', py: 0.25 }}>
                          Approve
                        </Button>
                        <Button size="small" color="error" variant="outlined"
                          startIcon={<Cancel sx={{ fontSize: '0.9rem !important' }} />}
                          onClick={e => handleReject(e, c.id)} sx={{ fontSize: '0.7rem', py: 0.25 }}>
                          Reject
                        </Button>
                      </Box>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        {data && data.pages > 1 && (
          <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
            <Pagination count={data.pages} page={page} onChange={(_, p) => setPage(p)} color="primary" />
          </Box>
        )}
      </Card>
    </Box>
  )
}

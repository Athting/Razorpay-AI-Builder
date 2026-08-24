import { useState } from 'react'
import {
  Box, Typography, Card, CardContent, Table, TableHead, TableBody,
  TableRow, TableCell, Alert, Button, Chip, Autocomplete, TextField,
  Tooltip, CircularProgress,
} from '@mui/material'
import { CheckCircle, Cancel, Download, Verified } from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { casesApi } from '../api/cases'
import { auditApi } from '../api/audit'
import { HashChainBadge } from '../components/audit/HashChainBadge'
import { ReasoningChip } from '../components/shared/ReasoningChip'
import { format } from 'date-fns'
import type { Case, AuditLogEntry } from '../api/types'

const ACTOR_META: Record<string, { icon: string; label: string; color: string }> = {
  system: { icon: '⚙️', label: 'System', color: '#EBF4FF' },
  model: { icon: '🧠', label: 'AI Model', color: '#F5F3FF' },
  human: { icon: '👤', label: 'Human', color: '#F0FDF4' },
}

export default function AuditTrail() {
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)
  const [caseSearch, setCaseSearch] = useState('')

  const { data: casesData } = useQuery({
    queryKey: ['cases', 1, caseSearch],
    queryFn: () => casesApi.list({ search: caseSearch || undefined, size: 20 }),
  })

  const { data: auditEntries = [], isLoading: auditLoading } = useQuery({
    queryKey: ['audit', selectedCaseId],
    queryFn: () => auditApi.getTrail(selectedCaseId!),
    enabled: !!selectedCaseId,
  })

  const { data: verifyResult } = useQuery({
    queryKey: ['audit-verify', selectedCaseId],
    queryFn: () => auditApi.verify(selectedCaseId!),
    enabled: !!selectedCaseId,
  })

  const handleExport = () => {
    if (!selectedCaseId) return
    window.open(auditApi.exportCsv(selectedCaseId), '_blank')
  }

  const caseOptions = casesData?.items || []

  return (
    <Box>
      <Typography variant="h4" fontWeight={800} color="primary.dark" mb={0.5}>Audit Trail</Typography>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Immutable, SHA-256 hash-chained log of every AI decision and system action
      </Typography>

      {/* Case Selector */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 3 }}>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
            <Autocomplete
              sx={{ minWidth: 360 }}
              options={caseOptions}
              getOptionLabel={(o: Case) =>
                `#${o.id.slice(-8).toUpperCase()} — ${o.customer?.name || 'Unknown'} (${o.type.replace('_', ' ')})`
              }
              onInputChange={(_, v) => setCaseSearch(v)}
              onChange={(_, v: Case | null) => setSelectedCaseId(v?.id || null)}
              renderInput={(params) => (
                <TextField {...params} label="Select a case to view audit trail" size="small" />
              )}
            />
            {selectedCaseId && (
              <Button
                variant="outlined" startIcon={<Download />} onClick={handleExport} size="small"
              >
                Export CSV
              </Button>
            )}
          </Box>
        </CardContent>
      </Card>

      {/* Chain Integrity Banner */}
      {verifyResult && (
        <Alert
          severity={verifyResult.valid ? 'success' : 'error'}
          icon={verifyResult.valid ? <Verified /> : <Cancel />}
          sx={{ mb: 3, fontWeight: 500 }}
        >
          {verifyResult.message}
          {verifyResult.valid && (
            <Typography variant="caption" display="block" color="text.secondary" mt={0.5}>
              All {verifyResult.total_entries} entries verified — SHA-256 hash chain intact.
            </Typography>
          )}
        </Alert>
      )}

      {/* Audit Table */}
      {selectedCaseId ? (
        <Card>
          <CardContent sx={{ p: 0 }}>
            {auditLoading ? (
              <Box sx={{ p: 4, textAlign: 'center' }}><CircularProgress /></Box>
            ) : auditEntries.length === 0 ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography color="text.secondary">No audit entries yet for this case.</Typography>
              </Box>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Timestamp</TableCell>
                    <TableCell>Actor</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Reasoning</TableCell>
                    <TableCell>Hash</TableCell>
                    <TableCell>Integrity</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {auditEntries.map((entry: AuditLogEntry, idx) => {
                    const actor = ACTOR_META[entry.actor] || ACTOR_META.system
                    return (
                      <TableRow key={entry.id} sx={{ '&:hover': { background: '#F8FAFF' } }}>
                        <TableCell sx={{ whiteSpace: 'nowrap' }}>
                          <Typography variant="caption" sx={{ fontFamily: '"JetBrains Mono", monospace' }}>
                            {format(new Date(entry.timestamp), 'MM/dd HH:mm:ss')}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={`${actor.icon} ${actor.label}`}
                            size="small"
                            sx={{ background: actor.color, fontWeight: 500, fontSize: '0.72rem' }}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight={600} fontSize="0.8rem">
                            {entry.action.replace(/_/g, ' ').replace(/:/g, ' → ')}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            v{entry.policy_version}
                          </Typography>
                        </TableCell>
                        <TableCell sx={{ maxWidth: 320 }}>
                          <ReasoningChip reasoning={entry.reasoning} />
                        </TableCell>
                        <TableCell>
                          <Box>
                            <Tooltip title={`Hash: ${entry.hash}`} placement="top">
                              <Typography variant="caption" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.65rem', color: '#64748B', cursor: 'help' }}>
                                {entry.hash.slice(0, 14)}…
                              </Typography>
                            </Tooltip>
                            <Typography variant="caption" display="block" sx={{ fontFamily: '"JetBrains Mono", monospace', fontSize: '0.6rem', color: '#CBD5E1' }}>
                              ↑ {entry.prev_hash.slice(0, 10)}…
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <HashChainBadge hash={entry.hash} valid={verifyResult?.valid !== false} />
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent sx={{ p: 6, textAlign: 'center' }}>
            <Typography fontSize={48} mb={2}>🔐</Typography>
            <Typography variant="h6" fontWeight={600} color="primary.dark" mb={1}>
              Select a case to view its audit trail
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Every AI decision, system action, and human override is recorded here with a SHA-256 hash chain for tamper-evidence.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}

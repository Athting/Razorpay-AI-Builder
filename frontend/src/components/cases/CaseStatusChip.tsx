import { Chip } from '@mui/material'
import { STATUS_COLORS, STATUS_BG } from '../../theme/razorpayTheme'
import type { CaseStatus } from '../../api/types'

const STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  in_progress: 'In Progress',
  recovered: '✓ Recovered',
  escalated: '⚠ Escalated',
  written_off: 'Written Off',
  human_pending: '👤 Human Review',
}

export function CaseStatusChip({ status }: { status: CaseStatus | string }) {
  return (
    <Chip
      label={STATUS_LABELS[status] || status}
      size="small"
      sx={{
        backgroundColor: STATUS_BG[status] || '#F8FAFC',
        color: STATUS_COLORS[status] || '#94A3B8',
        border: `1px solid ${STATUS_COLORS[status] || '#94A3B8'}40`,
        fontWeight: 600,
        fontSize: '0.75rem',
      }}
    />
  )
}

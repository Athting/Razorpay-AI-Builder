import { Tooltip, Box, Typography } from '@mui/material'
import { CheckCircle, Cancel } from '@mui/icons-material'

interface Props { hash: string; valid?: boolean }

export function HashChainBadge({ hash, valid = true }: Props) {
  return (
    <Tooltip title={`Full hash: ${hash}`} placement="top">
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, cursor: 'help' }}>
        {valid
          ? <CheckCircle sx={{ fontSize: 14, color: '#22C55E' }} />
          : <Cancel sx={{ fontSize: 14, color: '#EF4444' }} />}
        <Typography
          variant="caption"
          sx={{ fontFamily: '"JetBrains Mono", monospace', color: valid ? '#22C55E' : '#EF4444', fontSize: '0.7rem' }}
        >
          {hash.slice(0, 12)}…
        </Typography>
      </Box>
    </Tooltip>
  )
}

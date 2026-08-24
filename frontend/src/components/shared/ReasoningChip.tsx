import { useState } from 'react'
import { Chip, Tooltip, Box, Typography, Collapse } from '@mui/material'
import { Psychology } from '@mui/icons-material'

interface Props { reasoning: string; short?: boolean }

export function ReasoningChip({ reasoning, short = true }: Props) {
  const [expanded, setExpanded] = useState(false)
  const preview = reasoning.length > 80 ? reasoning.slice(0, 80) + '…' : reasoning

  return (
    <Box>
      <Chip
        icon={<Psychology sx={{ fontSize: '0.9rem !important' }} />}
        label={short && !expanded ? preview : reasoning}
        size="small"
        onClick={() => setExpanded(!expanded)}
        sx={{
          backgroundColor: '#EBF4FF',
          color: '#0C2451',
          border: '1px solid #3395FF30',
          fontStyle: 'italic',
          fontSize: '0.75rem',
          height: 'auto',
          py: 0.5,
          cursor: 'pointer',
          '& .MuiChip-label': { whiteSpace: 'normal', wordBreak: 'break-word' },
          maxWidth: '100%',
        }}
      />
    </Box>
  )
}

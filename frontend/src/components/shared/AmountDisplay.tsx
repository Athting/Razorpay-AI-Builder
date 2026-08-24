import { Typography, Tooltip } from '@mui/material'

interface Props { paise: number; variant?: 'h4' | 'h5' | 'h6' | 'body1' | 'body2'; color?: string }

export function AmountDisplay({ paise, variant = 'body1', color }: Props) {
  const formatted = new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0,
  }).format(paise / 100)

  return (
    <Typography
      variant={variant}
      fontWeight={600}
      className="mono"
      color={color || 'primary.dark'}
      sx={{ fontFamily: '"JetBrains Mono", monospace', letterSpacing: '-0.02em' }}
    >
      {formatted}
    </Typography>
  )
}

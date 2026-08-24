import { createTheme } from '@mui/material/styles'

export const STATUS_COLORS: Record<string, string> = {
  open: '#94A3B8',
  in_progress: '#F59E0B',
  recovered: '#22C55E',
  escalated: '#EF4444',
  written_off: '#64748B',
  human_pending: '#8B5CF6',
}

export const STATUS_BG: Record<string, string> = {
  open: '#F8FAFC',
  in_progress: '#FFFBEB',
  recovered: '#F0FDF4',
  escalated: '#FEF2F2',
  written_off: '#F8FAFC',
  human_pending: '#F5F3FF',
}

export const ROOT_CAUSE_LABELS: Record<string, string> = {
  insufficient_funds: 'Insufficient Funds',
  expired_card: 'Expired Card',
  invalid_card: 'Invalid Card',
  do_not_honor: 'Do Not Honor',
  issuer_unavailable: 'Issuer Unavailable',
  mandate_revoked: 'Mandate Revoked',
  suspected_fraud: 'Suspected Fraud',
  transaction_not_permitted: 'Not Permitted',
  system_error: 'System Error',
  technical_error: 'Technical Error',
  no_funds: 'No Funds',
  exceeds_limit: 'Exceeds Limit',
  unknown: 'Unknown',
}

export const CHANNEL_ICONS: Record<string, string> = {
  whatsapp: '📱',
  sms: '💬',
  email: '📧',
  voice: '📞',
  system: '⚙️',
}

export const ACTION_LABELS: Record<string, string> = {
  retry_payment: 'Retry Payment',
  send_reminder: 'Send Reminder',
  send_offer: 'Send Offer',
  escalate_to_human: 'Escalate',
  write_off: 'Write Off',
  generate_payment_link: 'Payment Link',
}

export const razorpayTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#3395FF',
      dark: '#0C2451',
      light: '#EBF4FF',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#0C2451',
      contrastText: '#FFFFFF',
    },
    success: { main: '#22C55E', light: '#F0FDF4' },
    warning: { main: '#F59E0B', light: '#FFFBEB' },
    error: { main: '#EF4444', light: '#FEF2F2' },
    background: {
      default: '#F8FAFF',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#0C2451',
      secondary: '#64748B',
    },
    divider: 'rgba(12,36,81,0.08)',
  },
  typography: {
    fontFamily: '"Inter", sans-serif',
    h1: { fontWeight: 800, letterSpacing: '-0.03em' },
    h2: { fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontWeight: 700, letterSpacing: '-0.01em' },
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 500 },
    body1: { fontSize: '0.9375rem' },
    body2: { fontSize: '0.875rem', color: '#64748B' },
    caption: { fontSize: '0.75rem', color: '#94A3B8' },
  },
  shape: { borderRadius: 12 },
  shadows: [
    'none',
    '0 1px 3px 0 rgba(12,36,81,0.06), 0 1px 2px -1px rgba(12,36,81,0.04)',
    '0 4px 6px -1px rgba(12,36,81,0.08), 0 2px 4px -2px rgba(12,36,81,0.06)',
    '0 10px 15px -3px rgba(12,36,81,0.08), 0 4px 6px -4px rgba(12,36,81,0.05)',
    ...Array(21).fill('none'),
  ] as any,
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px 0 rgba(12,36,81,0.08), 0 1px 2px -1px rgba(12,36,81,0.06)',
          border: '1px solid rgba(12,36,81,0.07)',
          borderRadius: 16,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 10,
          fontSize: '0.875rem',
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #3395FF 0%, #1A7BF0 100%)',
          boxShadow: '0 2px 8px rgba(51,149,255,0.35)',
          '&:hover': {
            background: 'linear-gradient(135deg, #1A7BF0 0%, #0C6CE0 100%)',
            boxShadow: '0 4px 12px rgba(51,149,255,0.45)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500, fontSize: '0.8125rem' },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 600,
          color: '#64748B',
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          backgroundColor: '#F8FAFF',
          borderBottom: '1px solid rgba(12,36,81,0.08)',
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { borderRadius: 4, height: 6 },
      },
    },
  },
})

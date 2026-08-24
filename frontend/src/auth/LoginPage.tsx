import React, { useState } from 'react'
import {
  Box, Card, CardContent, TextField, Button, Typography,
  Divider, Alert, CircularProgress, InputAdornment, IconButton,
} from '@mui/material'
import { Visibility, VisibilityOff } from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-toastify'
import { useAuth } from './AuthProvider'

export default function LoginPage() {
  const navigate = useNavigate()
  const { signInWithGoogle, signInWithEmail, signUpWithEmail, loading } = useAuth()
  const [isRegistering, setIsRegistering] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('admin@demo.com')
  const [password, setPassword] = useState('demo1234')
  const [showPass, setShowPass] = useState(false)
  const [error, setError] = useState('')

  const handleGoogle = async () => {
    setError('')
    try {
      await signInWithGoogle()
      navigate('/')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Google sign-in failed')
      toast.error('Sign-in failed')
    }
  }

  const handleEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      if (isRegistering) await signUpWithEmail(name, email, password)
      else await signInWithEmail(email, password)
      navigate('/')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Invalid credentials')
    }
  }

  return (
    <Box sx={{
      minHeight: '100vh', display: 'flex',
      background: 'linear-gradient(135deg, #0C2451 0%, #1A3A6E 50%, #0C2451 100%)',
    }}>
      {/* Left panel */}
      <Box sx={{
        flex: 1, display: { xs: 'none', md: 'flex' },
        flexDirection: 'column', justifyContent: 'center', px: 8,
        color: 'white',
      }}>
        <Typography variant="h3" fontWeight={800} mb={2}>
          ⚡ RevRecov
        </Typography>
        <Typography variant="h5" fontWeight={400} mb={3} sx={{ opacity: 0.85 }}>
          AI-Powered Revenue Recovery
        </Typography>
        <Typography variant="body1" sx={{ opacity: 0.7, maxWidth: 400, lineHeight: 1.7 }}>
          Detect failed payments, diagnose root causes with AI, and automatically recover revenue — with full audit trails and compliance built in.
        </Typography>
        <Box mt={6} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {['🔍 AI-powered root cause diagnosis', '🤖 Bounded, explainable policy engine', '📋 SHA-256 hash-chained audit log', '🛡️ TRAI/RBI compliance built in'].map(f => (
            <Typography key={f} variant="body2" sx={{ opacity: 0.75 }}>{f}</Typography>
          ))}
        </Box>
      </Box>

      {/* Right panel */}
      <Box sx={{
        width: { xs: '100%', md: 480 },
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        p: 4, background: 'rgba(255,255,255,0.04)', backdropFilter: 'blur(20px)',
      }}>
        <Card sx={{ width: '100%', maxWidth: 400, p: 1 }}>
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h5" fontWeight={700} mb={0.5} color="primary.dark">
              Welcome back
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={4}>
              {isRegistering ? 'Create your recovery workspace' : 'Sign in to your recovery dashboard'}
            </Typography>

            {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

            {/* Google Sign-In */}
            <Button
              fullWidth
              variant="outlined"
              size="large"
              onClick={handleGoogle}
              disabled={loading}
              startIcon={
                <img src="https://www.google.com/favicon.ico" width={18} height={18} alt="G" />
              }
              sx={{
                mb: 3, borderColor: 'divider', color: 'text.primary',
                '&:hover': { borderColor: '#3395FF', background: '#EBF4FF' },
              }}
            >
              {loading ? <CircularProgress size={20} /> : 'Continue with Google'}
            </Button>

            <Divider sx={{ mb: 3 }}>
              <Typography variant="caption" color="text.secondary">or continue with</Typography>
            </Divider>

            {/* Email/Password form */}
            <form onSubmit={handleEmail}>
              {isRegistering && <TextField fullWidth required label="Your name" value={name} onChange={e => setName(e.target.value)} sx={{ mb: 2 }} size="small" />}
              <TextField
                fullWidth label="Email" type="email" value={email}
                onChange={e => setEmail(e.target.value)}
                sx={{ mb: 2 }} size="small"
              />
              <TextField
                fullWidth label="Password" value={password}
                type={showPass ? 'text' : 'password'}
                onChange={e => setPassword(e.target.value)}
                sx={{ mb: 3 }} size="small"
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton size="small" onClick={() => setShowPass(!showPass)}>
                        {showPass ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
              <Button
                fullWidth type="submit" variant="contained" size="large" disabled={loading}
              >
                {loading ? <CircularProgress size={20} color="inherit" /> : isRegistering ? 'Create Account' : 'Sign In'}
              </Button>
            </form>

            <Button fullWidth sx={{ mt: 1.5 }} onClick={() => { setIsRegistering(!isRegistering); setError('') }}>
              {isRegistering ? 'Already have an account? Sign in' : 'New here? Create an account'}
            </Button>

            {!isRegistering && <Alert severity="info" sx={{ mt: 3 }} icon="💡">
              <Typography variant="caption">
                <strong>Demo:</strong> admin@demo.com / demo1234
              </Typography>
            </Alert>}
          </CardContent>
        </Card>
      </Box>
    </Box>
  )
}

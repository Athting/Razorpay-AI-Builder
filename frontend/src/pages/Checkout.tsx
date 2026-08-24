import { useState } from 'react'
import { Box, Button, Card, CardContent, TextField, Typography } from '@mui/material'
import { toast } from 'react-toastify'
import { paymentsApi } from '../api/payments'

export default function Checkout() {
  const [form, setForm] = useState({ amount: '', name: '', email: '', phone: '', description: 'Payment request' })
  const [link, setLink] = useState('')
  const submit = async () => { try { const r = await paymentsApi.createLink({ amount_paise: Math.round(Number(form.amount) * 100), customer_name: form.name, customer_email: form.email || undefined, customer_phone: form.phone || undefined, description: form.description }); setLink(r.short_url); toast.success('Payment link created') } catch (e:any) { toast.error(e?.response?.data?.detail || 'Could not create payment link') } }
  return <Box maxWidth={560}><Typography variant="h4" fontWeight={800} mb={3}>Create payment link</Typography><Card><CardContent><TextField fullWidth label="Amount (₹)" type="number" sx={{mb:2}} value={form.amount} onChange={e=>setForm({...form,amount:e.target.value})}/><TextField fullWidth label="Customer name" sx={{mb:2}} value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/><TextField fullWidth label="Email" sx={{mb:2}} value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/><TextField fullWidth label="Phone" sx={{mb:2}} value={form.phone} onChange={e=>setForm({...form,phone:e.target.value})}/><Button variant="contained" disabled={!form.amount || !form.name} onClick={submit}>Create secure Razorpay link</Button>{link && <Typography sx={{mt:2}}><a href={link} target="_blank" rel="noreferrer">Open payment link</a></Typography>}</CardContent></Card></Box>
}

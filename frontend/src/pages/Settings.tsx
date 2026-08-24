import { useEffect, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, Divider, MenuItem, Select, TextField, Typography } from '@mui/material'
import { toast } from 'react-toastify'
import { organizationApi, type Organization } from '../api/organization'

export default function Settings() {
  const [org, setOrg] = useState<Organization | null>(null)
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [razorpay, setRazorpay] = useState({ key_id: '', key_secret: '', webhook_secret: '' })
  const [communications, setCommunications] = useState({ sender_email: '', resend_api_key: '', twilio_account_sid: '', twilio_auth_token: '', twilio_from_number: '', twilio_whatsapp_from: '' })
  const [notifications, setNotifications] = useState({ email_recipients: '', slack_webhook_url: '', escalation_alerts: true })

  const load = async () => {
    setLoading(true)
    try { const [current, all] = await Promise.all([organizationApi.current(), organizationApi.list()]); setOrg(current); setOrganizations(all) }
    catch { setOrg(null) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  const saveRazorpay = async () => {
    try { await organizationApi.configureRazorpay(razorpay); toast.success('Razorpay connected'); await load() }
    catch (e: any) { toast.error(e?.response?.data?.detail || 'Could not connect Razorpay') }
  }
  const connectOAuth = async () => {
    try { const { url } = await organizationApi.connectRazorpay(); window.location.assign(url) }
    catch (e: any) { toast.error(e?.response?.data?.detail || 'Razorpay OAuth is not configured') }
  }
  const saveCommunications = async () => {
    try { await organizationApi.configureCommunications(communications); toast.success('Communication settings saved') }
    catch { toast.error('Could not save communication settings') }
  }
  const saveNotifications = async () => {
    try { await organizationApi.configureNotifications({ email_recipients: notifications.email_recipients.split(',').map(x => x.trim()).filter(Boolean), slack_webhook_url: notifications.slack_webhook_url || undefined, escalation_alerts: notifications.escalation_alerts }); toast.success('Alert settings saved') }
    catch { toast.error('Could not save alert settings') }
  }

  if (loading) return <Typography>Loading workspace…</Typography>
  if (!org) return <Box maxWidth={560}><Typography variant="h4" fontWeight={800} mb={2}>Create your workspace</Typography><TextField fullWidth label="Business name" value={name} onChange={e => setName(e.target.value)} /><Button sx={{ mt: 2 }} variant="contained" disabled={!name.trim()} onClick={async () => { try { await organizationApi.create(name); await load() } catch { toast.error('Could not create workspace') } }}>Create workspace</Button></Box>

  const webhookUrl = `${window.location.origin}${org.webhook_path}`
  return <Box maxWidth={760}>
    <Typography variant="h4" fontWeight={800} color="primary.dark">Workspace & Integrations</Typography>
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}><Typography color="text.secondary">{org.name} · {org.slug}</Typography>{organizations.length > 1 && <Select size="small" value={org.id} onChange={e => { localStorage.setItem('active_organization_id', e.target.value); window.location.reload() }}>{organizations.map(item => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</Select>}</Box>
    <Card sx={{ mb: 3 }}><CardContent><Typography variant="h6" fontWeight={700}>1. Razorpay connection</Typography><Typography variant="body2" color="text.secondary" mb={2}>Add the webhook URL below in Razorpay Dashboard → Webhooks, then save its signing secret here. Credentials are never displayed again.</Typography><TextField fullWidth label="Webhook URL (copy to Razorpay)" value={webhookUrl} InputProps={{ readOnly: true }} sx={{ mb: 2 }} /><Button variant="outlined" onClick={connectOAuth} sx={{ mb: 2 }}>Connect with Razorpay OAuth</Button><TextField fullWidth label="Razorpay Key ID" value={razorpay.key_id} onChange={e => setRazorpay({ ...razorpay, key_id: e.target.value })} sx={{ mb: 2 }} /><TextField fullWidth type="password" label="Razorpay Key Secret" value={razorpay.key_secret} onChange={e => setRazorpay({ ...razorpay, key_secret: e.target.value })} sx={{ mb: 2 }} /><TextField fullWidth type="password" label="Webhook signing secret" value={razorpay.webhook_secret} onChange={e => setRazorpay({ ...razorpay, webhook_secret: e.target.value })} /><Button sx={{ mt: 2 }} variant="contained" disabled={!razorpay.key_id || !razorpay.key_secret || !razorpay.webhook_secret} onClick={saveRazorpay}>Save Razorpay connection</Button></CardContent></Card>
    <Card sx={{ mb: 3 }}><CardContent><Typography variant="h6" fontWeight={700}>2. Team escalation alerts</Typography><TextField fullWidth label="Slack incoming-webhook URL" value={notifications.slack_webhook_url} onChange={e => setNotifications({ ...notifications, slack_webhook_url: e.target.value })} sx={{ mt: 2 }} /><Button sx={{ mt: 2 }} variant="contained" onClick={saveNotifications}>Save alert settings</Button></CardContent></Card>
    <Card><CardContent><Typography variant="h6" fontWeight={700}>3. Customer communications</Typography><Alert severity="info" sx={{ my: 2 }}>Email uses Resend. SMS and WhatsApp use Twilio. Only configure the providers you intend to use.</Alert><TextField fullWidth label="Email sender" value={communications.sender_email} onChange={e => setCommunications({ ...communications, sender_email: e.target.value })} sx={{ mb: 2 }} /><TextField fullWidth type="password" label="Resend API key" value={communications.resend_api_key} onChange={e => setCommunications({ ...communications, resend_api_key: e.target.value })} sx={{ mb: 2 }} /><Divider sx={{ my: 2 }} /><TextField fullWidth label="Twilio Account SID" value={communications.twilio_account_sid} onChange={e => setCommunications({ ...communications, twilio_account_sid: e.target.value })} sx={{ mb: 2 }} /><TextField fullWidth type="password" label="Twilio Auth Token" value={communications.twilio_auth_token} onChange={e => setCommunications({ ...communications, twilio_auth_token: e.target.value })} sx={{ mb: 2 }} /><TextField fullWidth label="Twilio SMS sender number" value={communications.twilio_from_number} onChange={e => setCommunications({ ...communications, twilio_from_number: e.target.value })} sx={{ mb: 2 }} /><TextField fullWidth label="Twilio WhatsApp sender" value={communications.twilio_whatsapp_from} onChange={e => setCommunications({ ...communications, twilio_whatsapp_from: e.target.value })} /><Button sx={{ mt: 2 }} variant="contained" onClick={saveCommunications}>Save communication settings</Button></CardContent></Card>
  </Box>
}

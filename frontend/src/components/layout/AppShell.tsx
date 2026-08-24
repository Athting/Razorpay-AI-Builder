import { Box } from '@mui/material'
import { Sidebar } from './Sidebar'
import { Outlet } from 'react-router-dom'

export function AppShell() {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', background: '#F8FAFF' }}>
      <Sidebar />
      <Box component="main" sx={{ flex: 1, overflow: 'auto', p: 3 }}>
        <Outlet />
      </Box>
    </Box>
  )
}

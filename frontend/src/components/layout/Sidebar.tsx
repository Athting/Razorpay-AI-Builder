import { useState } from 'react'
import {
  Box, Drawer, List, ListItemButton, ListItemIcon, ListItemText,
  Typography, Avatar, Divider, Button, Tooltip,
} from '@mui/material'
import {
  Dashboard, Assignment, Warning, Security, ManageSearch, Settings, Payment,
  Logout, ChevronLeft, ChevronRight,
} from '@mui/icons-material'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../auth/AuthProvider'

const NAV_ITEMS = [
  { label: 'Dashboard', icon: <Dashboard />, path: '/' },
  { label: 'Cases', icon: <Assignment />, path: '/cases' },
  { label: 'Escalations', icon: <Warning />, path: '/escalations' },
  { label: 'Compliance', icon: <Security />, path: '/compliance' },
  { label: 'Audit Trail', icon: <ManageSearch />, path: '/audit' },
  { label: 'Settings', icon: <Settings />, path: '/settings' },
  { label: 'Payment Links', icon: <Payment />, path: '/checkout' },
]

const DRAWER_WIDTH = 240
const COLLAPSED_WIDTH = 64

export function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, signOut } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const width = collapsed ? COLLAPSED_WIDTH : DRAWER_WIDTH

  return (
    <Drawer
      variant="permanent"
      sx={{
        width,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width,
          boxSizing: 'border-box',
          background: '#0C2451',
          color: 'white',
          border: 'none',
          transition: 'width 0.2s ease',
          overflow: 'hidden',
        },
      }}
    >
      {/* Brand */}
      <Box sx={{
        p: collapsed ? 1 : 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'initial',
        gap: 1.5,
        minHeight: 64,
      }}>
        {!collapsed && <Typography fontSize={22}>⚡</Typography>}
        {!collapsed && (
          <Typography fontWeight={800} fontSize={16} color="white" noWrap>
            RevRecov
          </Typography>
        )}
        <Box sx={{ flex: 1 }} />
        <Tooltip title={collapsed ? 'Expand' : 'Collapse'}>
          <Box
            onClick={() => setCollapsed(!collapsed)}
            sx={{ cursor: 'pointer', color: 'rgba(255,255,255,0.5)', '&:hover': { color: 'white' } }}
          >
            {collapsed ? <ChevronRight /> : <ChevronLeft />}
          </Box>
        </Tooltip>
      </Box>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />

      {/* Nav items */}
      <List sx={{ flex: 1, px: 1, py: 2 }}>
        {NAV_ITEMS.map(item => {
          const active = location.pathname === item.path ||
            (item.path !== '/' && location.pathname.startsWith(item.path))
          return (
            <Tooltip key={item.path} title={collapsed ? item.label : ''} placement="right">
              <ListItemButton
                onClick={() => navigate(item.path)}
                sx={{
                  borderRadius: 2, mb: 0.5,
                  background: active ? 'rgba(51,149,255,0.20)' : 'transparent',
                  '&:hover': { background: 'rgba(255,255,255,0.08)' },
                  minHeight: 44,
                  px: collapsed ? 1.5 : 2,
                }}
              >
                <ListItemIcon sx={{ color: active ? '#3395FF' : 'rgba(255,255,255,0.6)', minWidth: 36 }}>
                  {item.icon}
                </ListItemIcon>
                {!collapsed && (
                  <ListItemText
                    primary={item.label}
                    primaryTypographyProps={{
                      fontSize: '0.875rem',
                      fontWeight: active ? 600 : 400,
                      color: active ? 'white' : 'rgba(255,255,255,0.7)',
                    }}
                  />
                )}
              </ListItemButton>
            </Tooltip>
          )
        })}
      </List>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.1)' }} />

      {/* User */}
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar sx={{ width: 32, height: 32, bgcolor: '#3395FF', fontSize: 14 }}>
          {user?.name?.charAt(0).toUpperCase() || 'U'}
        </Avatar>
        {!collapsed && (
          <Box sx={{ flex: 1, overflow: 'hidden' }}>
            <Typography fontSize={13} fontWeight={600} color="white" noWrap>{user?.name}</Typography>
            <Typography fontSize={11} color="rgba(255,255,255,0.5)" noWrap>{user?.role}</Typography>
          </Box>
        )}
        {!collapsed && (
          <Tooltip title="Sign out">
            <Box onClick={signOut} sx={{ cursor: 'pointer', color: 'rgba(255,255,255,0.4)', '&:hover': { color: 'white' } }}>
              <Logout fontSize="small" />
            </Box>
          </Tooltip>
        )}
      </Box>
    </Drawer>
  )
}

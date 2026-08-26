import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import {
  AppBar, Toolbar, Typography, Drawer, List, ListItem, ListItemIcon,
  ListItemText, Box, IconButton, Avatar, Menu, MenuItem, Divider,
  Badge, useTheme, useMediaQuery
} from '@mui/material';
import {
  Menu as MenuIcon, Dashboard, ShowChart, Notifications,
  AccountCircle, Settings, Logout, AccountBalance,
  Speed, Assessment, Payment, SmartToy, Warning
} from '@mui/icons-material';
import { logout } from '../features/auth/authSlice';

const drawerWidth = 240;

const menuItems = [
  { text: 'Dashboard', icon: <Dashboard />, path: '/' },
  { text: 'Trading', icon: <ShowChart />, path: '/trading' },
  { text: 'Signals', icon: <Speed />, path: '/signals' },
  { text: 'Risk Management', icon: <Warning />, path: '/risk' },
  { text: 'Expert Advisors', icon: <SmartToy />, path: '/eas' },
  { text: 'Payments', icon: <Payment />, path: '/payments' },
  { text: 'Analytics', icon: <Assessment />, path: '/analytics' },
  { text: 'Settings', icon: <Settings />, path: '/settings' },
];

function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const { user } = useSelector((state) => state.auth);
  const { alerts } = useSelector((state) => state.risk);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleMenu = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    dispatch(logout());
    navigate('/login');
  };

  const drawer = (
    <Box sx={{ bgcolor: 'background.paper', height: '100%' }}>
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <AccountBalance sx={{ color: 'primary.main', fontSize: 32 }} />
        <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
          Dutchkem AI
        </Typography>
      </Box>
      <Divider />
      <List>
        {menuItems.map((item) => (
          <ListItem
            button
            key={item.text}
            onClick={() => {
              navigate(item.path);
              if (isMobile) handleDrawerToggle();
            }}
            sx={{
              bgcolor: location.pathname === item.path ? 'action.selected' : 'transparent',
              '&:hover': { bgcolor: 'action.hover' }
            }}
          >
            <ListItemIcon sx={{ color: location.pathname === item.path ? 'primary.main' : 'inherit' }}>
              {item.icon}
            </ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
          bgcolor: 'background.paper'
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap sx={{ flexGrow: 1 }}>
            {menuItems.find((item) => item.path === location.pathname)?.text || 'Dashboard'}
          </Typography>
          <IconButton color="inherit">
            <Badge badgeContent={alerts?.length || 0} color="error">
              <Notifications />
            </Badge>
          </IconButton>
          <IconButton onClick={handleMenu} sx={{ ml: 1 }}>
            <Avatar sx={{ bgcolor: 'primary.main' }}>
              {user?.username?.charAt(0).toUpperCase() || 'U'}
            </Avatar>
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleClose}
          >
            <MenuItem onClick={handleClose}>
              <ListItemIcon><AccountCircle /></ListItemIcon>
              Profile
            </MenuItem>
            <MenuItem onClick={() => { navigate('/settings'); handleClose(); }}>
              <ListItemIcon><Settings /></ListItemIcon>
              Settings
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon><Logout /></ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
      >
        {isMobile ? (
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={handleDrawerToggle}
            ModalProps={{ keepMounted: true }}
            sx={{
              '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth }
            }}
          >
            {drawer}
          </Drawer>
        ) : (
          <Drawer
            variant="permanent"
            sx={{
              '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth }
            }}
          >
            {drawer}
          </Drawer>
        )}
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          mt: '64px',
          minHeight: 'calc(100vh - 64px)',
          bgcolor: 'background.default'
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}

export default Layout;

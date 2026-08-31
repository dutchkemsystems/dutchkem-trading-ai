import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box, Grid, Paper, Typography, Card, CardContent, Button, TextField,
  Switch, FormControlLabel, Divider, Alert, Tabs, Tab, Avatar,
  List, ListItem, ListItemIcon, ListItemText, ListItemSecondaryAction, CircularProgress
} from '@mui/material';
import { Settings, Person, Security, Notifications, Link as LinkIcon } from '@mui/icons-material';
import { fetchProfile, updateProfile } from '../features/auth/authSlice';
import { authAPI } from '../services/api';

function Settings() {
  const dispatch = useDispatch();
  const { user } = useSelector((state) => state.auth);
  const [tabValue, setTabValue] = useState(0);
  const [profile, setProfile] = useState({ first_name: '', last_name: '', email: '', phone_number: '', country: '' });
  const [notifications, setNotifications] = useState({ emailTrades: true, emailSignals: true, emailRiskAlerts: true, pushTrades: true, pushSignals: true, pushRiskAlerts: true });
  const [mt5, setMt5] = useState({ mt5_account: '', mt5_server: '', mt5_password: '' });
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user) {
      setProfile({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
        phone_number: user.phone_number || '',
        country: user.country || '',
      });
      setMt5({ mt5_account: user.mt5_account || '', mt5_server: user.mt5_server || '', mt5_password: '' });
      setLoading(false);
    } else {
      dispatch(fetchProfile()).finally(() => setLoading(false));
    }
  }, [user, dispatch]);

  const handleSaveProfile = async () => {
    setSaving(true);
    setSaveMsg('');
    setError('');
    try {
      await dispatch(updateProfile(profile)).unwrap();
      setSaveMsg('Profile updated successfully');
    } catch (err) {
      setError(err || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleConnectMT5 = async () => {
    setSaving(true);
    setError('');
    try {
      await authAPI.connectMT5({ mt5_account: mt5.mt5_account, mt5_server: mt5.mt5_server });
      setSaveMsg('MT5 connection saved');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save MT5 connection');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px"><CircularProgress /></Box>;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        <Settings sx={{ mr: 1, verticalAlign: 'middle' }} />
        Settings
      </Typography>

      {saveMsg && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSaveMsg('')}>{saveMsg}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 3 }}>
          <Tab icon={<Person />} label="Profile" />
          <Tab icon={<Security />} label="Security" />
          <Tab icon={<Notifications />} label="Notifications" />
          <Tab icon={<LinkIcon />} label="MT5 Connection" />
        </Tabs>

        {tabValue === 0 && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Avatar sx={{ width: 100, height: 100, mx: 'auto', mb: 2, bgcolor: 'primary.main' }}>
                    {profile.first_name?.charAt(0) || 'U'}
                  </Avatar>
                  <Typography variant="h6">{profile.first_name} {profile.last_name}</Typography>
                  <Typography color="textSecondary">@{user?.username}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={8}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Profile Information</Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <TextField fullWidth label="First Name" value={profile.first_name}
                        onChange={(e) => setProfile({ ...profile, first_name: e.target.value })} />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField fullWidth label="Last Name" value={profile.last_name}
                        onChange={(e) => setProfile({ ...profile, last_name: e.target.value })} />
                    </Grid>
                    <Grid item xs={12}>
                      <TextField fullWidth label="Email" value={profile.email}
                        onChange={(e) => setProfile({ ...profile, email: e.target.value })} />
                    </Grid>
                    <Grid item xs={12}>
                      <TextField fullWidth label="Phone" value={profile.phone_number}
                        onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })} />
                    </Grid>
                    <Grid item xs={12}>
                      <Button variant="contained" onClick={handleSaveProfile} disabled={saving}>
                        {saving ? 'Saving...' : 'Save Changes'}
                      </Button>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {tabValue === 1 && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Security Settings</Typography>
              <List>
                <ListItem>
                  <ListItemIcon><Security /></ListItemIcon>
                  <ListItemText primary="Two-Factor Authentication"
                    secondary={user?.mfa_enabled ? 'Enabled' : 'Add an extra layer of security'} />
                  <ListItemSecondaryAction>
                    <Switch edge="end" checked={user?.mfa_enabled || false} disabled />
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemText primary="Active Sessions" secondary="Manage your active sessions" />
                  <Button variant="outlined" size="small" onClick={async () => {
                    try {
                      const { data } = await authAPI.getSessions();
                      setSaveMsg(`${data.length || 0} active sessions`);
                    } catch { setError('Failed to check sessions'); }
                  }}>Check</Button>
                </ListItem>
              </List>
            </CardContent>
          </Card>
        )}

        {tabValue === 2 && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Notification Preferences</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" gutterBottom>Email Notifications</Typography>
                  <FormControlLabel control={<Switch checked={notifications.emailTrades}
                    onChange={(e) => setNotifications({ ...notifications, emailTrades: e.target.checked })} />} label="Trade Alerts" />
                  <FormControlLabel control={<Switch checked={notifications.emailSignals}
                    onChange={(e) => setNotifications({ ...notifications, emailSignals: e.target.checked })} />} label="Signal Alerts" />
                  <FormControlLabel control={<Switch checked={notifications.emailRiskAlerts}
                    onChange={(e) => setNotifications({ ...notifications, emailRiskAlerts: e.target.checked })} />} label="Risk Alerts" />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" gutterBottom>Push Notifications</Typography>
                  <FormControlLabel control={<Switch checked={notifications.pushTrades}
                    onChange={(e) => setNotifications({ ...notifications, pushTrades: e.target.checked })} />} label="Trade Alerts" />
                  <FormControlLabel control={<Switch checked={notifications.pushSignals}
                    onChange={(e) => setNotifications({ ...notifications, pushSignals: e.target.checked })} />} label="Signal Alerts" />
                  <FormControlLabel control={<Switch checked={notifications.pushRiskAlerts}
                    onChange={(e) => setNotifications({ ...notifications, pushRiskAlerts: e.target.checked })} />} label="Risk Alerts" />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        )}

        {tabValue === 3 && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>MetaTrader 5 Connection</Typography>
              <Alert severity="info" sx={{ mb: 2 }}>
                {user?.mt5_account ? `Connected to ${user.mt5_server} (Account: ${user.mt5_account})` : 'Connect your MT5 account to enable live trading.'}
              </Alert>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField fullWidth label="MT5 Account Number" value={mt5.mt5_account}
                    onChange={(e) => setMt5({ ...mt5, mt5_account: e.target.value })} />
                </Grid>
                <Grid item xs={12}>
                  <TextField fullWidth label="Server" value={mt5.mt5_server}
                    onChange={(e) => setMt5({ ...mt5, mt5_server: e.target.value })} />
                </Grid>
                <Grid item xs={12}>
                  <Button variant="contained" onClick={handleConnectMT5} disabled={saving}>
                    {saving ? 'Saving...' : 'Connect'}
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        )}
      </Paper>
    </Box>
  );
}

export default Settings;

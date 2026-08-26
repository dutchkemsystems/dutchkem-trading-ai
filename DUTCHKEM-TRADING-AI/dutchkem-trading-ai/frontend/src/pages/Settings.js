import React, { useState } from 'react';
import {
  Box, Grid, Paper, Typography, Card, CardContent, Button, TextField,
  Switch, FormControlLabel, Divider, Alert, Tabs, Tab, Avatar,
  List, ListItem, ListItemIcon, ListItemText, ListItemSecondaryAction
} from '@mui/material';
import {
  Settings, Person, Security, Notifications, Payment, Link as LinkIcon
} from '@mui/icons-material';

function Settings() {
  const [tabValue, setTabValue] = useState(0);

  const [profile, setProfile] = useState({
    username: 'trader123',
    email: 'trader@example.com',
    firstName: 'John',
    lastName: 'Doe',
    phone: '+1234567890',
  });

  const [notifications, setNotifications] = useState({
    emailTrades: true,
    emailSignals: true,
    emailRiskAlerts: true,
    pushTrades: true,
    pushSignals: true,
    pushRiskAlerts: true,
    smsRiskAlerts: false,
  });

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        <Settings sx={{ mr: 1, verticalAlign: 'middle' }} />
        Settings
      </Typography>

      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 3 }}>
          <Tab icon={<Person />} label="Profile" />
          <Tab icon={<Security />} label="Security" />
          <Tab icon={<Notifications />} label="Notifications" />
          <Tab icon={<LinkIcon />} label="MT5 Connection" />
          <Tab icon={<Payment />} label="Payment Methods" />
        </Tabs>

        {tabValue === 0 && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Avatar sx={{ width: 100, height: 100, mx: 'auto', mb: 2, bgcolor: 'primary.main' }}>
                    {profile.firstName.charAt(0)}
                  </Avatar>
                  <Typography variant="h6">{profile.firstName} {profile.lastName}</Typography>
                  <Typography color="textSecondary">@{profile.username}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={8}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Profile Information</Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <TextField
                        fullWidth
                        label="First Name"
                        value={profile.firstName}
                        onChange={(e) => setProfile({ ...profile, firstName: e.target.value })}
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        fullWidth
                        label="Last Name"
                        value={profile.lastName}
                        onChange={(e) => setProfile({ ...profile, lastName: e.target.value })}
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="Email"
                        value={profile.email}
                        onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <TextField
                        fullWidth
                        label="Phone"
                        value={profile.phone}
                        onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <Button variant="contained">Save Changes</Button>
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
                  <ListItemText
                    primary="Two-Factor Authentication"
                    secondary="Add an extra layer of security to your account"
                  />
                  <ListItemSecondaryAction>
                    <Switch edge="end" />
                  </ListItemSecondaryAction>
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemIcon><Lock /></ListItemIcon>
                  <ListItemText
                    primary="Change Password"
                    secondary="Last changed 30 days ago"
                  />
                  <Button variant="outlined" size="small">Change</Button>
                </ListItem>
                <Divider />
                <ListItem>
                  <ListItemIcon><LinkIcon /></ListItemIcon>
                  <ListItemText
                    primary="Active Sessions"
                    secondary="2 devices connected"
                  />
                  <Button variant="outlined" size="small" color="error">Revoke All</Button>
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
                  <FormControlLabel
                    control={<Switch checked={notifications.emailTrades} onChange={(e) => setNotifications({ ...notifications, emailTrades: e.target.checked })} />}
                    label="Trade Alerts"
                  />
                  <FormControlLabel
                    control={<Switch checked={notifications.emailSignals} onChange={(e) => setNotifications({ ...notifications, emailSignals: e.target.checked })} />}
                    label="Signal Alerts"
                  />
                  <FormControlLabel
                    control={<Switch checked={notifications.emailRiskAlerts} onChange={(e) => setNotifications({ ...notifications, emailRiskAlerts: e.target.checked })} />}
                    label="Risk Alerts"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" gutterBottom>Push Notifications</Typography>
                  <FormControlLabel
                    control={<Switch checked={notifications.pushTrades} onChange={(e) => setNotifications({ ...notifications, pushTrades: e.target.checked })} />}
                    label="Trade Alerts"
                  />
                  <FormControlLabel
                    control={<Switch checked={notifications.pushSignals} onChange={(e) => setNotifications({ ...notifications, pushSignals: e.target.checked })} />}
                    label="Signal Alerts"
                  />
                  <FormControlLabel
                    control={<Switch checked={notifications.pushRiskAlerts} onChange={(e) => setNotifications({ ...notifications, pushRiskAlerts: e.target.checked })} />}
                    label="Risk Alerts"
                  />
                </Grid>
                <Grid item xs={12}>
                  <Button variant="contained">Save Preferences</Button>
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
                Connect your MT5 account to enable live trading and EA deployment.
              </Alert>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField fullWidth label="MT5 Account Number" />
                </Grid>
                <Grid item xs={12}>
                  <TextField fullWidth label="Server" />
                </Grid>
                <Grid item xs={12}>
                  <TextField fullWidth label="Password" type="password" />
                </Grid>
                <Grid item xs={12}>
                  <Button variant="contained">Connect</Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        )}

        {tabValue === 4 && (
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Payment Methods</Typography>
              <Alert severity="info">
                Manage your saved payment methods for quick deposits and withdrawals.
              </Alert>
            </CardContent>
          </Card>
        )}
      </Paper>
    </Box>
  );
}

export default Settings;

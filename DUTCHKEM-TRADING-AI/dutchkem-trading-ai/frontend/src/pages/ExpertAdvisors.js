import React, { useState, useEffect } from 'react';
import {
  Box, Grid, Paper, Typography, Card, CardContent, Button, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  FormControl, InputLabel, Select, MenuItem, Alert, Tabs, Tab, CircularProgress
} from '@mui/material';
import { SmartToy, Add, PlayArrow, Stop, Code } from '@mui/icons-material';
import { easAPI } from '../services/api';

function ExpertAdvisors() {
  const [tabValue, setTabValue] = useState(0);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [eas, setEas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newEA, setNewEA] = useState({ name: '', symbol: 'EURUSD', timeframe: 'H1', strategy_type: 'scalping', risk_per_trade: 1 });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { fetchEAs(); }, []);

  const fetchEAs = async () => {
    try {
      const { data } = await easAPI.getEAs();
      setEas(data.results || data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch EAs');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEA = async () => {
    setSubmitting(true);
    try {
      await easAPI.createEA(newEA);
      setCreateDialogOpen(false);
      fetchEAs();
      setNewEA({ name: '', symbol: 'EURUSD', timeframe: 'H1', strategy_type: 'scalping', risk_per_trade: 1 });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create EA');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeployEA = async (eaId) => {
    try {
      await easAPI.deployEA(eaId);
      fetchEAs();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to deploy EA');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'LIVE': return 'success';
      case 'PAUSED': return 'warning';
      case 'BACKTESTING': return 'info';
      default: return 'default';
    }
  };

  if (loading) {
    return <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px"><CircularProgress /></Box>;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        <SmartToy sx={{ mr: 1, verticalAlign: 'middle' }} />
        Expert Advisors
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Total EAs</Typography>
              <Typography variant="h4">{eas.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Active (Live)</Typography>
              <Typography variant="h4" color="success.main">
                {eas.filter((ea) => ea.status === 'LIVE').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Total Profit</Typography>
              <Typography variant="h4" color="success.main">
                ${eas.reduce((sum, ea) => sum + (ea.profit || 0), 0).toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Button variant="contained" fullWidth startIcon={<Add />}
                onClick={() => setCreateDialogOpen(true)}>
                Create EA
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
          <Tab label="My EAs" />
          <Tab label="Marketplace" />
        </Tabs>

        {tabValue === 0 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Timeframe</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Trades</TableCell>
                  <TableCell>Win Rate</TableCell>
                  <TableCell>Profit</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {eas.map((ea) => (
                  <TableRow key={ea.id}>
                    <TableCell>{ea.name}</TableCell>
                    <TableCell>{ea.symbol?.name || ea.symbol}</TableCell>
                    <TableCell>{ea.timeframe?.code || ea.timeframe}</TableCell>
                    <TableCell>
                      <Chip label={ea.status} color={getStatusColor(ea.status)} size="small" />
                    </TableCell>
                    <TableCell>{ea.total_trades || 0}</TableCell>
                    <TableCell>{ea.win_rate || 0}%</TableCell>
                    <TableCell color={(ea.profit || 0) >= 0 ? 'success.main' : 'error.main'}>
                      ${(ea.profit || 0).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {ea.status !== 'LIVE' && (
                        <Button size="small" color="success" startIcon={<PlayArrow />}
                          onClick={() => handleDeployEA(ea.id)}>Start</Button>
                      )}
                      <Button size="small" startIcon={<Code />}>Code</Button>
                    </TableCell>
                  </TableRow>
                ))}
                {eas.length === 0 && (
                  <TableRow><TableCell colSpan={8} align="center">No expert advisors created yet</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {tabValue === 1 && (
          <Alert severity="info">EA Marketplace coming soon!</Alert>
        )}
      </Paper>

      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Expert Advisor</DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" label="EA Name" fullWidth variant="outlined" value={newEA.name}
            onChange={(e) => setNewEA({ ...newEA, name: e.target.value })} />
          <FormControl fullWidth margin="dense">
            <InputLabel>Symbol</InputLabel>
            <Select label="Symbol" value={newEA.symbol}
              onChange={(e) => setNewEA({ ...newEA, symbol: e.target.value })}>
              <MenuItem value="EURUSD">EURUSD</MenuItem>
              <MenuItem value="GBPUSD">GBPUSD</MenuItem>
              <MenuItem value="USDJPY">USDJPY</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth margin="dense">
            <InputLabel>Timeframe</InputLabel>
            <Select label="Timeframe" value={newEA.timeframe}
              onChange={(e) => setNewEA({ ...newEA, timeframe: e.target.value })}>
              {['M5', 'M15', 'M30', 'H1', 'H2', 'H4'].map((tf) => (
                <MenuItem key={tf} value={tf}>{tf}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth margin="dense">
            <InputLabel>Strategy Type</InputLabel>
            <Select label="Strategy Type" value={newEA.strategy_type}
              onChange={(e) => setNewEA({ ...newEA, strategy_type: e.target.value })}>
              {['scalping', 'momentum', 'swing', 'trend', 'position', 'strategic'].map((s) => (
                <MenuItem key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField margin="dense" label="Risk per Trade (%)" type="number" fullWidth variant="outlined"
            value={newEA.risk_per_trade}
            onChange={(e) => setNewEA({ ...newEA, risk_per_trade: parseFloat(e.target.value) })} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="secondary">Generate with AI</Button>
          <Button variant="contained" onClick={handleCreateEA} disabled={submitting || !newEA.name}>
            {submitting ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ExpertAdvisors;

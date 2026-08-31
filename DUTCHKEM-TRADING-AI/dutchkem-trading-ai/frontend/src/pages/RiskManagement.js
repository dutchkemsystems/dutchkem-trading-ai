import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box, Grid, Paper, Typography, Card, CardContent, LinearProgress,
  Alert, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Chip, CircularProgress
} from '@mui/material';
import { Warning, TrendingDown, TrendingUp, Speed } from '@mui/icons-material';
import { fetchRiskDashboard, fetchRiskAlerts } from '../features/risk/riskSlice';

function RiskManagement() {
  const dispatch = useDispatch();
  const { dashboard, alerts, loading, error } = useSelector((state) => state.risk);

  useEffect(() => {
    dispatch(fetchRiskDashboard());
    dispatch(fetchRiskAlerts());
  }, [dispatch]);

  if (loading && !dashboard) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const riskParams = dashboard?.risk_parameters || {};
  const currentStatus = dashboard?.current_status || {};
  const circuitBreakers = dashboard?.circuit_breakers || {};

  const riskLimits = [
    { name: 'Max Daily Loss', current: Math.abs(currentStatus.daily_pnl_percent || 0), limit: riskParams.max_daily_loss || 2, unit: '%', status: Math.abs(currentStatus.daily_pnl_percent || 0) >= (riskParams.max_daily_loss || 2) ? 'danger' : Math.abs(currentStatus.daily_pnl_percent || 0) >= (riskParams.max_daily_loss || 2) * 0.5 ? 'warning' : 'ok' },
    { name: 'Max Drawdown', current: currentStatus.drawdown_percent || 0, limit: riskParams.max_drawdown || 15, unit: '%', status: (currentStatus.drawdown_percent || 0) >= (riskParams.max_drawdown || 15) ? 'danger' : (currentStatus.drawdown_percent || 0) >= (riskParams.max_drawdown || 15) * 0.5 ? 'warning' : 'ok' },
    { name: 'Daily Target', current: currentStatus.daily_pnl_percent || 0, limit: riskParams.daily_growth_target || 0.14, unit: '%', status: (currentStatus.daily_pnl_percent || 0) >= (riskParams.daily_growth_target || 0.14) ? 'ok' : 'warning' },
    { name: 'Daily Trades', current: currentStatus.daily_trades_count || 0, limit: riskParams.max_daily_trades || 10, unit: '', status: (currentStatus.daily_trades_count || 0) >= (riskParams.max_daily_trades || 10) ? 'danger' : 'ok' },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'ok': return 'success';
      case 'warning': return 'warning';
      case 'danger': return 'error';
      default: return 'info';
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        <Warning sx={{ mr: 1, verticalAlign: 'middle' }} />
        Risk Management
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {!circuitBreakers.daily_loss_active && !circuitBreakers.max_drawdown_active ? (
        <Alert severity="success" sx={{ mb: 3 }}>All systems normal. Trading is allowed.</Alert>
      ) : (
        <Alert severity="error" sx={{ mb: 3 }}>Circuit breaker triggered! Trading has been stopped.</Alert>
      )}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Daily P&L</Typography>
              <Typography variant="h5" color={(currentStatus.daily_pnl_percent || 0) >= 0 ? 'success.main' : 'error.main'}>
                {Number(currentStatus.daily_pnl_percent || 0).toFixed(2)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Drawdown</Typography>
              <Typography variant="h5" color={(currentStatus.drawdown_percent || 0) > 10 ? 'error.main' : 'inherit'}>
                {Number(currentStatus.drawdown_percent || 0).toFixed(2)}%
              </Typography>
              <LinearProgress variant="determinate"
                value={Math.min((currentStatus.drawdown_percent || 0) / (riskParams.max_drawdown || 15) * 100, 100)}
                color={(currentStatus.drawdown_percent || 0) > 10 ? 'error' : 'primary'}
                sx={{ mt: 1 }} />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Daily Loss Remaining</Typography>
              <Typography variant="h5" color={(currentStatus.daily_loss_remaining || 2) < 0.5 ? 'error.main' : 'success.main'}>
                {Number(currentStatus.daily_loss_remaining || 2).toFixed(2)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Daily Trades</Typography>
              <Typography variant="h5">{currentStatus.daily_trades_count || 0} / {riskParams.max_daily_trades || 10}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Risk Limits</Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Limit</TableCell>
                    <TableCell>Current</TableCell>
                    <TableCell>Maximum</TableCell>
                    <TableCell>Progress</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {riskLimits.map((limit) => (
                    <TableRow key={limit.name}>
                      <TableCell>{limit.name}</TableCell>
                      <TableCell>{limit.current.toFixed(2)}{limit.unit}</TableCell>
                      <TableCell>{limit.limit}{limit.unit}</TableCell>
                      <TableCell>
                        <LinearProgress variant="determinate"
                          value={Math.min((limit.current / limit.limit) * 100, 100)}
                          color={getStatusColor(limit.status)}
                          sx={{ width: 150 }} />
                      </TableCell>
                      <TableCell>
                        <Chip label={limit.status.toUpperCase()} color={getStatusColor(limit.status)} size="small" />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Recent Alerts</Typography>
            {(alerts || []).slice(0, 5).map((alert, index) => (
              <Alert key={alert.id || index} severity={alert.severity?.toLowerCase() || 'info'} sx={{ mb: 1 }}>
                <Typography variant="body2">{alert.message}</Typography>
                <Typography variant="caption" color="textSecondary">
                  {alert.created_at ? new Date(alert.created_at).toLocaleString() : ''}
                </Typography>
              </Alert>
            ))}
            {(!alerts || alerts.length === 0) && (
              <Typography color="textSecondary" align="center">No recent alerts</Typography>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>Circuit Breakers</Typography>
        <Box display="flex" gap={2}>
          <Chip label="Daily Loss Limit" color={circuitBreakers.daily_loss_active ? 'error' : 'success'} variant="outlined" />
          <Chip label="Max Drawdown" color={circuitBreakers.max_drawdown_active ? 'error' : 'success'} variant="outlined" />
          <Chip label="Daily Trade Limit" color={circuitBreakers.daily_trades_active ? 'error' : 'success'} variant="outlined" />
        </Box>
      </Paper>
    </Box>
  );
}

export default RiskManagement;

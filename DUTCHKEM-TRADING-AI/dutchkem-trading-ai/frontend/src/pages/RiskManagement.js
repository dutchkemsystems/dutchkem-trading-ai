import React from 'react';
import {
  Box, Grid, Paper, Typography, Card, CardContent, LinearProgress,
  Alert, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Chip
} from '@mui/material';
import { Warning, TrendingDown, TrendingUp, Speed } from '@mui/icons-material';

function RiskManagement() {
  const riskStatus = {
    equity: 10450.25,
    peakEquity: 10500.00,
    drawdown: 0.47,
    dailyPnl: 320.50,
    dailyPnlPercent: 0.31,
    dailyTrades: 3,
    isCircuitBreakerTriggered: false,
  };

  const riskLimits = [
    { name: 'Max Daily Loss', current: 0.5, limit: 2, unit: '%', status: 'ok' },
    { name: 'Max Drawdown', current: 0.47, limit: 15, unit: '%', status: 'ok' },
    { name: 'Daily Target', current: 0.31, limit: 0.4, unit: '%', status: 'warning' },
    { name: 'Daily Trades', current: 3, limit: 10, unit: '', status: 'ok' },
    { name: 'Position Size', current: 1, limit: 1, unit: '%', status: 'ok' },
  ];

  const recentAlerts = [
    { type: 'INFO', message: 'Daily target reached 77.5%', time: '10 min ago', severity: 'info' },
    { type: 'WARNING', message: 'Position size at 80% of limit', time: '1 hour ago', severity: 'warning' },
    { type: 'SUCCESS', message: 'Trade closed with +$45 profit', time: '2 hours ago', severity: 'success' },
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

      {/* Circuit Breaker Status */}
      {!riskStatus.isCircuitBreakerTriggered ? (
        <Alert severity="success" sx={{ mb: 3 }}>
          All systems normal. Trading is allowed.
        </Alert>
      ) : (
        <Alert severity="error" sx={{ mb: 3 }}>
          Circuit breaker triggered! Trading has been stopped.
        </Alert>
      )}

      {/* Risk Status Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Current Equity</Typography>
              <Typography variant="h5">${riskStatus.equity.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Peak Equity</Typography>
              <Typography variant="h5">${riskStatus.peakEquity.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Drawdown</Typography>
              <Typography variant="h5" color={riskStatus.drawdown > 10 ? 'error.main' : 'inherit'}>
                {riskStatus.drawdown}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={(riskStatus.drawdown / 15) * 100}
                color={riskStatus.drawdown > 10 ? 'error' : 'primary'}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Daily P&L</Typography>
              <Typography variant="h5" color={riskStatus.dailyPnl >= 0 ? 'success.main' : 'error.main'}>
                ${riskStatus.dailyPnl} ({riskStatus.dailyPnlPercent}%)
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Risk Limits */}
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
                      <TableCell>{limit.current}{limit.unit}</TableCell>
                      <TableCell>{limit.limit}{limit.unit}</TableCell>
                      <TableCell>
                        <LinearProgress
                          variant="determinate"
                          value={(limit.current / limit.limit) * 100}
                          color={getStatusColor(limit.status)}
                          sx={{ width: 150 }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={limit.status.toUpperCase()}
                          color={getStatusColor(limit.status)}
                          size="small"
                        />
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
            {recentAlerts.map((alert, index) => (
              <Alert key={index} severity={alert.severity} sx={{ mb: 1 }}>
                <Typography variant="body2">{alert.message}</Typography>
                <Typography variant="caption" color="textSecondary">{alert.time}</Typography>
              </Alert>
            ))}
          </Paper>
        </Grid>
      </Grid>

      {/* Daily Performance */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>Daily Performance</Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Win Rate</Typography>
                <Typography variant="h4" color="success.main">62%</Typography>
                <Typography variant="body2" color="textSecondary">5 wins / 3 losses</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Risk-Reward Ratio</Typography>
                <Typography variant="h4">1:2.3</Typography>
                <Typography variant="body2" color="textSecondary">Avg Win: $45 / Avg Loss: $20</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card>
              <CardContent>
                <Typography color="textSecondary">Profit Factor</Typography>
                <Typography variant="h4" color="success.main">2.8</Typography>
                <Typography variant="body2" color="textSecondary">Total Win / Total Loss</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
}

export default RiskManagement;

import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box, Grid, Paper, Typography, Card, CardContent, CardHeader,
  LinearProgress, Chip, Alert, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow
} from '@mui/material';
import {
  TrendingUp, TrendingDown, AccountBalance, Warning,
  Speed, SmartToy, Payment
} from '@mui/icons-material';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area
} from 'recharts';
import { setDrawdownStatus, setDailyPerformance } from '../features/risk/riskSlice';
import { setPortfolio } from '../features/trading/tradingSlice';

// Mock data for charts
const equityCurve = [
  { time: '00:00', equity: 10000 },
  { time: '04:00', equity: 10050 },
  { time: '08:00', equity: 10120 },
  { time: '12:00', equity: 10080 },
  { time: '16:00', equity: 10180 },
  { time: '20:00', equity: 10250 },
  { time: '24:00', equity: 10320 },
];

const dailyPnL = [
  { day: 'Mon', pnl: 0.12 },
  { day: 'Tue', pnl: 0.18 },
  { day: 'Wed', pnl: -0.05 },
  { day: 'Thu', pnl: 0.15 },
  { day: 'Fri', pnl: 0.22 },
];

function Dashboard() {
  const dispatch = useDispatch();
  const { drawdownStatus, dailyPerformance } = useSelector((state) => state.risk);
  const { portfolio } = useSelector((state) => state.trading);
  const { activeSignals } = useSelector((state) => state.signals);

  // Mock portfolio data
  const mockPortfolio = {
    balance: 10320.50,
    equity: 10450.25,
    margin: 500.00,
    freeMargin: 9950.25,
    unrealizedPnl: 129.75,
    dailyPnl: 320.50,
    dailyPnlPercent: 0.31,
    drawdown: 2.5,
  };

  const mockSignals = [
    { symbol: 'EURUSD', direction: 'LONG', score: 85, timeframe: 'H1' },
    { symbol: 'GBPUSD', direction: 'SHORT', score: 72, timeframe: 'M15' },
    { symbol: 'USDJPY', direction: 'LONG', score: 68, timeframe: 'H4' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Trading Dashboard
      </Typography>

      {/* Daily Performance Alert */}
      {mockPortfolio.dailyPnlPercent >= 0.4 && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Daily target reached! Trading stopped at {mockPortfolio.dailyPnlPercent}% gain.
        </Alert>
      )}

      {/* Portfolio Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <AccountBalance sx={{ color: 'primary.main', mr: 1 }} />
                <Typography color="textSecondary">Balance</Typography>
              </Box>
              <Typography variant="h5">${mockPortfolio.balance.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <TrendingUp sx={{ color: 'success.main', mr: 1 }} />
                <Typography color="textSecondary">Equity</Typography>
              </Box>
              <Typography variant="h5">${mockPortfolio.equity.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                {mockPortfolio.dailyPnl >= 0 ? (
                  <TrendingUp sx={{ color: 'success.main', mr: 1 }} />
                ) : (
                  <TrendingDown sx={{ color: 'error.main', mr: 1 }} />
                )}
                <Typography color="textSecondary">Daily P&L</Typography>
              </Box>
              <Typography variant="h5" color={mockPortfolio.dailyPnl >= 0 ? 'success.main' : 'error.main'}>
                ${mockPortfolio.dailyPnl.toLocaleString()} ({mockPortfolio.dailyPnlPercent}%)
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Warning sx={{ color: mockPortfolio.drawdown > 10 ? 'error.main' : 'warning.main', mr: 1 }} />
                <Typography color="textSecondary">Drawdown</Typography>
              </Box>
              <Typography variant="h5" color={mockPortfolio.drawdown > 10 ? 'error.main' : 'inherit'}>
                {mockPortfolio.drawdown}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={mockPortfolio.drawdown}
                color={mockPortfolio.drawdown > 10 ? 'error' : 'primary'}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Equity Curve</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={equityCurve}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="time" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1a2940', border: '1px solid #333' }}
                />
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="#1976d2"
                  fill="rgba(25, 118, 210, 0.3)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Daily P&L</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyPnL}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="day" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1a2940', border: '1px solid #333' }}
                />
                <Line
                  type="monotone"
                  dataKey="pnl"
                  stroke="#4caf50"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

      {/* Active Signals and Risk Status */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              <Speed sx={{ mr: 1, verticalAlign: 'middle' }} />
              Active Signals
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Symbol</TableCell>
                    <TableCell>Direction</TableCell>
                    <TableCell>Score</TableCell>
                    <TableCell>Timeframe</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mockSignals.map((signal, index) => (
                    <TableRow key={index}>
                      <TableCell>{signal.symbol}</TableCell>
                      <TableCell>
                        <Chip
                          label={signal.direction}
                          color={signal.direction === 'LONG' ? 'success' : 'error'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{signal.score}%</TableCell>
                      <TableCell>{signal.timeframe}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              <Warning sx={{ mr: 1, verticalAlign: 'middle' }} />
              Risk Status
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Daily Loss Limit</Typography>
                <Typography variant="body2">0.5% / 2%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={25} color="success" />
            </Box>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Daily Trades</Typography>
                <Typography variant="body2">3 / 10</Typography>
              </Box>
              <LinearProgress variant="determinate" value={30} />
            </Box>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Daily Target</Typography>
                <Typography variant="body2">0.31% / 0.4%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={77.5} color="warning" />
            </Box>
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Max Drawdown</Typography>
                <Typography variant="body2">2.5% / 15%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={16.7} />
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard;

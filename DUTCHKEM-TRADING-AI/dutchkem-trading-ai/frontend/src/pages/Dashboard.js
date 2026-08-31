import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box, Grid, Paper, Typography, Card, CardContent,
  LinearProgress, Chip, Alert, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, CircularProgress
} from '@mui/material';
import {
  TrendingUp, TrendingDown, AccountBalance, Warning, Speed
} from '@mui/icons-material';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area
} from 'recharts';
import { fetchPortfolio, fetchPositions } from '../features/trading/tradingSlice';
import { fetchActiveSignals } from '../features/signals/signalsSlice';
import { fetchDrawdownStatus, fetchDailyPerformance } from '../features/risk/riskSlice';
import { fetchLivePrices } from '../features/market/marketSlice';

function Dashboard() {
  const dispatch = useDispatch();
  const { portfolio, positions, loading: tradingLoading } = useSelector((state) => state.trading);
  const { activeSignals } = useSelector((state) => state.signals);
  const { drawdownStatus, dailyPerformance } = useSelector((state) => state.risk);
  const { livePrices } = useSelector((state) => state.market);
  const [equityCurve, setEquityCurve] = useState([]);
  const [dailyPnL, setDailyPnL] = useState([]);

  useEffect(() => {
    dispatch(fetchPortfolio());
    dispatch(fetchPositions());
    dispatch(fetchActiveSignals());
    dispatch(fetchDrawdownStatus());
    dispatch(fetchDailyPerformance());
    dispatch(fetchLivePrices());
  }, [dispatch]);

  useEffect(() => {
    if (dailyPerformance?.daily_pnl) {
      setDailyPnL(dailyPerformance.daily_pnl.map((d) => ({
        day: new Date(d.date).toLocaleDateString('en', { weekday: 'short' }),
        pnl: d.pnl,
      })));
    }
  }, [dailyPerformance]);

  useEffect(() => {
    if (portfolio?.equity_history) {
      setEquityCurve(portfolio.equity_history.map((e) => ({
        time: new Date(e.timestamp).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' }),
        equity: parseFloat(e.equity),
      })));
    }
  }, [portfolio]);

  const balance = portfolio?.balance || 0;
  const equity = portfolio?.equity || 0;
  const margin = portfolio?.margin || 0;
  const freeMargin = portfolio?.free_margin || 0;
  const unrealizedPnl = portfolio?.unrealized_pnl || 0;
  const dailyPnl = dailyPerformance?.today?.total_pnl || 0;
  const dailyPnlPercent = dailyPerformance?.today?.daily_growth_percent || 0;
  const drawdown = drawdownStatus?.drawdown_percent || 0;
  const dailyTarget = dailyPerformance?.risk_parameters?.daily_growth_target || 0.14;

  if (tradingLoading && !portfolio) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Trading Dashboard
      </Typography>

      {dailyPnlPercent >= dailyTarget && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Daily target reached! Trading stopped at {dailyPnlPercent.toFixed(2)}% gain.
        </Alert>
      )}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <AccountBalance sx={{ color: 'primary.main', mr: 1 }} />
                <Typography color="textSecondary">Balance</Typography>
              </Box>
              <Typography variant="h5">${Number(balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}</Typography>
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
              <Typography variant="h5">${Number(equity).toLocaleString(undefined, { minimumFractionDigits: 2 })}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                {dailyPnl >= 0 ? (
                  <TrendingUp sx={{ color: 'success.main', mr: 1 }} />
                ) : (
                  <TrendingDown sx={{ color: 'error.main', mr: 1 }} />
                )}
                <Typography color="textSecondary">Daily P&L</Typography>
              </Box>
              <Typography variant="h5" color={dailyPnl >= 0 ? 'success.main' : 'error.main'}>
                ${Number(dailyPnl).toFixed(2)} ({Number(unrealizedPnl).toFixed(2)})
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Warning sx={{ color: drawdown > 10 ? 'error.main' : 'warning.main', mr: 1 }} />
                <Typography color="textSecondary">Drawdown</Typography>
              </Box>
              <Typography variant="h5" color={drawdown > 10 ? 'error.main' : 'inherit'}>
                {Number(drawdown).toFixed(2)}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(drawdown / 15 * 100, 100)}
                color={drawdown > 10 ? 'error' : 'primary'}
                sx={{ mt: 1 }}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Equity Curve</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={equityCurve}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="time" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip contentStyle={{ backgroundColor: '#1a2940', border: '1px solid #333' }} />
                <Area type="monotone" dataKey="equity" stroke="#1976d2" fill="rgba(25, 118, 210, 0.3)" />
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
                <Tooltip contentStyle={{ backgroundColor: '#1a2940', border: '1px solid #333' }} />
                <Line type="monotone" dataKey="pnl" stroke="#4caf50" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>

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
                  {(activeSignals || []).map((signal, index) => (
                    <TableRow key={signal.id || index}>
                      <TableCell>{signal.symbol?.name || signal.symbol}</TableCell>
                      <TableCell>
                        <Chip
                          label={signal.signal_type || signal.direction}
                          color={(signal.signal_type || signal.direction) === 'BUY' || (signal.signal_type || signal.direction) === 'LONG' ? 'success' : 'error'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{signal.strength || signal.score}%</TableCell>
                      <TableCell>{signal.timeframe?.code || signal.timeframe}</TableCell>
                    </TableRow>
                  ))}
                  {(!activeSignals || activeSignals.length === 0) && (
                    <TableRow>
                      <TableCell colSpan={4} align="center">
                        <Typography color="textSecondary">No active signals</Typography>
                      </TableCell>
                    </TableRow>
                  )}
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
                <Typography variant="body2">{Number(drawdownStatus?.daily_pnl_percent || 0).toFixed(2)}% / 2%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={Math.min(Math.abs(drawdownStatus?.daily_pnl_percent || 0) / 2 * 100, 100)} color="success" />
            </Box>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Daily Trades</Typography>
                <Typography variant="body2">{drawdownStatus?.daily_trades_count || 0} / 10</Typography>
              </Box>
              <LinearProgress variant="determinate" value={Math.min((drawdownStatus?.daily_trades_count || 0) / 10 * 100, 100)} />
            </Box>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Daily Target</Typography>
                <Typography variant="body2">{Number(dailyPnlPercent).toFixed(2)}% / {dailyTarget}%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={Math.min(dailyPnlPercent / dailyTarget * 100, 100)} color="warning" />
            </Box>
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Max Drawdown</Typography>
                <Typography variant="body2">{Number(drawdown).toFixed(2)}% / 15%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={Math.min(drawdown / 15 * 100, 100)} />
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard;

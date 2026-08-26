import React, { useState, useEffect } from 'react';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { Card, Grid, Typography, Box, Chip, Tab, Tabs, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper } from '@mui/material';
import { TrendingUp, TrendingDown, Assessment, Speed, Timeline, Warning } from '@mui/icons-material';
import api from '../services/api';

const Analytics = () => {
  const [performance, setPerformance] = useState(null);
  const [riskAnalytics, setRiskAnalytics] = useState(null);
  const [signalAnalytics, setSignalAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const [perfRes, riskRes, signalRes] = await Promise.all([
        api.get('/analytics/performance/'),
        api.get('/analytics/risk/'),
        api.get('/analytics/signals/'),
      ]);
      setPerformance(perfRes.data);
      setRiskAnalytics(riskRes.data);
      setSignalAnalytics(signalRes.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, subtitle, icon, color }) => (
    <Card sx={{ p: 2, height: '100%', bgcolor: '#1a2940' }}>
      <Box display="flex" justifyContent="space-between" alignItems="flex-start">
        <Box>
          <Typography variant="body2" color="textSecondary">{title}</Typography>
          <Typography variant="h5" fontWeight="bold" color={color || 'white'}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="textSecondary">{subtitle}</Typography>
          )}
        </Box>
        {icon && (
          <Box sx={{ color: color || '#1976d2', opacity: 0.7 }}>
            {icon}
          </Box>
        )}
      </Box>
    </Card>
  );

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography color="white">Loading analytics...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" fontWeight="bold" color="white" gutterBottom>
        Trading Analytics
      </Typography>

      <Tabs
        value={tabValue}
        onChange={(e, v) => setTabValue(v)}
        sx={{ mb: 3, '& .MuiTab-root': { color: '#888' }, '& .Mui-selected': { color: '#1976d2' } }}
      >
        <Tab label="Performance" />
        <Tab label="Risk" />
        <Tab label="Signals" />
      </Tabs>

      {tabValue === 0 && performance && (
        <>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Today's P&L"
                value={`$${performance.today.total_pnl}`}
                subtitle={`${performance.today.total_trades} trades`}
                icon={<TrendingUp />}
                color={performance.today.total_pnl >= 0 ? '#4caf50' : '#f44336'}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Win Rate (Today)"
                value={`${performance.today.win_rate}%`}
                subtitle={`${performance.today.winning_trades}W / ${performance.today.losing_trades}L`}
                icon={<Assessment />}
                color="#1976d2"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Week P&L"
                value={`$${performance.week.total_pnl}`}
                subtitle={`${performance.week.total_trades} trades`}
                icon={<Timeline />}
                color={performance.week.total_pnl >= 0 ? '#4caf50' : '#f44336'}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Month P&L"
                value={`$${performance.month.total_pnl}`}
                subtitle={`${performance.month.total_trades} trades`}
                icon={<TrendingUp />}
                color={performance.month.total_pnl >= 0 ? '#4caf50' : '#f44336'}
              />
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Card sx={{ p: 2, bgcolor: '#1a2940' }}>
                <Typography variant="h6" color="white" gutterBottom>
                  Daily P&L (30 Days)
                </Typography>
                <Box height={300}>
                  <Line
                    data={{
                      labels: performance.daily_pnl.map(d => d.date),
                      datasets: [{
                        label: 'Daily P&L',
                        data: performance.daily_pnl.map(d => d.pnl),
                        borderColor: '#1976d2',
                        backgroundColor: 'rgba(25, 118, 210, 0.1)',
                        fill: true,
                        tension: 0.4,
                      }]
                    }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: { legend: { labels: { color: '#fff' } } },
                      scales: {
                        x: { ticks: { color: '#888' }, grid: { color: '#333' } },
                        y: { ticks: { color: '#888' }, grid: { color: '#333' } },
                      }
                    }}
                  />
                </Box>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card sx={{ p: 2, bgcolor: '#1a2940' }}>
                <Typography variant="h6" color="white" gutterBottom>
                  P&L by Symbol
                </Typography>
                <Box height={300}>
                  <Bar
                    data={{
                      labels: Object.keys(performance.symbol_breakdown),
                      datasets: [{
                        label: 'P&L',
                        data: Object.values(performance.symbol_breakdown).map(s => s.pnl),
                        backgroundColor: Object.values(performance.symbol_breakdown).map(s => 
                          s.pnl >= 0 ? '#4caf50' : '#f44336'
                        ),
                      }]
                    }}
                    options={{
                      responsive: true,
                      maintainAspectRatio: false,
                      plugins: { legend: { display: false } },
                      scales: {
                        x: { ticks: { color: '#888' }, grid: { color: '#333' } },
                        y: { ticks: { color: '#888' }, grid: { color: '#333' } },
                      }
                    }}
                  />
                </Box>
              </Card>
            </Grid>
          </Grid>

          <Card sx={{ p: 2, mt: 3, bgcolor: '#1a2940' }}>
            <Typography variant="h6" color="white" gutterBottom>
              Timeframe Performance
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ color: '#888' }}>Timeframe</TableCell>
                    <TableCell sx={{ color: '#888' }}>Total Signals</TableCell>
                    <TableCell sx={{ color: '#888' }}>Active</TableCell>
                    <TableCell sx={{ color: '#888' }}>Avg Strength</TableCell>
                    <TableCell sx={{ color: '#888' }}>Win Rate</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {Object.entries(performance.timeframe_breakdown).map(([tf, data]) => (
                    <TableRow key={tf}>
                      <TableCell sx={{ color: 'white' }}>{tf}</TableCell>
                      <TableCell sx={{ color: 'white' }}>{data.trades}</TableCell>
                      <TableCell sx={{ color: 'white' }}>{data.wins}</TableCell>
                      <TableCell sx={{ color: 'white' }}>{(data.pnl / data.trades).toFixed(2)}</TableCell>
                      <TableCell sx={{ color: 'white' }}>
                        {((data.wins / data.trades) * 100).toFixed(1)}%
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </>
      )}

      {tabValue === 1 && riskAnalytics && (
        <>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Daily Loss Remaining"
                value={`${riskAnalytics.current_status.daily_loss_remaining.toFixed(2)}%`}
                subtitle={`Max: ${riskAnalytics.risk_parameters.max_daily_loss}%`}
                icon={<Warning />}
                color={riskAnalytics.current_status.daily_loss_remaining < 0.5 ? '#f44336' : '#4caf50'}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Drawdown Remaining"
                value={`${riskAnalytics.current_status.drawdown_remaining.toFixed(2)}%`}
                subtitle={`Max: ${riskAnalytics.risk_parameters.max_drawdown}%`}
                icon={<TrendingDown />}
                color={riskAnalytics.current_status.drawdown_remaining < 3 ? '#f44336' : '#4caf50'}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Daily Trades"
                value={riskAnalytics.current_status.daily_trades_count}
                subtitle={`Max: ${riskAnalytics.risk_parameters.max_daily_trades}`}
                icon={<Speed />}
                color="#1976d2"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Daily Target"
                value={`${riskAnalytics.risk_parameters.daily_growth_target}%`}
                subtitle="Daily growth goal"
                icon={<TrendingUp />}
                color="#4caf50"
              />
            </Grid>
          </Grid>

          <Card sx={{ p: 2, bgcolor: '#1a2940' }}>
            <Typography variant="h6" color="white" gutterBottom>
              Circuit Breakers
            </Typography>
            <Box display="flex" gap={2}>
              <Chip
                label="Daily Loss Limit"
                color={riskAnalytics.circuit_breakers.daily_loss_active ? 'error' : 'success'}
                variant="outlined"
              />
              <Chip
                label="Max Drawdown"
                color={riskAnalytics.circuit_breakers.max_drawdown_active ? 'error' : 'success'}
                variant="outlined"
              />
              <Chip
                label="Daily Trade Limit"
                color={riskAnalytics.circuit_breakers.daily_trades_active ? 'error' : 'success'}
                variant="outlined"
              />
            </Box>
          </Card>

          {riskAnalytics.recent_alerts.length > 0 && (
            <Card sx={{ p: 2, mt: 3, bgcolor: '#1a2940' }}>
              <Typography variant="h6" color="white" gutterBottom>
                Recent Alerts
              </Typography>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ color: '#888' }}>Type</TableCell>
                      <TableCell sx={{ color: '#888' }}>Severity</TableCell>
                      <TableCell sx={{ color: '#888' }}>Message</TableCell>
                      <TableCell sx={{ color: '#888' }}>Time</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {riskAnalytics.recent_alerts.map((alert, idx) => (
                      <TableRow key={idx}>
                        <TableCell sx={{ color: 'white' }}>{alert.type}</TableCell>
                        <TableCell sx={{ color: 'white' }}>
                          <Chip
                            label={alert.severity}
                            size="small"
                            color={alert.severity === 'CRITICAL' ? 'error' : 'warning'}
                          />
                        </TableCell>
                        <TableCell sx={{ color: 'white' }}>{alert.message}</TableCell>
                        <TableCell sx={{ color: 'white' }}>{alert.created_at}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Card>
          )}
        </>
      )}

      {tabValue === 2 && signalAnalytics && (
        <>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Total Signals"
                value={signalAnalytics.summary.total_signals}
                subtitle="All time"
                icon={<Assessment />}
                color="#1976d2"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Active Signals"
                value={signalAnalytics.summary.active_signals}
                subtitle="Currently active"
                icon={<Speed />}
                color="#4caf50"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Buy Signals"
                value={signalAnalytics.summary.buy_signals}
                subtitle="Long signals"
                icon={<TrendingUp />}
                color="#4caf50"
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <StatCard
                title="Sell Signals"
                value={signalAnalytics.summary.sell_signals}
                subtitle="Short signals"
                icon={<TrendingDown />}
                color="#f44336"
              />
            </Grid>
          </Grid>

          <Card sx={{ p: 2, bgcolor: '#1a2940' }}>
            <Typography variant="h6" color="white" gutterBottom>
              Recent Signals
            </Typography>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ color: '#888' }}>Symbol</TableCell>
                    <TableCell sx={{ color: '#888' }}>Type</TableCell>
                    <TableCell sx={{ color: '#888' }}>Strength</TableCell>
                    <TableCell sx={{ color: '#888' }}>Timeframe</TableCell>
                    <TableCell sx={{ color: '#888' }}>Created</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {signalAnalytics.recent_signals.map((signal) => (
                    <TableRow key={signal.id}>
                      <TableCell sx={{ color: 'white' }}>{signal.symbol}</TableCell>
                      <TableCell sx={{ color: 'white' }}>
                        <Chip
                          label={signal.type}
                          size="small"
                          color={signal.type === 'BUY' ? 'success' : 'error'}
                        />
                      </TableCell>
                      <TableCell sx={{ color: 'white' }}>{signal.strength}%</TableCell>
                      <TableCell sx={{ color: 'white' }}>{signal.timeframe}</TableCell>
                      <TableCell sx={{ color: 'white' }}>{signal.created_at}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </>
      )}
    </Box>
  );
};

export default Analytics;

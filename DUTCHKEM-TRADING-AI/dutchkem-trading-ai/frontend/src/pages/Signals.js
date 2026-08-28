import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box, Grid, Paper, Typography, Card, CardContent, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Button, LinearProgress, Alert, Tabs, Tab, CircularProgress
} from '@mui/material';
import { Speed, TrendingUp, TrendingDown, CheckCircle } from '@mui/icons-material';
import { fetchActiveSignals, fetchConfluenceScores } from '../features/signals/signalsSlice';

function Signals() {
  const dispatch = useDispatch();
  const { activeSignals, confluenceScores, loading, error } = useSelector((state) => state.signals);
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    dispatch(fetchActiveSignals());
    dispatch(fetchConfluenceScores());
  }, [dispatch]);

  const getScoreColor = (score) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const directionalSignals = (activeSignals || []).filter((s) => s.signal_type !== 'NEUTRAL');
  const strongSignals = (activeSignals || []).filter((s) => s.strength >= 80);
  const avgScore = directionalSignals.length > 0
    ? Math.round(directionalSignals.reduce((a, b) => a + (b.strength || 0), 0) / directionalSignals.length)
    : 0;

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        <Speed sx={{ mr: 1, verticalAlign: 'middle' }} />
        Trading Signals
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Active Signals</Typography>
              <Typography variant="h4">{directionalSignals.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Strong Signals</Typography>
              <Typography variant="h4" color="success.main">{strongSignals.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Average Score</Typography>
              <Typography variant="h4">{avgScore}%</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Total Signals</Typography>
              <Typography variant="h4">{(activeSignals || []).length}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
          <Tab label="Active Signals" />
          <Tab label="Multi-Timeframe Confluence" />
        </Tabs>

        {tabValue === 0 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Direction</TableCell>
                  <TableCell>Score</TableCell>
                  <TableCell>Level</TableCell>
                  <TableCell>Timeframe</TableCell>
                  <TableCell>Entry</TableCell>
                  <TableCell>SL</TableCell>
                  <TableCell>TP</TableCell>
                  <TableCell>R:R</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {activeSignals.map((signal) => {
                  const level = signal.strength >= 80 ? 'STRONG' : signal.strength >= 60 ? 'MODERATE' : 'WEAK';
                  return (
                    <TableRow key={signal.id}>
                      <TableCell>{signal.symbol?.name || signal.symbol}</TableCell>
                      <TableCell>
                        <Chip
                          icon={signal.signal_type === 'BUY' ? <TrendingUp /> : <TrendingDown />}
                          label={signal.signal_type}
                          color={signal.signal_type === 'BUY' ? 'success' : 'error'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <LinearProgress variant="determinate" value={signal.strength || 0}
                            color={getScoreColor(signal.strength)} sx={{ width: 100 }} />
                          <Typography variant="body2">{signal.strength}%</Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip label={level}
                          color={level === 'STRONG' ? 'success' : level === 'MODERATE' ? 'warning' : 'error'}
                          size="small" />
                      </TableCell>
                      <TableCell>{signal.timeframe?.code || signal.timeframe}</TableCell>
                      <TableCell>{signal.entry_price || '-'}</TableCell>
                      <TableCell>{signal.stop_loss || '-'}</TableCell>
                      <TableCell>{signal.take_profit || '-'}</TableCell>
                      <TableCell>{signal.risk_reward_ratio || '-'}</TableCell>
                    </TableRow>
                  );
                })}
                {activeSignals.length === 0 && (
                  <TableRow><TableCell colSpan={9} align="center">No active signals</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {tabValue === 1 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Symbol</TableCell>
                  <TableCell>M5</TableCell>
                  <TableCell>M15</TableCell>
                  <TableCell>M30</TableCell>
                  <TableCell>H1</TableCell>
                  <TableCell>H2</TableCell>
                  <TableCell>H4</TableCell>
                  <TableCell>Total</TableCell>
                  <TableCell>Direction</TableCell>
                  <TableCell>Aligned</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(confluenceScores || []).map((item) => (
                  <TableRow key={item.symbol?.name || item.symbol || item.id}>
                    <TableCell>{item.symbol?.name || item.symbol}</TableCell>
                    {['m5', 'm15', 'm30', 'h1', 'h2', 'h4'].map((tf) => (
                      <TableCell key={tf}>
                        <Chip label={`${item[tf] || 0}%`} color={getScoreColor(item[tf] || 0)} size="small" />
                      </TableCell>
                    ))}
                    <TableCell>
                      <Typography variant="h6" color={getScoreColor(item.total || 0) + '.main'}>
                        {item.total || 0}%
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={item.direction || item.signal_type}
                        color={item.direction === 'BUY' || item.signal_type === 'BUY' ? 'success' : 'error'} />
                    </TableCell>
                    <TableCell>
                      {item.aligned ? <CheckCircle color="success" /> : <Typography color="textSecondary">-</Typography>}
                    </TableCell>
                  </TableRow>
                ))}
                {confluenceScores.length === 0 && (
                  <TableRow><TableCell colSpan={10} align="center">No confluence data available</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  );
}

export default Signals;

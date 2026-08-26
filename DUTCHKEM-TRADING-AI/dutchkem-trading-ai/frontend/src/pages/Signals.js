import React, { useState } from 'react';
import {
  Box, Grid, Paper, Typography, Card, CardContent, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Button, LinearProgress, Alert, Tabs, Tab
} from '@mui/material';
import { Speed, TrendingUp, TrendingDown, CheckCircle } from '@mui/icons-material';

function Signals() {
  const [tabValue, setTabValue] = useState(0);

  const activeSignals = [
    { id: 1, symbol: 'EURUSD', direction: 'LONG', score: 85, level: 'STRONG', timeframe: 'H1', entry: 1.1200, sl: 1.1150, tp: 1.1300, rr: '1:2' },
    { id: 2, symbol: 'GBPUSD', direction: 'SHORT', score: 72, level: 'MODERATE', timeframe: 'M15', entry: 1.3100, sl: 1.3150, tp: 1.3000, rr: '1:2' },
    { id: 3, symbol: 'USDJPY', direction: 'LONG', score: 68, level: 'MODERATE', timeframe: 'H4', entry: 149.50, sl: 149.00, tp: 150.50, rr: '1:2' },
    { id: 4, symbol: 'AUDUSD', direction: 'NEUTRAL', score: 45, level: 'WEAK', timeframe: 'M30', entry: null, sl: null, tp: null, rr: null },
  ];

  const confluenceScores = [
    { symbol: 'EURUSD', m5: 65, m15: 70, m30: 75, h1: 85, h2: 80, h4: 78, total: 85, direction: 'LONG', aligned: true },
    { symbol: 'GBPUSD', m5: 60, m15: 72, m30: 68, h1: 65, h2: 60, h4: 55, total: 72, direction: 'SHORT', aligned: false },
    { symbol: 'USDJPY', m5: 55, m15: 60, m30: 65, h1: 70, h2: 75, h4: 68, total: 68, direction: 'LONG', aligned: false },
  ];

  const getScoreColor = (score) => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        <Speed sx={{ mr: 1, verticalAlign: 'middle' }} />
        Trading Signals
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Active Signals</Typography>
              <Typography variant="h4">{activeSignals.filter(s => s.direction !== 'NEUTRAL').length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Strong Signals</Typography>
              <Typography variant="h4" color="success.main">
                {activeSignals.filter(s => s.level === 'STRONG').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Average Score</Typography>
              <Typography variant="h4">
                {Math.round(activeSignals.filter(s => s.direction !== 'NEUTRAL').reduce((a, b) => a + b.score, 0) / activeSignals.filter(s => s.direction !== 'NEUTRAL').length)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Win Rate (Today)</Typography>
              <Typography variant="h4" color="success.main">62%</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
          <Tab label="Active Signals" />
          <Tab label="Multi-Timeframe Confluence" />
          <Tab label="Signal History" />
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
                  <TableCell>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {activeSignals.map((signal) => (
                  <TableRow key={signal.id}>
                    <TableCell>{signal.symbol}</TableCell>
                    <TableCell>
                      <Chip
                        icon={signal.direction === 'LONG' ? <TrendingUp /> : signal.direction === 'SHORT' ? <TrendingDown /> : null}
                        label={signal.direction}
                        color={signal.direction === 'LONG' ? 'success' : signal.direction === 'SHORT' ? 'error' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <LinearProgress
                          variant="determinate"
                          value={signal.score}
                          color={getScoreColor(signal.score)}
                          sx={{ width: 100 }}
                        />
                        <Typography variant="body2">{signal.score}%</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={signal.level}
                        color={signal.level === 'STRONG' ? 'success' : signal.level === 'MODERATE' ? 'warning' : 'error'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{signal.timeframe}</TableCell>
                    <TableCell>{signal.entry || '-'}</TableCell>
                    <TableCell>{signal.sl || '-'}</TableCell>
                    <TableCell>{signal.tp || '-'}</TableCell>
                    <TableCell>{signal.rr || '-'}</TableCell>
                    <TableCell>
                      {signal.direction !== 'NEUTRAL' && (
                        <Button variant="contained" size="small" color={signal.direction === 'LONG' ? 'success' : 'error'}>
                          Trade
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
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
                {confluenceScores.map((item) => (
                  <TableRow key={item.symbol}>
                    <TableCell>{item.symbol}</TableCell>
                    <TableCell>
                      <Chip label={`${item.m5}%`} color={getScoreColor(item.m5)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip label={`${item.m15}%`} color={getScoreColor(item.m15)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip label={`${item.m30}%`} color={getScoreColor(item.m30)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip label={`${item.h1}%`} color={getScoreColor(item.h1)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip label={`${item.h2}%`} color={getScoreColor(item.h2)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Chip label={`${item.h4}%`} color={getScoreColor(item.h4)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="h6" color={getScoreColor(item.total) + '.main'}>
                        {item.total}%
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={item.direction}
                        color={item.direction === 'LONG' ? 'success' : item.direction === 'SHORT' ? 'error' : 'default'}
                      />
                    </TableCell>
                    <TableCell>
                      {item.aligned ? (
                        <CheckCircle color="success" />
                      ) : (
                        <Typography color="textSecondary">-</Typography>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {tabValue === 2 && (
          <Alert severity="info">Signal history will show past signals with outcomes.</Alert>
        )}
      </Paper>
    </Box>
  );
}

export default Signals;

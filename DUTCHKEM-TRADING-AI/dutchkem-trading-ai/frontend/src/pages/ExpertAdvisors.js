import React, { useState } from 'react';
import {
  Box, Grid, Paper, Typography, Card, CardContent, Button, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  FormControl, InputLabel, Select, MenuItem, Alert, Tabs, Tab
} from '@mui/material';
import { SmartToy, Add, PlayArrow, Stop, Delete, Code } from '@mui/icons-material';

function ExpertAdvisors() {
  const [tabValue, setTabValue] = useState(0);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);

  const expertAdvisors = [
    { id: 1, name: 'M5 Scalper Pro', symbol: 'EURUSD', timeframe: 'M5', status: 'LIVE', trades: 156, winRate: 63, profit: 450.25 },
    { id: 2, name: 'H1 Trend Rider', symbol: 'GBPUSD', timeframe: 'H1', status: 'LIVE', trades: 45, winRate: 58, profit: 320.00 },
    { id: 3, name: 'M15 Momentum', symbol: 'USDJPY', timeframe: 'M15', status: 'PAUSED', trades: 89, winRate: 60, profit: 180.50 },
    { id: 4, name: 'H4 Strategic', symbol: 'AUDUSD', timeframe: 'H4', status: 'INACTIVE', trades: 0, winRate: 0, profit: 0 },
  ];

  const backtestResults = [
    { ea: 'M5 Scalper Pro', period: '2023-2024', return: 45.2, maxDD: 8.5, sharpe: 1.8, trades: 1560 },
    { ea: 'H1 Trend Rider', period: '2023-2024', return: 32.1, maxDD: 12.3, sharpe: 1.5, trades: 450 },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'LIVE': return 'success';
      case 'PAUSED': return 'warning';
      case 'BACKTESTING': return 'info';
      default: return 'default';
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        <SmartToy sx={{ mr: 1, verticalAlign: 'middle' }} />
        Expert Advisors
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Total EAs</Typography>
              <Typography variant="h4">{expertAdvisors.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Active (Live)</Typography>
              <Typography variant="h4" color="success.main">
                {expertAdvisors.filter(ea => ea.status === 'LIVE').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Total Profit</Typography>
              <Typography variant="h4" color="success.main">
                ${expertAdvisors.reduce((sum, ea) => sum + ea.profit, 0).toLocaleString()}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Button
                variant="contained"
                fullWidth
                startIcon={<Add />}
                onClick={() => setCreateDialogOpen(true)}
              >
                Create EA
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
          <Tab label="My EAs" />
          <Tab label="Backtest Results" />
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
                {expertAdvisors.map((ea) => (
                  <TableRow key={ea.id}>
                    <TableCell>{ea.name}</TableCell>
                    <TableCell>{ea.symbol}</TableCell>
                    <TableCell>{ea.timeframe}</TableCell>
                    <TableCell>
                      <Chip
                        label={ea.status}
                        color={getStatusColor(ea.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{ea.trades}</TableCell>
                    <TableCell>{ea.winRate}%</TableCell>
                    <TableCell color={ea.profit >= 0 ? 'success.main' : 'error.main'}>
                      ${ea.profit.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {ea.status === 'LIVE' ? (
                        <Button size="small" color="warning" startIcon={<Stop />}>Pause</Button>
                      ) : ea.status === 'PAUSED' ? (
                        <Button size="small" color="success" startIcon={<PlayArrow />}>Resume</Button>
                      ) : (
                        <Button size="small" color="success" startIcon={<PlayArrow />}>Start</Button>
                      )}
                      <Button size="small" startIcon={<Code />}>Code</Button>
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
                  <TableCell>EA Name</TableCell>
                  <TableCell>Period</TableCell>
                  <TableCell>Return</TableCell>
                  <TableCell>Max Drawdown</TableCell>
                  <TableCell>Sharpe Ratio</TableCell>
                  <TableCell>Trades</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {backtestResults.map((result, index) => (
                  <TableRow key={index}>
                    <TableCell>{result.ea}</TableCell>
                    <TableCell>{result.period}</TableCell>
                    <TableCell color="success.main">+{result.return}%</TableCell>
                    <TableCell color="error.main">{result.maxDD}%</TableCell>
                    <TableCell>{result.sharpe}</TableCell>
                    <TableCell>{result.trades}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {tabValue === 2 && (
          <Alert severity="info">EA Marketplace coming soon! Browse and purchase expert advisors.</Alert>
        )}
      </Paper>

      {/* Create EA Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Expert Advisor</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="EA Name"
            fullWidth
            variant="outlined"
          />
          <FormControl fullWidth margin="dense">
            <InputLabel>Symbol</InputLabel>
            <Select label="Symbol">
              <MenuItem value="EURUSD">EURUSD</MenuItem>
              <MenuItem value="GBPUSD">GBPUSD</MenuItem>
              <MenuItem value="USDJPY">USDJPY</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth margin="dense">
            <InputLabel>Timeframe</InputLabel>
            <Select label="Timeframe">
              <MenuItem value="M5">M5</MenuItem>
              <MenuItem value="M15">M15</MenuItem>
              <MenuItem value="M30">M30</MenuItem>
              <MenuItem value="H1">H1</MenuItem>
              <MenuItem value="H2">H2</MenuItem>
              <MenuItem value="H4">H4</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth margin="dense">
            <InputLabel>Strategy Type</InputLabel>
            <Select label="Strategy Type">
              <MenuItem value="scalping">Scalping</MenuItem>
              <MenuItem value="momentum">Momentum</MenuItem>
              <MenuItem value="swing">Swing</MenuItem>
              <MenuItem value="trend">Trend</MenuItem>
              <MenuItem value="position">Position</MenuItem>
              <MenuItem value="strategic">Strategic</MenuItem>
            </Select>
          </FormControl>
          <TextField
            margin="dense"
            label="Risk per Trade (%)"
            type="number"
            fullWidth
            variant="outlined"
            defaultValue={1}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="secondary">Generate with AI</Button>
          <Button variant="contained">Create</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default ExpertAdvisors;

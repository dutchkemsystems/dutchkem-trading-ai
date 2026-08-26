import React, { useState, useEffect } from 'react';
import {
  Box, Grid, Paper, Typography, Tabs, Tab, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Chip, Button,
  Select, MenuItem, FormControl, InputLabel, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Alert
} from '@mui/material';
import { Add, Close, Edit } from '@mui/icons-material';
import TradingViewWidget from 'react-tradingview-widget';

function Trading() {
  const [tabValue, setTabValue] = useState(0);
  const [selectedSymbol, setSelectedSymbol] = useState('EURUSD');
  const [selectedTimeframe, setSelectedTimeframe] = useState('H1');
  const [orderDialogOpen, setOrderDialogOpen] = useState(false);
  const [orderType, setOrderType] = useState('MARKET');

  const symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'];
  const timeframes = ['M5', 'M15', 'M30', 'H1', 'H2', 'H4'];

  const positions = [
    { id: 1, symbol: 'EURUSD', type: 'BUY', volume: 0.1, openPrice: 1.1200, currentPrice: 1.1235, pnl: 35.00, sl: 1.1150, tp: 1.1300 },
    { id: 2, symbol: 'GBPUSD', type: 'SELL', volume: 0.05, openPrice: 1.3100, currentPrice: 1.3050, pnl: 25.00, sl: 1.3150, tp: 1.3000 },
  ];

  const orders = [
    { id: 1, symbol: 'USDJPY', type: 'LIMIT', direction: 'BUY', volume: 0.1, price: 149.50, sl: 149.00, tp: 150.50, status: 'PENDING' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Trading
      </Typography>

      {/* Symbol and Timeframe Selection */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth>
            <InputLabel>Symbol</InputLabel>
            <Select
              value={selectedSymbol}
              label="Symbol"
              onChange={(e) => setSelectedSymbol(e.target.value)}
            >
              {symbols.map((sym) => (
                <MenuItem key={sym} value={sym}>{sym}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth>
            <InputLabel>Timeframe</InputLabel>
            <Select
              value={selectedTimeframe}
              label="Timeframe"
              onChange={(e) => setSelectedTimeframe(e.target.value)}
            >
              {timeframes.map((tf) => (
                <MenuItem key={tf} value={tf}>{tf}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} md={4}>
          <Button
            variant="contained"
            startIcon={<Add />}
            fullWidth
            sx={{ height: '56px' }}
            onClick={() => setOrderDialogOpen(true)}
          >
            New Order
          </Button>
        </Grid>
      </Grid>

      {/* Chart */}
      <Paper sx={{ mb: 3, height: 500 }}>
        <TradingViewWidget
          symbol={`FX:${selectedSymbol}`}
          interval={selectedTimeframe.toLowerCase().replace('m', '').replace('h', 'H')}
          theme="dark"
          style={{ height: '100%' }}
          locale="en"
          autosize
        />
      </Paper>

      {/* Positions and Orders */}
      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
          <Tab label={`Positions (${positions.length})`} />
          <Tab label={`Orders (${orders.length})`} />
        </Tabs>

        {tabValue === 0 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Volume</TableCell>
                  <TableCell>Open Price</TableCell>
                  <TableCell>Current</TableCell>
                  <TableCell>SL</TableCell>
                  <TableCell>TP</TableCell>
                  <TableCell>P&L</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {positions.map((pos) => (
                  <TableRow key={pos.id}>
                    <TableCell>{pos.symbol}</TableCell>
                    <TableCell>
                      <Chip
                        label={pos.type}
                        color={pos.type === 'BUY' ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{pos.volume}</TableCell>
                    <TableCell>{pos.openPrice}</TableCell>
                    <TableCell>{pos.currentPrice}</TableCell>
                    <TableCell>{pos.sl}</TableCell>
                    <TableCell>{pos.tp}</TableCell>
                    <TableCell color={pos.pnl >= 0 ? 'success.main' : 'error.main'}>
                      ${pos.pnl.toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <Button size="small" color="error" startIcon={<Close />}>
                        Close
                      </Button>
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
                  <TableCell>Type</TableCell>
                  <TableCell>Direction</TableCell>
                  <TableCell>Volume</TableCell>
                  <TableCell>Price</TableCell>
                  <TableCell>SL</TableCell>
                  <TableCell>TP</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders.map((order) => (
                  <TableRow key={order.id}>
                    <TableCell>{order.symbol}</TableCell>
                    <TableCell>{order.type}</TableCell>
                    <TableCell>
                      <Chip
                        label={order.direction}
                        color={order.direction === 'BUY' ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{order.volume}</TableCell>
                    <TableCell>{order.price}</TableCell>
                    <TableCell>{order.sl}</TableCell>
                    <TableCell>{order.tp}</TableCell>
                    <TableCell>
                      <Chip label={order.status} color="warning" size="small" />
                    </TableCell>
                    <TableCell>
                      <Button size="small" color="error" startIcon={<Close />}>
                        Cancel
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      {/* New Order Dialog */}
      <Dialog open={orderDialogOpen} onClose={() => setOrderDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>New Order - {selectedSymbol}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Order Type</InputLabel>
              <Select
                value={orderType}
                label="Order Type"
                onChange={(e) => setOrderType(e.target.value)}
              >
                <MenuItem value="MARKET">Market</MenuItem>
                <MenuItem value="LIMIT">Limit</MenuItem>
                <MenuItem value="STOP">Stop</MenuItem>
              </Select>
            </FormControl>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Button fullWidth variant="contained" color="success" size="large">
                  BUY
                </Button>
              </Grid>
              <Grid item xs={6}>
                <Button fullWidth variant="contained" color="error" size="large">
                  SELL
                </Button>
              </Grid>
              <Grid item xs={12}>
                <TextField fullWidth label="Volume" type="number" defaultValue={0.1} />
              </Grid>
              {orderType !== 'MARKET' && (
                <Grid item xs={12}>
                  <TextField fullWidth label="Price" type="number" />
                </Grid>
              )}
              <Grid item xs={6}>
                <TextField fullWidth label="Stop Loss" type="number" />
              </Grid>
              <Grid item xs={6}>
                <TextField fullWidth label="Take Profit" type="number" />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOrderDialogOpen(false)}>Cancel</Button>
          <Button variant="contained">Place Order</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Trading;

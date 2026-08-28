import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Box, Grid, Paper, Typography, Tabs, Tab, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Chip, Button,
  Select, MenuItem, FormControl, InputLabel, Dialog, DialogTitle,
  DialogContent, DialogActions, TextField, Alert, CircularProgress
} from '@mui/material';
import { Add, Close } from '@mui/icons-material';
import TradingViewWidget from 'react-tradingview-widget';
import {
  fetchPositions, fetchOrders, fetchSymbols, createOrder,
  closeTrade, cancelOrder
} from '../features/trading/tradingSlice';

function Trading() {
  const dispatch = useDispatch();
  const { positions, orders, symbols, loading, error } = useSelector((state) => state.trading);
  const [tabValue, setTabValue] = useState(0);
  const [selectedSymbol, setSelectedSymbol] = useState('EURUSD');
  const [selectedTimeframe, setSelectedTimeframe] = useState('H1');
  const [orderDialogOpen, setOrderDialogOpen] = useState(false);
  const [orderForm, setOrderForm] = useState({
    orderType: 'MARKET', symbol: 'EURUSD', volume: 0.1,
    price: '', stopLoss: '', takeProfit: '', direction: 'BUY'
  });
  const [submitting, setSubmitting] = useState(false);
  const [orderError, setOrderError] = useState('');

  useEffect(() => {
    dispatch(fetchPositions());
    dispatch(fetchOrders());
    dispatch(fetchSymbols());
  }, [dispatch]);

  const timeframes = ['M5', 'M15', 'M30', 'H1', 'H2', 'H4'];

  const handlePlaceOrder = async () => {
    setSubmitting(true);
    setOrderError('');
    try {
      const orderData = {
        symbol: symbols.find((s) => s.name === orderForm.symbol)?.id,
        order_type: orderForm.orderType,
        position_type: orderForm.direction,
        volume: parseFloat(orderForm.volume),
        price: orderForm.orderType !== 'MARKET' ? parseFloat(orderForm.price) : undefined,
        stop_loss: orderForm.stopLoss ? parseFloat(orderForm.stopLoss) : undefined,
        take_profit: orderForm.takeProfit ? parseFloat(orderForm.takeProfit) : undefined,
      };
      await dispatch(createOrder(orderData)).unwrap();
      setOrderDialogOpen(false);
      dispatch(fetchOrders());
      dispatch(fetchPositions());
    } catch (err) {
      setOrderError(err || 'Failed to place order');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCloseTrade = async (tradeId) => {
    try {
      await dispatch(closeTrade(tradeId)).unwrap();
      dispatch(fetchPositions());
    } catch (err) {
      console.error('Failed to close trade:', err);
    }
  };

  const handleCancelOrder = async (orderId) => {
    try {
      await dispatch(cancelOrder(orderId)).unwrap();
      dispatch(fetchOrders());
    } catch (err) {
      console.error('Failed to cancel order:', err);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Trading
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth>
            <InputLabel>Symbol</InputLabel>
            <Select value={selectedSymbol} label="Symbol" onChange={(e) => setSelectedSymbol(e.target.value)}>
              {symbols.map((sym) => (
                <MenuItem key={sym.id} value={sym.name}>{sym.name}</MenuItem>
              ))}
              {symbols.length === 0 && <MenuItem value="EURUSD">EURUSD</MenuItem>}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} md={4}>
          <FormControl fullWidth>
            <InputLabel>Timeframe</InputLabel>
            <Select value={selectedTimeframe} label="Timeframe" onChange={(e) => setSelectedTimeframe(e.target.value)}>
              {timeframes.map((tf) => (
                <MenuItem key={tf} value={tf}>{tf}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>
        <Grid item xs={12} md={4}>
          <Button variant="contained" startIcon={<Add />} fullWidth sx={{ height: '56px' }}
            onClick={() => setOrderDialogOpen(true)}>
            New Order
          </Button>
        </Grid>
      </Grid>

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

      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
          <Tab label={`Positions (${positions.length})`} />
          <Tab label={`Orders (${orders.length})`} />
        </Tabs>

        {loading ? (
          <Box display="flex" justifyContent="center" p={3}><CircularProgress /></Box>
        ) : (
          <>
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
                        <TableCell>{pos.symbol?.name || pos.symbol}</TableCell>
                        <TableCell>
                          <Chip label={pos.position_type} color={pos.position_type === 'BUY' ? 'success' : 'error'} size="small" />
                        </TableCell>
                        <TableCell>{pos.volume}</TableCell>
                        <TableCell>{pos.open_price}</TableCell>
                        <TableCell>{pos.current_price}</TableCell>
                        <TableCell>{pos.stop_loss || '-'}</TableCell>
                        <TableCell>{pos.take_profit || '-'}</TableCell>
                        <TableCell color={parseFloat(pos.unrealized_pnl) >= 0 ? 'success.main' : 'error.main'}>
                          ${Number(pos.unrealized_pnl).toFixed(2)}
                        </TableCell>
                        <TableCell>
                          <Button size="small" color="error" startIcon={<Close />}
                            onClick={() => handleCloseTrade(pos.trade)}>
                            Close
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                    {positions.length === 0 && (
                      <TableRow><TableCell colSpan={9} align="center">No open positions</TableCell></TableRow>
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
                        <TableCell>{order.symbol?.name || order.symbol}</TableCell>
                        <TableCell>{order.order_type}</TableCell>
                        <TableCell>
                          <Chip label={order.position_type} color={order.position_type === 'BUY' ? 'success' : 'error'} size="small" />
                        </TableCell>
                        <TableCell>{order.volume}</TableCell>
                        <TableCell>{order.price}</TableCell>
                        <TableCell>{order.stop_loss || '-'}</TableCell>
                        <TableCell>{order.take_profit || '-'}</TableCell>
                        <TableCell>
                          <Chip label={order.status} color={order.status === 'PENDING' ? 'warning' : 'info'} size="small" />
                        </TableCell>
                        <TableCell>
                          {order.status === 'PENDING' && (
                            <Button size="small" color="error" startIcon={<Close />}
                              onClick={() => handleCancelOrder(order.id)}>
                              Cancel
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                    {orders.length === 0 && (
                      <TableRow><TableCell colSpan={9} align="center">No pending orders</TableCell></TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </>
        )}
      </Paper>

      <Dialog open={orderDialogOpen} onClose={() => setOrderDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>New Order - {selectedSymbol}</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            {orderError && <Alert severity="error" sx={{ mb: 2 }}>{orderError}</Alert>}
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Order Type</InputLabel>
              <Select value={orderForm.orderType} label="Order Type"
                onChange={(e) => setOrderForm({ ...orderForm, orderType: e.target.value })}>
                <MenuItem value="MARKET">Market</MenuItem>
                <MenuItem value="LIMIT">Limit</MenuItem>
                <MenuItem value="STOP">Stop</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Symbol</InputLabel>
              <Select value={orderForm.symbol} label="Symbol"
                onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value })}>
                {symbols.map((sym) => (
                  <MenuItem key={sym.id} value={sym.name}>{sym.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Button fullWidth variant="contained" color="success" size="large"
                  onClick={() => setOrderForm({ ...orderForm, direction: 'BUY' })}
                  sx={{ opacity: orderForm.direction === 'BUY' ? 1 : 0.5 }}>
                  BUY
                </Button>
              </Grid>
              <Grid item xs={6}>
                <Button fullWidth variant="contained" color="error" size="large"
                  onClick={() => setOrderForm({ ...orderForm, direction: 'SELL' })}
                  sx={{ opacity: orderForm.direction === 'SELL' ? 1 : 0.5 }}>
                  SELL
                </Button>
              </Grid>
              <Grid item xs={12}>
                <TextField fullWidth label="Volume" type="number" value={orderForm.volume}
                  onChange={(e) => setOrderForm({ ...orderForm, volume: e.target.value })} />
              </Grid>
              {orderForm.orderType !== 'MARKET' && (
                <Grid item xs={12}>
                  <TextField fullWidth label="Price" type="number" value={orderForm.price}
                    onChange={(e) => setOrderForm({ ...orderForm, price: e.target.value })} />
                </Grid>
              )}
              <Grid item xs={6}>
                <TextField fullWidth label="Stop Loss" type="number" value={orderForm.stopLoss}
                  onChange={(e) => setOrderForm({ ...orderForm, stopLoss: e.target.value })} />
              </Grid>
              <Grid item xs={6}>
                <TextField fullWidth label="Take Profit" type="number" value={orderForm.takeProfit}
                  onChange={(e) => setOrderForm({ ...orderForm, takeProfit: e.target.value })} />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOrderDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handlePlaceOrder} disabled={submitting}>
            {submitting ? 'Placing...' : 'Place Order'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Trading;

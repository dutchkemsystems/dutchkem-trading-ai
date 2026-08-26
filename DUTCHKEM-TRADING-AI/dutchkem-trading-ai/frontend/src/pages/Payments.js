import React, { useState } from 'react';
import {
  Box, Grid, Paper, Typography, Tabs, Tab, Card, CardContent,
  Button, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, FormControl, InputLabel, Select, MenuItem, Alert
} from '@mui/material';
import { Payment, Add, AccountBalance, CreditCard, CurrencyBitcoin, PhoneAndroid } from '@mui/icons-material';

function Payments() {
  const [tabValue, setTabValue] = useState(0);
  const [depositDialogOpen, setDepositDialogOpen] = useState(false);
  const [withdrawDialogOpen, setWithdrawDialogOpen] = useState(false);
  const [selectedMethod, setSelectedMethod] = useState('');

  const balance = {
    available: 10450.25,
    pending: 500.00,
    bonus: 200.00,
  };

  const transactions = [
    { id: 1, type: 'DEPOSIT', amount: 1000, method: 'Credit Card', status: 'COMPLETED', date: '2024-01-15' },
    { id: 2, type: 'DEPOSIT', amount: 500, method: 'Crypto (USDT)', status: 'COMPLETED', date: '2024-01-14' },
    { id: 3, type: 'WITHDRAWAL', amount: 200, method: 'Bank Transfer', status: 'PENDING', date: '2024-01-13' },
    { id: 4, type: 'DEPOSIT', amount: 2000, method: 'PayPal', status: 'COMPLETED', date: '2024-01-12' },
  ];

  const depositMethods = [
    { id: 'card', name: 'Credit/Debit Card', icon: <CreditCard />, min: 50, max: 10000, fee: '0%', time: 'Instant' },
    { id: 'crypto', name: 'Crypto (BTC, ETH, USDT)', icon: <CurrencyBitcoin />, min: 50, max: null, fee: 'Network', time: '10-60 min' },
    { id: 'paypal', name: 'PayPal/Skrill/Neteller', icon: <Payment />, min: 50, max: 10000, fee: '0%', time: 'Instant' },
    { id: 'mobile', name: 'Mobile Money', icon: <PhoneAndroid />, min: 10, max: 5000, fee: '$0.50', time: 'Instant' },
    { id: 'bank', name: 'Bank Transfer', icon: <AccountBalance />, min: 100, max: null, fee: '$0', time: '1-3 days' },
  ];

  const kycStatus = 'VERIFIED';

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        <Payment sx={{ mr: 1, verticalAlign: 'middle' }} />
        Payments
      </Typography>

      {/* Balance Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Available Balance</Typography>
              <Typography variant="h4" color="success.main">${balance.available.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Pending</Typography>
              <Typography variant="h4" color="warning.main">${balance.pending.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary">Bonus</Typography>
              <Typography variant="h4" color="info.main">${balance.bonus.toLocaleString()}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* KYC Status */}
      {kycStatus !== 'VERIFIED' && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Please complete KYC verification to enable withdrawals.
        </Alert>
      )}

      {/* Tabs */}
      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
          <Tab label="Deposit" />
          <Tab label="Withdraw" />
          <Tab label="Transaction History" />
          <Tab label="Payment Methods" />
        </Tabs>

        {tabValue === 0 && (
          <Grid container spacing={2}>
            {depositMethods.map((method) => (
              <Grid item xs={12} md={6} key={method.id}>
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      {method.icon}
                      <Typography variant="h6" sx={{ ml: 1 }}>{method.name}</Typography>
                    </Box>
                    <Typography variant="body2" color="textSecondary">
                      Min: ${method.min} | Max: {method.max ? `$${method.max}` : 'Unlimited'}
                    </Typography>
                    <Typography variant="body2" color="textSecondary">
                      Fee: {method.fee} | Time: {method.time}
                    </Typography>
                    <Button
                      variant="contained"
                      fullWidth
                      sx={{ mt: 2 }}
                      onClick={() => {
                        setSelectedMethod(method.id);
                        setDepositDialogOpen(true);
                      }}
                    >
                      Deposit
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}

        {tabValue === 1 && (
          <Box>
            {kycStatus !== 'VERIFIED' ? (
              <Alert severity="error">KYC verification required for withdrawals.</Alert>
            ) : (
              <Grid container spacing={2}>
                {depositMethods.filter(m => m.id !== 'bank').map((method) => (
                  <Grid item xs={12} md={6} key={method.id}>
                    <Card>
                      <CardContent>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                          {method.icon}
                          <Typography variant="h6" sx={{ ml: 1 }}>{method.name}</Typography>
                        </Box>
                        <Button
                          variant="contained"
                          color="secondary"
                          fullWidth
                          onClick={() => {
                            setSelectedMethod(method.id);
                            setWithdrawDialogOpen(true);
                          }}
                        >
                          Withdraw
                        </Button>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        )}

        {tabValue === 2 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Type</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Method</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Date</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transactions.map((tx) => (
                  <TableRow key={tx.id}>
                    <TableCell>
                      <Chip
                        label={tx.type}
                        color={tx.type === 'DEPOSIT' ? 'success' : 'warning'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>${tx.amount.toLocaleString()}</TableCell>
                    <TableCell>{tx.method}</TableCell>
                    <TableCell>
                      <Chip
                        label={tx.status}
                        color={tx.status === 'COMPLETED' ? 'success' : 'warning'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{tx.date}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {tabValue === 3 && (
          <Alert severity="info">Add and manage your payment methods here.</Alert>
        )}
      </Paper>

      {/* Deposit Dialog */}
      <Dialog open={depositDialogOpen} onClose={() => setDepositDialogOpen(false)}>
        <DialogTitle>Deposit Funds</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Amount"
            type="number"
            fullWidth
            variant="outlined"
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDepositDialogOpen(false)}>Cancel</Button>
          <Button variant="contained">Deposit</Button>
        </DialogActions>
      </Dialog>

      {/* Withdraw Dialog */}
      <Dialog open={withdrawDialogOpen} onClose={() => setWithdrawDialogOpen(false)}>
        <DialogTitle>Withdraw Funds</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Amount"
            type="number"
            fullWidth
            variant="outlined"
            sx={{ mt: 2 }}
          />
          <Alert severity="info" sx={{ mt: 2 }}>
            Available for withdrawal: ${balance.available.toLocaleString()}
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWithdrawDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="secondary">Withdraw</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Payments;

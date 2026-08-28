import React, { useState, useEffect } from 'react';
import {
  Box, Grid, Paper, Typography, Tabs, Tab, Card, CardContent,
  Button, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Chip, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Alert, CircularProgress, MenuItem, Select, FormControl,
  InputLabel, Divider
} from '@mui/material';
import { Payment, AccountBalance, CreditCard, PhoneAndroid, CheckCircle, Error } from '@mui/icons-material';
import { paymentsAPI } from '../services/api';

const CURRENCIES = [
  { code: 'NGN', name: 'Nigerian Naira', symbol: '₦' },
  { code: 'GHS', name: 'Ghanaian Cedi', symbol: 'GH₵' },
  { code: 'KES', name: 'Kenyan Shilling', symbol: 'KSh' },
  { code: 'ZAR', name: 'South African Rand', symbol: 'R' },
];

const CHANNELS = [
  { id: 'card', name: 'Card', icon: <CreditCard /> },
  { id: 'bank_transfer', name: 'Bank Transfer', icon: <AccountBalance /> },
  { id: 'ussd', name: 'USSD', icon: <PhoneAndroid /> },
  { id: 'mobile_money', name: 'Mobile Money', icon: <PhoneAndroid /> },
];

function Payments() {
  const [tabValue, setTabValue] = useState(0);
  const [depositDialogOpen, setDepositDialogOpen] = useState(false);
  const [withdrawDialogOpen, setWithdrawDialogOpen] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [depositAmount, setDepositAmount] = useState('');
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [selectedCurrency, setSelectedCurrency] = useState('NGN');
  const [selectedChannel, setSelectedChannel] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [kycStatus, setKycStatus] = useState('NOT_STARTED');
  const [paymentStatus, setPaymentStatus] = useState(null);

  useEffect(() => {
    fetchData();
    checkPaymentCallback();
  }, []);

  const checkPaymentCallback = () => {
    const params = new URLSearchParams(window.location.search);
    const status = params.get('status');
    const reference = params.get('reference');
    if (status && reference) {
      if (status === 'COMPLETED') {
        setSuccess(`Payment ${reference} completed successfully!`);
      } else {
        setError(`Payment ${reference} status: ${status}`);
      }
      window.history.replaceState({}, '', '/payments');
    }
  };

  const fetchData = async () => {
    try {
      const [txRes, kycRes] = await Promise.all([
        paymentsAPI.getTransactions(),
        paymentsAPI.getKYCStatus(),
      ]);
      setTransactions(txRes.data.results || txRes.data || []);
      setKycStatus(kycRes.data.status || 'NOT_STARTED');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load payment data');
    } finally {
      setLoading(false);
    }
  };

  const handleDeposit = async () => {
    if (!depositAmount || parseFloat(depositAmount) < 100) {
      setError('Minimum deposit is 100');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const { data } = await paymentsAPI.initializeDeposit({
        amount: parseFloat(depositAmount),
        currency: selectedCurrency,
        channel: selectedChannel,
      });
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        setSuccess(`Payment reference: ${data.reference}. Status: ${data.status}`);
        setDepositDialogOpen(false);
        setDepositAmount('');
        fetchData();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to initialize deposit');
    } finally {
      setSubmitting(false);
    }
  };

  const handleWithdraw = async () => {
    if (!withdrawAmount || parseFloat(withdrawAmount) < 500) {
      setError('Minimum withdrawal is 500');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await paymentsAPI.createWithdrawal({
        amount: parseFloat(withdrawAmount),
        currency: selectedCurrency,
      });
      setWithdrawDialogOpen(false);
      setWithdrawAmount('');
      setSuccess('Withdrawal request submitted successfully');
      fetchData();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create withdrawal');
    } finally {
      setSubmitting(false);
    }
  };

  const getChannelIcon = (channelId) => {
    const channel = CHANNELS.find(c => c.id === channelId);
    return channel ? channel.icon : <Payment />;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'COMPLETED': return 'success';
      case 'FAILED': return 'error';
      case 'PROCESSING': return 'warning';
      case 'PENDING': return 'info';
      default: return 'default';
    }
  };

  const getCurrencySymbol = (code) => {
    const currency = CURRENCIES.find(c => c.code === code);
    return currency ? currency.symbol : code;
  };

  if (loading) {
    return <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px"><CircularProgress /></Box>;
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        <Payment sx={{ mr: 1, verticalAlign: 'middle' }} />
        Payments
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>}

      {kycStatus !== 'VERIFIED' && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          Please complete KYC verification to enable withdrawals.
        </Alert>
      )}

      <Paper sx={{ p: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} sx={{ mb: 2 }}>
          <Tab label="Deposit" />
          <Tab label="Withdraw" />
          <Tab label="Transaction History" />
        </Tabs>

        {tabValue === 0 && (
          <Box>
            <Alert severity="info" sx={{ mb: 2 }}>
              Deposits are processed via Korapay. Supports Card, Bank Transfer, USSD, and Mobile Money.
            </Alert>
            <Grid container spacing={2}>
              {CURRENCIES.map((currency) => (
                <Grid item xs={12} sm={6} md={3} key={currency.code}>
                  <Card sx={{ cursor: 'pointer' }}
                    onClick={() => { setSelectedCurrency(currency.code); setDepositDialogOpen(true); }}>
                    <CardContent>
                      <Typography variant="h6">{currency.symbol}</Typography>
                      <Typography variant="body2" color="textSecondary">{currency.name}</Typography>
                      <Typography variant="caption" color="textSecondary">
                        Min: {currency.symbol}100
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {tabValue === 1 && (
          <Box>
            {kycStatus !== 'VERIFIED' ? (
              <Alert severity="error">KYC verification required for withdrawals.</Alert>
            ) : (
              <Grid container spacing={2}>
                {CURRENCIES.map((currency) => (
                  <Grid item xs={12} sm={6} md={3} key={currency.code}>
                    <Card sx={{ cursor: 'pointer' }}
                      onClick={() => { setSelectedCurrency(currency.code); setWithdrawDialogOpen(true); }}>
                      <CardContent>
                        <Typography variant="h6">{currency.symbol}</Typography>
                        <Typography variant="body2" color="textSecondary">{currency.name}</Typography>
                        <Typography variant="caption" color="textSecondary">
                          Min: {currency.symbol}500
                        </Typography>
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
                  <TableCell>Currency</TableCell>
                  <TableCell>Channel</TableCell>
                  <TableCell>Fee</TableCell>
                  <TableCell>Net Amount</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Reference</TableCell>
                  <TableCell>Date</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transactions.map((tx) => (
                  <TableRow key={tx.id}>
                    <TableCell>
                      <Chip label={tx.transaction_type}
                        color={tx.transaction_type === 'DEPOSIT' ? 'success' : 'warning'} size="small" />
                    </TableCell>
                    <TableCell>{getCurrencySymbol(tx.currency)}{Number(tx.amount).toLocaleString()}</TableCell>
                    <TableCell>{tx.currency}</TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {getChannelIcon(tx.channel)}
                        <Typography variant="body2">{tx.channel || 'N/A'}</Typography>
                      </Box>
                    </TableCell>
                    <TableCell>{getCurrencySymbol(tx.currency)}{Number(tx.fee).toLocaleString()}</TableCell>
                    <TableCell>{getCurrencySymbol(tx.currency)}{Number(tx.net_amount).toLocaleString()}</TableCell>
                    <TableCell>
                      <Chip label={tx.status} color={getStatusColor(tx.status)} size="small" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                        {tx.korapay_ref}
                      </Typography>
                    </TableCell>
                    <TableCell>{new Date(tx.created_at).toLocaleDateString()}</TableCell>
                  </TableRow>
                ))}
                {transactions.length === 0 && (
                  <TableRow><TableCell colSpan={9} align="center">No transactions yet</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      <Dialog open={depositDialogOpen} onClose={() => setDepositDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Deposit {CURRENCIES.find(c => c.code === selectedCurrency)?.symbol}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus margin="dense" label="Amount" type="number" fullWidth variant="outlined" sx={{ mt: 2 }}
            value={depositAmount} onChange={(e) => setDepositAmount(e.target.value)}
            inputProps={{ min: 100 }}
          />
          <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
            Minimum deposit: {getCurrencySymbol(selectedCurrency)}100
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" gutterBottom>Select Payment Channel</Typography>
          <Grid container spacing={1}>
            {CHANNELS.map((channel) => (
              <Grid item xs={6} key={channel.id}>
                <Card
                  sx={{
                    cursor: 'pointer',
                    border: selectedChannel === channel.id ? '2px solid #1976d2' : '1px solid #e0e0e0',
                    bgcolor: selectedChannel === channel.id ? '#e3f2fd' : 'inherit',
                  }}
                  onClick={() => setSelectedChannel(channel.id)}
                >
                  <CardContent sx={{ textAlign: 'center', py: 1 }}>
                    {channel.icon}
                    <Typography variant="body2">{channel.name}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDepositDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleDeposit}
            disabled={submitting || !depositAmount || parseFloat(depositAmount) < 100}>
            {submitting ? <CircularProgress size={20} /> : 'Deposit via Korapay'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={withdrawDialogOpen} onClose={() => setWithdrawDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Withdraw {CURRENCIES.find(c => c.code === selectedCurrency)?.symbol}
        </DialogTitle>
        <DialogContent>
          <TextField autoFocus margin="dense" label="Amount" type="number" fullWidth variant="outlined" sx={{ mt: 2 }}
            value={withdrawAmount} onChange={(e) => setWithdrawAmount(e.target.value)}
            inputProps={{ min: 500 }}
          />
          <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
            Minimum withdrawal: {getCurrencySymbol(selectedCurrency)}500
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWithdrawDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="secondary" onClick={handleWithdraw}
            disabled={submitting || !withdrawAmount || parseFloat(withdrawAmount) < 500}>
            {submitting ? <CircularProgress size={20} /> : 'Withdraw'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Payments;

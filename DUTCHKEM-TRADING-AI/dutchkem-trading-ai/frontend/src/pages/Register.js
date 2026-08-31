import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box, Container, Paper, Typography, TextField, Button,
  Link, Alert, Grid
} from '@mui/material';
import { AccountBalance } from '@mui/icons-material';
import { registerUser } from '../features/auth/authSlice';

function Register() {
  const [formData, setFormData] = useState({
    username: '', email: '', password: '', password_confirm: '',
    first_name: '', last_name: ''
  });
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error } = useSelector((state) => state.auth);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.password !== formData.password_confirm) {
      return;
    }
    const result = await dispatch(registerUser(formData));
    if (!result.error) {
      navigate('/');
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'background.default' }}>
      <Container maxWidth="sm">
        <Paper elevation={3} sx={{ p: 4 }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 3 }}>
            <AccountBalance sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
            <Typography variant="h4" fontWeight="bold">Create Account</Typography>
            <Typography color="textSecondary">Join Dutchkem Trading AI</Typography>
          </Box>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <form onSubmit={handleSubmit}>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField fullWidth label="First Name" value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })} required />
              </Grid>
              <Grid item xs={6}>
                <TextField fullWidth label="Last Name" value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })} required />
              </Grid>
              <Grid item xs={12}>
                <TextField fullWidth label="Username" value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })} required />
              </Grid>
              <Grid item xs={12}>
                <TextField fullWidth label="Email" type="email" value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })} required />
              </Grid>
              <Grid item xs={12}>
                <TextField fullWidth label="Password" type="password" value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })} required />
              </Grid>
              <Grid item xs={12}>
                <TextField fullWidth label="Confirm Password" type="password" value={formData.password_confirm}
                  onChange={(e) => setFormData({ ...formData, password_confirm: e.target.value })} required />
              </Grid>
            </Grid>
            <Button fullWidth variant="contained" type="submit" size="large" disabled={loading}
              sx={{ mt: 3, mb: 2 }}>
              {loading ? 'Creating Account...' : 'Create Account'}
            </Button>
          </form>

          <Typography variant="body2" align="center">
            Already have an account?{' '}
            <Link component={RouterLink} to="/login">Sign in</Link>
          </Typography>
        </Paper>
      </Container>
    </Box>
  );
}

export default Register;

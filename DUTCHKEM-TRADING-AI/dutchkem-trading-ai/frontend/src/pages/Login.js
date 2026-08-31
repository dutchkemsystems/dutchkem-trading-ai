import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box, Container, Paper, Typography, TextField, Button,
  Link, Alert, InputAdornment, IconButton
} from '@mui/material';
import { Visibility, VisibilityOff, AccountBalance } from '@mui/icons-material';
import { loginUser } from '../features/auth/authSlice';

function Login() {
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error } = useSelector((state) => state.auth);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const result = await dispatch(loginUser(formData));
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
            <Typography variant="h4" fontWeight="bold">Dutchkem AI</Typography>
            <Typography color="textSecondary">Multi-Timeframe Trading Platform</Typography>
          </Box>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <form onSubmit={handleSubmit}>
            <TextField fullWidth label="Username" value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              margin="normal" required />
            <TextField fullWidth label="Password" type={showPassword ? 'text' : 'password'}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              margin="normal" required
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword(!showPassword)}>
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                )
              }} />
            <Button fullWidth variant="contained" type="submit" size="large" disabled={loading}
              sx={{ mt: 3, mb: 2 }}>
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <Typography variant="body2" align="center">
            Don't have an account?{' '}
            <Link component={RouterLink} to="/register">Sign up</Link>
          </Typography>
        </Paper>
      </Container>
    </Box>
  );
}

export default Login;

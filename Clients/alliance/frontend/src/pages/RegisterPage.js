import React, { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Link,
  CircularProgress,
  Container,
  Divider,
} from '@mui/material';
import { useAuth } from '../context/AuthContext';

const RegisterPage = () => {
  const navigate = useNavigate();
  const { register, error } = useAuth();
  const [formData, setFormData] = useState({
    conUsername: '',
    conPassword: '',
    dashboardPassword: '',
    confirmPassword: '',
    email: '',
  });
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');

    // Validate passwords match
    if (formData.dashboardPassword !== formData.confirmPassword) {
      setLocalError('Dashboard passwords do not match');
      return;
    }

    if (formData.dashboardPassword.length < 8) {
      setLocalError('Dashboard password must be at least 8 characters');
      return;
    }

    setLoading(true);

    const result = await register(
      formData.conUsername,
      formData.conPassword,
      formData.dashboardPassword,
      formData.email
    );
    setLoading(false);

    if (result.success) {
      navigate('/dashboard');
    } else {
      setLocalError(result.error);
    }
  };

  return (
    <Container maxWidth="sm">
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="100vh"
        py={4}
      >
        <Typography variant="h3" component="h1" gutterBottom color="primary">
          Conlyse
        </Typography>
        <Typography variant="h6" color="textSecondary" gutterBottom>
          Alliance Dashboard
        </Typography>

        <Card sx={{ width: '100%', mt: 4 }}>
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h5" component="h2" gutterBottom align="center">
              Create Account
            </Typography>

            {(localError || error) && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {localError || error}
              </Alert>
            )}

            <Alert severity="info" sx={{ mb: 2 }}>
              Your Conflict of Nations credentials are used to verify your identity.
              They are not stored - only your CoN username is saved.
            </Alert>

            <form onSubmit={handleSubmit}>
              <Typography variant="subtitle2" color="textSecondary" sx={{ mt: 2, mb: 1 }}>
                Conflict of Nations Account
              </Typography>

              <TextField
                fullWidth
                label="CoN Username"
                name="conUsername"
                value={formData.conUsername}
                onChange={handleChange}
                margin="normal"
                required
                autoComplete="username"
                autoFocus
                helperText="Your Conflict of Nations username"
              />

              <TextField
                fullWidth
                label="CoN Password"
                name="conPassword"
                type="password"
                value={formData.conPassword}
                onChange={handleChange}
                margin="normal"
                required
                helperText="Used only for verification - not stored"
              />

              <Divider sx={{ my: 3 }} />

              <Typography variant="subtitle2" color="textSecondary" sx={{ mb: 1 }}>
                Dashboard Account
              </Typography>

              <TextField
                fullWidth
                label="Dashboard Password"
                name="dashboardPassword"
                type="password"
                value={formData.dashboardPassword}
                onChange={handleChange}
                margin="normal"
                required
                helperText="Create a separate password for this dashboard (min 8 characters)"
              />

              <TextField
                fullWidth
                label="Confirm Dashboard Password"
                name="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={handleChange}
                margin="normal"
                required
              />

              <TextField
                fullWidth
                label="Email (optional)"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
                margin="normal"
                helperText="For account recovery"
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                sx={{ mt: 3, mb: 2 }}
              >
                {loading ? <CircularProgress size={24} /> : 'Create Account'}
              </Button>
            </form>

            <Box textAlign="center">
              <Typography variant="body2" color="textSecondary">
                Already have an account?{' '}
                <Link component={RouterLink} to="/login">
                  Sign in
                </Link>
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Box>
    </Container>
  );
};

export default RegisterPage;

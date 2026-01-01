import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  CardActions,
  Grid,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Add as AddIcon,
  GroupAdd as JoinIcon,
  ArrowBack as BackIcon,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { allianceAPI } from '../api';

const AlliancesPage = () => {
  const navigate = useNavigate();
  const { alliances, refreshUser } = useAuth();
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [joinDialogOpen, setJoinDialogOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Create alliance form
  const [createForm, setCreateForm] = useState({
    name: '',
    tag: '',
    description: '',
  });

  // Join alliance form
  const [inviteCode, setInviteCode] = useState('');

  const handleCreateAlliance = async () => {
    setError(null);
    setLoading(true);
    try {
      await allianceAPI.create(createForm);
      setSuccess('Alliance created successfully!');
      setCreateDialogOpen(false);
      setCreateForm({ name: '', tag: '', description: '' });
      await refreshUser();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create alliance');
    }
    setLoading(false);
  };

  const handleJoinAlliance = async () => {
    setError(null);
    setLoading(true);
    try {
      await allianceAPI.join(inviteCode);
      setSuccess('Successfully joined alliance!');
      setJoinDialogOpen(false);
      setInviteCode('');
      await refreshUser();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to join alliance');
    }
    setLoading(false);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box display="flex" alignItems="center" gap={2} mb={4}>
        <IconButton onClick={() => navigate('/dashboard')}>
          <BackIcon />
        </IconButton>
        <Box flex={1}>
          <Typography variant="h4" component="h1">
            Your Alliances
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Manage your alliance memberships
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<JoinIcon />}
          onClick={() => setJoinDialogOpen(true)}
        >
          Join Alliance
        </Button>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Alliance
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Alliance List */}
      {alliances.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="textSecondary" gutterBottom>
              You're not a member of any alliances yet
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 3 }}>
              Create a new alliance or join an existing one with an invite code
            </Typography>
            <Box display="flex" gap={2} justifyContent="center">
              <Button
                variant="outlined"
                startIcon={<JoinIcon />}
                onClick={() => setJoinDialogOpen(true)}
              >
                Join Alliance
              </Button>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => setCreateDialogOpen(true)}
              >
                Create Alliance
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {alliances.map((alliance) => (
            <Grid item xs={12} sm={6} md={4} key={alliance.alliance_id}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  cursor: 'pointer',
                  '&:hover': { boxShadow: 6 },
                }}
                onClick={() => navigate(`/alliances/${alliance.alliance_id}`)}
              >
                <CardContent sx={{ flex: 1 }}>
                  <Box display="flex" alignItems="center" gap={1} mb={1}>
                    <Chip
                      label={alliance.tag}
                      color="primary"
                      size="small"
                    />
                    <Chip
                      label={alliance.role}
                      variant="outlined"
                      size="small"
                      color={alliance.role === 'owner' ? 'warning' : 'default'}
                    />
                  </Box>
                  <Typography variant="h6" gutterBottom>
                    {alliance.name}
                  </Typography>
                  {alliance.description && (
                    <Typography variant="body2" color="textSecondary">
                      {alliance.description}
                    </Typography>
                  )}
                  <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                    {alliance.member_count} member{alliance.member_count !== 1 ? 's' : ''}
                  </Typography>
                </CardContent>
                <CardActions>
                  <Button size="small" color="primary">
                    View Details
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {/* Create Alliance Dialog */}
      <Dialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create New Alliance</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Alliance Name"
            value={createForm.name}
            onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Tag (e.g., ABC)"
            value={createForm.tag}
            onChange={(e) => setCreateForm({ ...createForm, tag: e.target.value.toUpperCase() })}
            margin="normal"
            required
            inputProps={{ maxLength: 10 }}
            helperText="Short identifier shown in brackets, e.g., [ABC]"
          />
          <TextField
            fullWidth
            label="Description (optional)"
            value={createForm.description}
            onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
            margin="normal"
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateAlliance}
            variant="contained"
            disabled={loading || !createForm.name || !createForm.tag}
          >
            {loading ? <CircularProgress size={24} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Join Alliance Dialog */}
      <Dialog
        open={joinDialogOpen}
        onClose={() => setJoinDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Join Alliance</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            Enter the invite code provided by an alliance admin
          </Typography>
          <TextField
            fullWidth
            label="Invite Code"
            value={inviteCode}
            onChange={(e) => setInviteCode(e.target.value)}
            margin="normal"
            required
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setJoinDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleJoinAlliance}
            variant="contained"
            disabled={loading || !inviteCode}
          >
            {loading ? <CircularProgress size={24} /> : 'Join'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AlliancesPage;

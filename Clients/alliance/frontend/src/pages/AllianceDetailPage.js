import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  IconButton,
  Chip,
  Alert,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  ContentCopy as CopyIcon,
  Refresh as RefreshIcon,
  ExitToApp as LeaveIcon,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { allianceAPI, dashboardAPI } from '../api';

const AllianceDetailPage = () => {
  const { allianceId } = useParams();
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();

  const [alliance, setAlliance] = useState(null);
  const [myRole, setMyRole] = useState(null);
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);
  const [copiedInvite, setCopiedInvite] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [allianceResponse, gamesResponse] = await Promise.all([
        allianceAPI.get(allianceId),
        dashboardAPI.getAllianceGames(allianceId),
      ]);
      setAlliance(allianceResponse.data.alliance);
      setMyRole(allianceResponse.data.my_role);
      setGames(gamesResponse.data.games || []);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load alliance data');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, [allianceId]);

  const handleCopyInvite = () => {
    navigator.clipboard.writeText(alliance.invite_code);
    setCopiedInvite(true);
    setTimeout(() => setCopiedInvite(false), 2000);
  };

  const handleRegenerateInvite = async () => {
    try {
      const response = await allianceAPI.regenerateInvite(allianceId);
      setAlliance({ ...alliance, invite_code: response.data.invite_code });
      setSuccess('Invite code regenerated');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to regenerate invite code');
    }
  };

  const handleLeave = async () => {
    try {
      await allianceAPI.leave(allianceId);
      await refreshUser();
      navigate('/alliances');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to leave alliance');
    }
    setLeaveDialogOpen(false);
  };

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (!alliance) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">Alliance not found</Alert>
      </Container>
    );
  }

  const activeGames = games.filter(g => g.is_active);
  const isAdmin = myRole === 'owner' || myRole === 'admin';

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box display="flex" alignItems="center" gap={2} mb={4}>
        <IconButton onClick={() => navigate('/alliances')}>
          <BackIcon />
        </IconButton>
        <Box flex={1}>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip label={alliance.tag} color="primary" />
            <Typography variant="h4" component="h1">
              {alliance.name}
            </Typography>
          </Box>
          {alliance.description && (
            <Typography variant="body1" color="textSecondary">
              {alliance.description}
            </Typography>
          )}
        </Box>
        <Tooltip title="Refresh">
          <IconButton onClick={fetchData}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
        {myRole !== 'owner' && (
          <Button
            color="error"
            startIcon={<LeaveIcon />}
            onClick={() => setLeaveDialogOpen(true)}
          >
            Leave
          </Button>
        )}
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

      <Grid container spacing={3}>
        {/* Invite Code Card */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Invite Code
              </Typography>
              <Box display="flex" alignItems="center" gap={1}>
                <TextField
                  value={alliance.invite_code}
                  InputProps={{ readOnly: true }}
                  size="small"
                  fullWidth
                />
                <Tooltip title={copiedInvite ? 'Copied!' : 'Copy'}>
                  <IconButton onClick={handleCopyInvite}>
                    <CopyIcon />
                  </IconButton>
                </Tooltip>
              </Box>
              {isAdmin && (
                <Button
                  size="small"
                  onClick={handleRegenerateInvite}
                  sx={{ mt: 1 }}
                >
                  Regenerate Code
                </Button>
              )}
              <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                Share this code with players you want to invite
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Stats Card */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Alliance Stats
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Typography variant="h4" color="primary">
                    {alliance.members?.length || 0}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Members
                  </Typography>
                </Grid>
                <Grid item xs={6}>
                  <Typography variant="h4" color="primary">
                    {activeGames.length}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Active Games
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Members List */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Members
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Player</TableCell>
                      <TableCell>Role</TableCell>
                      <TableCell>Joined</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {alliance.members?.map((member) => (
                      <TableRow key={member.membership_id}>
                        <TableCell>
                          {member.user?.con_username}
                          {member.user?.user_id === user?.user_id && (
                            <Chip label="You" size="small" sx={{ ml: 1 }} />
                          )}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={member.role}
                            size="small"
                            color={member.role === 'owner' ? 'warning' : 'default'}
                          />
                        </TableCell>
                        <TableCell>
                          {member.joined_at
                            ? new Date(member.joined_at).toLocaleDateString()
                            : 'N/A'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Games */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Alliance Games ({activeGames.length} active)
              </Typography>
              {activeGames.length === 0 ? (
                <Typography variant="body2" color="textSecondary">
                  No active games found for alliance members
                </Typography>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Game ID</TableCell>
                        <TableCell>Scenario</TableCell>
                        <TableCell>Members Playing</TableCell>
                        <TableCell>Started</TableCell>
                        <TableCell>Speed</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {activeGames.map((game) => (
                        <TableRow
                          key={game.game_id}
                          hover
                          sx={{ cursor: 'pointer' }}
                          onClick={() => window.open(`/game/${game.game_id}/dashboard`, '_blank')}
                        >
                          <TableCell>{game.game_id}</TableCell>
                          <TableCell>{game.scenario_name}</TableCell>
                          <TableCell>
                            {game.members?.map((m, i) => (
                              <Chip
                                key={i}
                                label={m.player_name}
                                size="small"
                                sx={{ mr: 0.5, mb: 0.5 }}
                              />
                            ))}
                          </TableCell>
                          <TableCell>{formatDate(game.start_time)}</TableCell>
                          <TableCell>
                            <Chip
                              label={`${game.speed}x`}
                              size="small"
                              color={game.speed === 4 ? 'warning' : 'default'}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Leave Dialog */}
      <Dialog open={leaveDialogOpen} onClose={() => setLeaveDialogOpen(false)}>
        <DialogTitle>Leave Alliance</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to leave {alliance.name}?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setLeaveDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleLeave} color="error">
            Leave
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AllianceDetailPage;

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Button,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Groups as GroupsIcon,
  SportsEsports as GameIcon,
  TrendingUp as TrendingUpIcon,
  EmojiEvents as TrophyIcon,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { dashboardAPI } from '../api';

const DashboardPage = () => {
  const navigate = useNavigate();
  const { user, alliances } = useAuth();
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({});

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const gamesResponse = await dashboardAPI.getMyGames();
      const gamesData = gamesResponse.data.games || [];
      setGames(gamesData);

      // Fetch stats for active games
      const activeGames = gamesData.filter(g => g.is_active);
      const statsPromises = activeGames.slice(0, 5).map(async (game) => {
        try {
          const statsResponse = await dashboardAPI.getMyStats(game.game_id);
          return { gameId: game.game_id, ...statsResponse.data };
        } catch (err) {
          return { gameId: game.game_id, error: true };
        }
      });
      const statsResults = await Promise.all(statsPromises);
      const statsMap = {};
      statsResults.forEach(s => { statsMap[s.gameId] = s; });
      setStats(statsMap);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load dashboard data');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchData();
  }, []);

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp * 1000).toLocaleDateString();
  };

  const activeGames = games.filter(g => g.is_active);
  const completedGames = games.filter(g => !g.is_active);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
        <Box>
          <Typography variant="h4" component="h1">
            Welcome, {user?.con_username}
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Your personal Conflict of Nations dashboard
          </Typography>
        </Box>
        <Tooltip title="Refresh data">
          <IconButton onClick={fetchData} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <GameIcon color="primary" />
                <Typography variant="h6">{activeGames.length}</Typography>
              </Box>
              <Typography variant="body2" color="textSecondary">
                Active Games
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <TrophyIcon color="warning" />
                <Typography variant="h6">{completedGames.length}</Typography>
              </Box>
              <Typography variant="body2" color="textSecondary">
                Completed Games
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <GroupsIcon color="secondary" />
                <Typography variant="h6">{alliances.length}</Typography>
              </Box>
              <Typography variant="body2" color="textSecondary">
                Alliances
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ cursor: 'pointer' }} onClick={() => navigate('/alliances')}>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <TrendingUpIcon color="success" />
                <Typography variant="h6">View</Typography>
              </Box>
              <Typography variant="body2" color="textSecondary">
                Alliance Dashboard
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Alliances Quick View */}
      {alliances.length > 0 && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Your Alliances
            </Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {alliances.map((alliance) => (
                <Chip
                  key={alliance.alliance_id}
                  label={`[${alliance.tag}] ${alliance.name}`}
                  color="primary"
                  variant="outlined"
                  onClick={() => navigate(`/alliances/${alliance.alliance_id}`)}
                />
              ))}
              <Button
                variant="outlined"
                size="small"
                onClick={() => navigate('/alliances')}
              >
                Manage Alliances
              </Button>
            </Box>
          </CardContent>
        </Card>
      )}

      {/* Active Games */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Active Games
      </Typography>

      {loading ? (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress />
        </Box>
      ) : activeGames.length === 0 ? (
        <Alert severity="info">
          No active games found. Games you join will appear here once they're being tracked.
        </Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Game ID</TableCell>
                <TableCell>Scenario</TableCell>
                <TableCell>Country</TableCell>
                <TableCell>Victory Points</TableCell>
                <TableCell>Provinces</TableCell>
                <TableCell>Started</TableCell>
                <TableCell>Speed</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {activeGames.map((game) => {
                const gameStats = stats[game.game_id];
                return (
                  <TableRow
                    key={game.game_id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => window.open(`/game/${game.game_id}/dashboard`, '_blank')}
                  >
                    <TableCell>{game.game_id}</TableCell>
                    <TableCell>{game.scenario_name}</TableCell>
                    <TableCell>{game.country_name || 'Unknown'}</TableCell>
                    <TableCell>
                      {gameStats?.stats?.victory_points ?? '-'}
                    </TableCell>
                    <TableCell>
                      {gameStats?.stats?.province_count ?? '-'}
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
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Completed Games */}
      {completedGames.length > 0 && (
        <>
          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            Completed Games
          </Typography>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Game ID</TableCell>
                  <TableCell>Scenario</TableCell>
                  <TableCell>Country</TableCell>
                  <TableCell>Started</TableCell>
                  <TableCell>Ended</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {completedGames.slice(0, 10).map((game) => (
                  <TableRow
                    key={game.game_id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => window.open(`/game/${game.game_id}/dashboard`, '_blank')}
                  >
                    <TableCell>{game.game_id}</TableCell>
                    <TableCell>{game.scenario_name}</TableCell>
                    <TableCell>{game.country_name || 'Unknown'}</TableCell>
                    <TableCell>{formatDate(game.start_time)}</TableCell>
                    <TableCell>{formatDate(game.end_time)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Container>
  );
};

export default DashboardPage;

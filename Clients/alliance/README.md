# Conlyse Alliance Dashboard

A multi-tenant dashboard for Conflict of Nations players to track their games and collaborate with alliance members.

## Features

- **User Authentication**: Verify identity using Conflict of Nations credentials
- **Personal Dashboard**: View your games, stats, and progress across all tracked games
- **Alliance Management**: Create and join alliances with other players
- **Alliance Dashboard**: See all games where alliance members are playing
- **Secure**: Passwords are hashed, JWT-based authentication, CoN credentials are verified but not stored

## Quick Start

### Option 1: Fresh Installation (New Database)

1. Clone or copy the alliance folder
2. Create environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```
3. Start with Docker Compose:
   ```bash
   docker-compose up -d
   ```
4. Access at `http://localhost`

### Option 2: Connect to Existing Conlyse Database

1. Create environment file:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` with your existing database credentials:
   ```
   MYSQL_IP_ADDR=your-database-host
   MYSQL_DATABASE=your-database-name
   MYSQL_USER=your-database-user
   MYSQL_USER_PASSWORD=your-database-password
   ```
3. Start with external database compose file:
   ```bash
   docker-compose -f docker-compose.external-db.yml up -d
   ```

## Cloudflare Deployment

### Using Cloudflare Containers

1. Build and push your images to a container registry:
   ```bash
   docker build -t your-registry/conlyse-alliance-backend ./backend
   docker build -t your-registry/conlyse-alliance-frontend ./frontend
   docker push your-registry/conlyse-alliance-backend
   docker push your-registry/conlyse-alliance-frontend
   ```

2. Deploy to Cloudflare Containers following their documentation

3. Configure environment variables in Cloudflare dashboard

### Using Cloudflare Tunnel (Recommended for Self-Hosted)

1. Install cloudflared:
   ```bash
   # On Ubuntu/Debian
   curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
   sudo dpkg -i cloudflared.deb
   ```

2. Authenticate and create tunnel:
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create conlyse-alliance
   ```

3. Create tunnel config (`~/.cloudflared/config.yml`):
   ```yaml
   tunnel: YOUR_TUNNEL_ID
   credentials-file: /root/.cloudflared/YOUR_TUNNEL_ID.json

   ingress:
     - hostname: alliance.yourdomain.com
       service: http://localhost:80
     - service: http_status:404
   ```

4. Run the tunnel:
   ```bash
   cloudflared tunnel run conlyse-alliance
   ```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│                   - Login/Register pages                     │
│                   - Personal Dashboard                       │
│                   - Alliance Management                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend API (Flask)                     │
│                   - JWT Authentication                       │
│                   - Alliance CRUD                            │
│                   - Dashboard Data                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ SQLAlchemy
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MySQL Database                            │
│              - Existing Conlyse tables                       │
│              - New alliance_* tables                         │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user (requires CoN credentials)
- `POST /api/auth/login` - Login with dashboard password
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/refresh` - Refresh JWT token

### Alliances
- `GET /api/alliances` - List user's alliances
- `POST /api/alliances` - Create new alliance
- `GET /api/alliances/:id` - Get alliance details
- `POST /api/alliances/join` - Join alliance with invite code
- `POST /api/alliances/:id/leave` - Leave alliance
- `POST /api/alliances/:id/regenerate-invite` - Regenerate invite code

### Dashboard
- `GET /api/dashboard/my-games` - Get user's games
- `GET /api/dashboard/my-stats/:gameId` - Get user's stats for a game
- `GET /api/dashboard/alliance/:allianceId/games` - Get alliance games

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET` | Flask session secret key | Random |
| `JWT_SECRET` | JWT signing secret | Random |
| `JWT_EXPIRATION_HOURS` | Token expiration time | 24 |
| `MYSQL_USER` | Database username | conlyse |
| `MYSQL_USER_PASSWORD` | Database password | - |
| `MYSQL_IP_ADDR` | Database host | db |
| `MYSQL_DATABASE` | Database name | conlyse |
| `DEBUG` | Enable debug mode | false |
| `CORS_ORIGINS` | Allowed CORS origins | * |

## Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python api.py
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Security Notes

1. **CoN Password Verification**: The CoN password is only used during registration to verify the user owns the account. It is NOT stored.

2. **Dashboard Password**: Users create a separate password for the dashboard, which is hashed using Werkzeug's secure password hashing.

3. **JWT Tokens**: Authentication uses JWT tokens with configurable expiration.

4. **HTTPS**: Always use HTTPS in production. Cloudflare provides this automatically.

## Database Tables

The alliance dashboard creates these additional tables:

- `alliance_user` - Dashboard user accounts
- `alliance` - Alliance definitions
- `alliance_membership` - User-Alliance relationships
- `alliance_watched_game` - Games tracked by alliances

These tables are created automatically on first run and don't interfere with existing Conlyse tables.

## Troubleshooting

### "Could not verify CoN credentials"
- Check that the CoN username and password are correct
- The CoN servers may be temporarily unavailable

### "No tracked games found"
- Ensure the Conlyse bot is running and tracking games
- The username must match exactly (case-insensitive)

### Database connection errors
- Verify database credentials in `.env`
- Ensure the database is accessible from the container

## License

MIT License - See LICENSE file for details.

"""
Alliance Dashboard API
Flask REST API for user authentication, alliance management, and personalized dashboards.
"""
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_compress import Compress
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, and_, or_, case
from sqlalchemy.orm import aliased
import jwt

from dotenv import load_dotenv

from models import Base, User, Alliance, AllianceMembership, WatchedGame
from con_auth import verify_con_credentials

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET', secrets.token_hex(32))
app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', secrets.token_hex(32))
app.config['JWT_EXPIRATION_HOURS'] = int(os.getenv('JWT_EXPIRATION_HOURS', 24))

# Database configuration - connects to existing Conlyse database
app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"mysql+mysqlconnector://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_USER_PASSWORD')}"
    f"@{os.getenv('MYSQL_IP_ADDR')}/{os.getenv('MYSQL_DATABASE')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = os.getenv('DEBUG', 'false').lower() == 'true'

# Initialize extensions
db = SQLAlchemy(app)
Compress(app)
CORS(app, origins=os.getenv('CORS_ORIGINS', '*').split(','))


# Import existing Conlyse models for data access
from sqlalchemy import BigInteger, Boolean, Column, Float, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship


class Player(db.Model):
    """Existing player table from Conlyse."""
    __tablename__ = 'player'
    __table_args__ = {'extend_existing': True}

    player_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True)
    site_user_id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(75), nullable=False)


class Game(db.Model):
    """Existing game table from Conlyse."""
    __tablename__ = 'game'
    __table_args__ = {'extend_existing': True}

    game_id = Column(Integer, primary_key=True)
    scenario_id = Column(Integer, nullable=False)
    start_time = Column(TIMESTAMP)
    end_time = Column(TIMESTAMP)
    current_time = Column(TIMESTAMP)
    next_day_time = Column(TIMESTAMP)
    open_slots = Column(Integer)


class Scenario(db.Model):
    """Existing scenario table from Conlyse."""
    __tablename__ = 'scenario'
    __table_args__ = {'extend_existing': True}

    scenario_id = Column(Integer, primary_key=True)
    map_id = Column(Integer)
    name = Column(String(45))
    speed = Column(Integer)


class GameHasPlayer(db.Model):
    """Existing game_has_player table from Conlyse."""
    __tablename__ = 'game_has_player'
    __table_args__ = {'extend_existing': True}

    game_id = Column(Integer, ForeignKey('game.game_id'), primary_key=True, nullable=False)
    player_id = Column(BigInteger, ForeignKey('player.player_id'), primary_key=True, nullable=False)
    country_id = Column(BigInteger, nullable=False)


class Country(db.Model):
    """Existing country table from Conlyse."""
    __tablename__ = 'country'
    __table_args__ = {'extend_existing': True}

    universal_country_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True)
    country_id = Column(BigInteger, nullable=False)
    team_id = Column(Integer)
    capital_id = Column(Integer)
    defeated = Column(Boolean)
    computer = Column(Boolean)
    valid_from = Column(TIMESTAMP, nullable=False)
    valid_until = Column(TIMESTAMP)
    game_id = Column(Integer, ForeignKey('game.game_id'), primary_key=True, nullable=False)
    static_country_id = Column(Integer, primary_key=True, nullable=False)


class StaticCountry(db.Model):
    """Existing static_country table from Conlyse."""
    __tablename__ = 'static_country'
    __table_args__ = {'extend_existing': True}

    static_country_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(45))
    map_id = Column(Integer)
    native_computer = Column(Boolean)
    country_id = Column(Integer)
    faction = Column(Integer)


class Province(db.Model):
    """Existing province table from Conlyse."""
    __tablename__ = 'province'
    __table_args__ = {'extend_existing': True}

    province_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True)
    owner_id = Column(BigInteger, nullable=False)
    morale = Column(Integer)
    province_state_id = Column(Integer)
    victory_points = Column(Integer)
    resource_production = Column(Integer)
    tax_production = Column(Integer)
    valid_from = Column(TIMESTAMP, nullable=False)
    valid_until = Column(TIMESTAMP)
    game_id = Column(Integer, ForeignKey('game.game_id'), primary_key=True, nullable=False)
    static_province_id = Column(Integer, primary_key=True, nullable=False)


# Create alliance tables
with app.app_context():
    Base.metadata.create_all(db.engine)


# =============================================================================
# JWT Authentication
# =============================================================================

def generate_token(user_id: int) -> str:
    """Generate a JWT token for a user."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=app.config['JWT_EXPIRATION_HOURS']),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, app.config['JWT_SECRET'], algorithm='HS256')


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require valid JWT token for protected routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token is invalid or expired'}), 401

        # Get user from database
        user = db.session.get(User, payload['user_id'])
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated


# =============================================================================
# Authentication Endpoints
# =============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register a new user with CoN credentials.
    Verifies credentials against CoN servers before creating account.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    con_username = data.get('con_username', '').strip()
    con_password = data.get('con_password', '')
    dashboard_password = data.get('dashboard_password', '')
    email = data.get('email', '').strip() or None

    if not con_username or not con_password or not dashboard_password:
        return jsonify({'error': 'CoN username, CoN password, and dashboard password are required'}), 400

    if len(dashboard_password) < 8:
        return jsonify({'error': 'Dashboard password must be at least 8 characters'}), 400

    # Check if user already exists
    existing_user = db.session.query(User).filter(
        func.lower(User.con_username) == con_username.lower()
    ).first()

    if existing_user:
        return jsonify({'error': 'User with this CoN username already registered'}), 409

    # Verify CoN credentials
    auth_result = verify_con_credentials(con_username, con_password)

    if not auth_result['success']:
        return jsonify({
            'error': 'Could not verify CoN credentials',
            'details': auth_result.get('error', 'Unknown error')
        }), 401

    # Try to find player in existing Conlyse data
    player = db.session.query(Player).filter(
        func.lower(Player.name) == con_username.lower()
    ).first()

    # Create new user
    user = User(
        con_username=con_username,
        con_player_id=auth_result.get('player_id') or (player.player_id if player else None),
        con_site_user_id=auth_result.get('site_user_id') or (player.site_user_id if player else None),
        email=email,
    )
    user.set_password(dashboard_password)

    db.session.add(user)
    db.session.commit()

    # Generate token
    token = generate_token(user.user_id)

    return jsonify({
        'message': 'Registration successful',
        'token': token,
        'user': user.to_dict(),
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Log in with dashboard credentials.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    con_username = data.get('con_username', '').strip()
    password = data.get('password', '')

    if not con_username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    # Find user
    user = db.session.query(User).filter(
        func.lower(User.con_username) == con_username.lower()
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 401

    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()

    # Generate token
    token = generate_token(user.user_id)

    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': user.to_dict(),
    })


@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current authenticated user's info."""
    user = g.current_user

    # Get user's alliances
    memberships = db.session.query(AllianceMembership).filter(
        AllianceMembership.user_id == user.user_id
    ).all()

    alliances = []
    for m in memberships:
        alliance_data = m.alliance.to_dict()
        alliance_data['role'] = m.role
        alliances.append(alliance_data)

    return jsonify({
        'user': user.to_dict(),
        'alliances': alliances,
    })


@app.route('/api/auth/refresh', methods=['POST'])
@token_required
def refresh_token():
    """Refresh the JWT token."""
    user = g.current_user
    token = generate_token(user.user_id)
    return jsonify({'token': token})


# =============================================================================
# Alliance Endpoints
# =============================================================================

@app.route('/api/alliances', methods=['GET'])
@token_required
def list_alliances():
    """List alliances the current user belongs to."""
    user = g.current_user

    memberships = db.session.query(AllianceMembership).filter(
        AllianceMembership.user_id == user.user_id
    ).all()

    alliances = []
    for m in memberships:
        alliance_data = m.alliance.to_dict(include_members=True)
        alliance_data['my_role'] = m.role
        alliances.append(alliance_data)

    return jsonify({'alliances': alliances})


@app.route('/api/alliances', methods=['POST'])
@token_required
def create_alliance():
    """Create a new alliance."""
    user = g.current_user
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    name = data.get('name', '').strip()
    tag = data.get('tag', '').strip().upper()
    description = data.get('description', '').strip() or None
    is_public = data.get('is_public', False)

    if not name or not tag:
        return jsonify({'error': 'Alliance name and tag are required'}), 400

    if len(tag) > 10:
        return jsonify({'error': 'Tag must be 10 characters or less'}), 400

    # Check for existing alliance with same name or tag
    existing = db.session.query(Alliance).filter(
        or_(
            func.lower(Alliance.name) == name.lower(),
            func.lower(Alliance.tag) == tag.lower()
        )
    ).first()

    if existing:
        return jsonify({'error': 'Alliance with this name or tag already exists'}), 409

    # Create alliance
    alliance = Alliance(
        name=name,
        tag=tag,
        description=description,
        owner_id=user.user_id,
        invite_code=secrets.token_urlsafe(16),
        is_public=is_public,
    )
    db.session.add(alliance)
    db.session.flush()  # Get alliance_id

    # Add owner as member with owner role
    membership = AllianceMembership(
        user_id=user.user_id,
        alliance_id=alliance.alliance_id,
        role='owner',
    )
    db.session.add(membership)
    db.session.commit()

    return jsonify({
        'message': 'Alliance created successfully',
        'alliance': alliance.to_dict(include_members=True),
    }), 201


@app.route('/api/alliances/<int:alliance_id>', methods=['GET'])
@token_required
def get_alliance(alliance_id):
    """Get alliance details (must be a member)."""
    user = g.current_user

    # Check membership
    membership = db.session.query(AllianceMembership).filter(
        AllianceMembership.alliance_id == alliance_id,
        AllianceMembership.user_id == user.user_id
    ).first()

    if not membership:
        return jsonify({'error': 'You are not a member of this alliance'}), 403

    alliance = db.session.get(Alliance, alliance_id)
    if not alliance:
        return jsonify({'error': 'Alliance not found'}), 404

    return jsonify({
        'alliance': alliance.to_dict(include_members=True),
        'my_role': membership.role,
    })


@app.route('/api/alliances/join', methods=['POST'])
@token_required
def join_alliance():
    """Join an alliance using invite code."""
    user = g.current_user
    data = request.get_json()

    invite_code = data.get('invite_code', '').strip()
    if not invite_code:
        return jsonify({'error': 'Invite code is required'}), 400

    alliance = db.session.query(Alliance).filter(
        Alliance.invite_code == invite_code
    ).first()

    if not alliance:
        return jsonify({'error': 'Invalid invite code'}), 404

    # Check if already a member
    existing = db.session.query(AllianceMembership).filter(
        AllianceMembership.alliance_id == alliance.alliance_id,
        AllianceMembership.user_id == user.user_id
    ).first()

    if existing:
        return jsonify({'error': 'You are already a member of this alliance'}), 409

    # Join alliance
    membership = AllianceMembership(
        user_id=user.user_id,
        alliance_id=alliance.alliance_id,
        role='member',
    )
    db.session.add(membership)
    db.session.commit()

    return jsonify({
        'message': 'Successfully joined alliance',
        'alliance': alliance.to_dict(),
    })


@app.route('/api/alliances/<int:alliance_id>/leave', methods=['POST'])
@token_required
def leave_alliance(alliance_id):
    """Leave an alliance."""
    user = g.current_user

    membership = db.session.query(AllianceMembership).filter(
        AllianceMembership.alliance_id == alliance_id,
        AllianceMembership.user_id == user.user_id
    ).first()

    if not membership:
        return jsonify({'error': 'You are not a member of this alliance'}), 404

    if membership.role == 'owner':
        return jsonify({'error': 'Owner cannot leave. Transfer ownership first or delete the alliance.'}), 400

    db.session.delete(membership)
    db.session.commit()

    return jsonify({'message': 'Successfully left alliance'})


@app.route('/api/alliances/<int:alliance_id>/regenerate-invite', methods=['POST'])
@token_required
def regenerate_invite_code(alliance_id):
    """Regenerate alliance invite code (admin/owner only)."""
    user = g.current_user

    membership = db.session.query(AllianceMembership).filter(
        AllianceMembership.alliance_id == alliance_id,
        AllianceMembership.user_id == user.user_id
    ).first()

    if not membership or membership.role not in ['owner', 'admin']:
        return jsonify({'error': 'Admin privileges required'}), 403

    alliance = db.session.get(Alliance, alliance_id)
    alliance.invite_code = secrets.token_urlsafe(16)
    db.session.commit()

    return jsonify({
        'message': 'Invite code regenerated',
        'invite_code': alliance.invite_code,
    })


# =============================================================================
# Dashboard Endpoints
# =============================================================================

@app.route('/api/dashboard/my-games', methods=['GET'])
@token_required
def get_my_games():
    """Get games where the current user is playing."""
    user = g.current_user

    if not user.con_player_id:
        # Try to find player by username
        player = db.session.query(Player).filter(
            func.lower(Player.name) == user.con_username.lower()
        ).first()

        if not player:
            return jsonify({'games': [], 'message': 'No tracked games found for your account'})

        player_id = player.player_id
    else:
        player_id = user.con_player_id

    # Get all games for this player
    games_query = db.session.query(
        Game.game_id,
        Game.current_time,
        Game.start_time,
        Game.end_time,
        Scenario.name.label('scenario_name'),
        Scenario.speed,
        Scenario.map_id,
        GameHasPlayer.country_id,
        StaticCountry.name.label('country_name'),
    ).join(
        GameHasPlayer, Game.game_id == GameHasPlayer.game_id
    ).join(
        Scenario, Game.scenario_id == Scenario.scenario_id
    ).outerjoin(
        Country, and_(
            Country.game_id == Game.game_id,
            Country.country_id == GameHasPlayer.country_id,
            Country.valid_until == None
        )
    ).outerjoin(
        StaticCountry, Country.static_country_id == StaticCountry.static_country_id
    ).filter(
        GameHasPlayer.player_id == player_id
    ).order_by(Game.start_time.desc())

    games = []
    for g_data in games_query.all():
        games.append({
            'game_id': g_data.game_id,
            'scenario_name': g_data.scenario_name,
            'speed': g_data.speed,
            'map_id': g_data.map_id,
            'country_id': g_data.country_id,
            'country_name': g_data.country_name,
            'start_time': g_data.start_time.timestamp() if g_data.start_time else None,
            'current_time': g_data.current_time.timestamp() if g_data.current_time else None,
            'end_time': g_data.end_time.timestamp() if g_data.end_time else None,
            'is_active': g_data.end_time is None,
        })

    return jsonify({'games': games})


@app.route('/api/dashboard/my-stats/<int:game_id>', methods=['GET'])
@token_required
def get_my_game_stats(game_id):
    """Get the current user's stats for a specific game."""
    user = g.current_user

    # Find player
    if not user.con_player_id:
        player = db.session.query(Player).filter(
            func.lower(Player.name) == user.con_username.lower()
        ).first()
        if not player:
            return jsonify({'error': 'Player not found'}), 404
        player_id = player.player_id
    else:
        player_id = user.con_player_id

    # Get country_id for this game
    game_player = db.session.query(GameHasPlayer).filter(
        GameHasPlayer.game_id == game_id,
        GameHasPlayer.player_id == player_id
    ).first()

    if not game_player:
        return jsonify({'error': 'You are not in this game'}), 404

    country_id = game_player.country_id

    # Get current country stats
    country_stats = db.session.query(
        func.sum(Province.victory_points).label('victory_points'),
        func.avg(Province.morale).label('avg_morale'),
        func.count(Province.province_id).label('province_count'),
        func.sum(Province.resource_production).label('total_resources'),
        func.sum(Province.tax_production).label('total_tax'),
    ).filter(
        Province.game_id == game_id,
        Province.owner_id == country_id,
        Province.valid_until == None
    ).first()

    # Get country info
    country = db.session.query(
        Country, StaticCountry
    ).join(
        StaticCountry, Country.static_country_id == StaticCountry.static_country_id
    ).filter(
        Country.game_id == game_id,
        Country.country_id == country_id,
        Country.valid_until == None
    ).first()

    return jsonify({
        'game_id': game_id,
        'country_id': country_id,
        'country_name': country.StaticCountry.name if country else None,
        'defeated': country.Country.defeated if country else False,
        'stats': {
            'victory_points': int(country_stats.victory_points or 0),
            'avg_morale': round(country_stats.avg_morale or 0, 1),
            'province_count': int(country_stats.province_count or 0),
            'total_resources': int(country_stats.total_resources or 0),
            'total_tax': int(country_stats.total_tax or 0),
        }
    })


@app.route('/api/dashboard/alliance/<int:alliance_id>/games', methods=['GET'])
@token_required
def get_alliance_games(alliance_id):
    """Get all games where alliance members are playing."""
    user = g.current_user

    # Check membership
    membership = db.session.query(AllianceMembership).filter(
        AllianceMembership.alliance_id == alliance_id,
        AllianceMembership.user_id == user.user_id
    ).first()

    if not membership:
        return jsonify({'error': 'You are not a member of this alliance'}), 403

    # Get all alliance members' player IDs
    members = db.session.query(AllianceMembership, User).join(
        User, AllianceMembership.user_id == User.user_id
    ).filter(
        AllianceMembership.alliance_id == alliance_id
    ).all()

    player_ids = []
    username_to_user = {}
    for m, u in members:
        if u.con_player_id:
            player_ids.append(u.con_player_id)
        username_to_user[u.con_username.lower()] = u

    # Also find players by username
    players = db.session.query(Player).filter(
        func.lower(Player.name).in_([un.lower() for un in username_to_user.keys()])
    ).all()

    for p in players:
        if p.player_id not in player_ids:
            player_ids.append(p.player_id)

    if not player_ids:
        return jsonify({'games': []})

    # Get all games for these players
    games_query = db.session.query(
        Game.game_id,
        Game.current_time,
        Game.start_time,
        Game.end_time,
        Scenario.name.label('scenario_name'),
        Scenario.speed,
    ).join(
        GameHasPlayer, Game.game_id == GameHasPlayer.game_id
    ).join(
        Scenario, Game.scenario_id == Scenario.scenario_id
    ).filter(
        GameHasPlayer.player_id.in_(player_ids)
    ).distinct().order_by(Game.start_time.desc())

    games = []
    for g_data in games_query.all():
        # Get members playing in this game
        members_in_game = db.session.query(
            GameHasPlayer.country_id,
            Player.name
        ).join(
            Player, GameHasPlayer.player_id == Player.player_id
        ).filter(
            GameHasPlayer.game_id == g_data.game_id,
            GameHasPlayer.player_id.in_(player_ids)
        ).all()

        games.append({
            'game_id': g_data.game_id,
            'scenario_name': g_data.scenario_name,
            'speed': g_data.speed,
            'start_time': g_data.start_time.timestamp() if g_data.start_time else None,
            'current_time': g_data.current_time.timestamp() if g_data.current_time else None,
            'end_time': g_data.end_time.timestamp() if g_data.end_time else None,
            'is_active': g_data.end_time is None,
            'members': [{'player_name': m.name, 'country_id': m.country_id} for m in members_in_game],
        })

    return jsonify({'games': games})


# =============================================================================
# Health Check
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
    })


# =============================================================================
# Run Server
# =============================================================================

if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)

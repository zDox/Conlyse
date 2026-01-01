"""
Database models for the Alliance Dashboard.
Extends the existing Conlyse database with user authentication and alliance management.
"""
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Column, Float, ForeignKey, Index, Integer, String, TIMESTAMP, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()


class User(Base):
    """
    Authenticated user of the alliance dashboard.
    Linked to a Conflict of Nations player account.
    """
    __tablename__ = 'alliance_user'

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    con_username = Column(String(75), unique=True, nullable=False)  # CoN username
    con_player_id = Column(BigInteger, nullable=True)  # Linked player_id from player table
    con_site_user_id = Column(BigInteger, nullable=True)  # CoN site_user_id
    password_hash = Column(String(256), nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    last_login = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    memberships = relationship('AllianceMembership', back_populates='user', cascade='all, delete-orphan')
    owned_alliances = relationship('Alliance', back_populates='owner', foreign_keys='Alliance.owner_id')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert user to dictionary for API responses."""
        return {
            'user_id': self.user_id,
            'con_username': self.con_username,
            'con_player_id': self.con_player_id,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


class Alliance(Base):
    """
    An alliance is a group of players who play together across multiple games.
    """
    __tablename__ = 'alliance'

    alliance_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    tag = Column(String(10), unique=True, nullable=False)  # Short tag like [ABC]
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey('alliance_user.user_id'), nullable=False)
    invite_code = Column(String(32), unique=True, nullable=False)  # For joining
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    is_public = Column(Boolean, default=False)  # Whether anyone can join

    # Relationships
    owner = relationship('User', back_populates='owned_alliances', foreign_keys=[owner_id])
    members = relationship('AllianceMembership', back_populates='alliance', cascade='all, delete-orphan')

    def to_dict(self, include_members=False):
        """Convert alliance to dictionary for API responses."""
        data = {
            'alliance_id': self.alliance_id,
            'name': self.name,
            'tag': self.tag,
            'description': self.description,
            'owner_id': self.owner_id,
            'invite_code': self.invite_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_public': self.is_public,
            'member_count': len(self.members) if self.members else 0,
        }
        if include_members:
            data['members'] = [m.to_dict() for m in self.members]
        return data


class AllianceMembership(Base):
    """
    Junction table for users belonging to alliances.
    Users can belong to multiple alliances.
    """
    __tablename__ = 'alliance_membership'

    membership_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('alliance_user.user_id'), nullable=False)
    alliance_id = Column(Integer, ForeignKey('alliance.alliance_id'), nullable=False)
    role = Column(String(20), default='member')  # 'owner', 'admin', 'member'
    joined_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    user = relationship('User', back_populates='memberships')
    alliance = relationship('Alliance', back_populates='members')

    # Unique constraint - user can only be in an alliance once
    __table_args__ = (
        Index('ix_user_alliance', 'user_id', 'alliance_id', unique=True),
    )

    def to_dict(self):
        """Convert membership to dictionary for API responses."""
        return {
            'membership_id': self.membership_id,
            'user_id': self.user_id,
            'alliance_id': self.alliance_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'user': {
                'user_id': self.user.user_id,
                'con_username': self.user.con_username,
            } if self.user else None,
        }


class WatchedGame(Base):
    """
    Games that an alliance is tracking/watching together.
    """
    __tablename__ = 'alliance_watched_game'

    watched_id = Column(Integer, primary_key=True, autoincrement=True)
    alliance_id = Column(Integer, ForeignKey('alliance.alliance_id'), nullable=False)
    game_id = Column(Integer, nullable=False)  # References game.game_id
    added_by = Column(Integer, ForeignKey('alliance_user.user_id'), nullable=False)
    added_at = Column(TIMESTAMP, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index('ix_alliance_game', 'alliance_id', 'game_id', unique=True),
    )

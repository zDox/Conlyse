from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Account(Base):
    __tablename__ = 'account'

    account_id = Column(Integer, primary_key=True)
    email = Column(String(45))
    username = Column(String(45))
    password = Column(String(45))


class Game(Base):
    __tablename__ = 'game'

    game_id = Column(Integer, primary_key=True)
    scenario_id = Column(ForeignKey('scenario.scenario_id'), nullable=False, index=True)
    start_time = Column(TIMESTAMP)
    end_time = Column(TIMESTAMP)
    current_time = Column(TIMESTAMP)
    next_day_time = Column(TIMESTAMP)
    next_heal_time = Column(TIMESTAMP)
    open_slots = Column(Integer)

    scenario = relationship('Scenario')


class Scenario(Base):
    __tablename__ = 'scenario'

    scenario_id = Column(Integer, primary_key=True)
    map_id = Column(Integer)
    name = Column(String(45))
    speed = Column(Integer)


class GamesAccount(Base):
    __tablename__ = 'games_accounts'

    game_id = Column(ForeignKey('game.game_id'), primary_key=True, nullable=False, index=True)
    account_id = Column(ForeignKey('account.account_id'), primary_key=True, nullable=False, index=True)
    joined = Column(Boolean)
    server_uuid = Column(String(45))

    account = relationship('Account')
    game = relationship('Game')

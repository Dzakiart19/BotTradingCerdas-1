from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import os

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    spread = Column(Float)
    estimated_pl = Column(Float)
    actual_pl = Column(Float)
    exit_price = Column(Float)
    status = Column(String(20), default='OPEN')
    signal_time = Column(DateTime, default=datetime.utcnow)
    close_time = Column(DateTime)
    timeframe = Column(String(10))
    result = Column(String(10))
    
class SignalLog(Base):
    __tablename__ = 'signal_logs'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    indicators = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    accepted = Column(Boolean, default=False)
    rejection_reason = Column(String(255))

class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer, nullable=False)
    ticker = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    take_profit = Column(Float, nullable=False)
    current_price = Column(Float)
    unrealized_pl = Column(Float)
    status = Column(String(20), default='ACTIVE')
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime)

class Performance(Base):
    __tablename__ = 'performance'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow)
    total_trades = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    total_pl = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    equity = Column(Float, default=0.0)

class DatabaseManager:
    def __init__(self, db_path='data/bot.db'):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
        
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            connect_args={'check_same_thread': False},
            echo=False
        )
        
        with self.engine.connect() as conn:
            conn.execute(text('PRAGMA journal_mode=WAL'))
            conn.commit()
        
        Base.metadata.create_all(self.engine)
        
        self.Session = scoped_session(sessionmaker(bind=self.engine))
    
    def get_session(self):
        return self.Session()
    
    def close(self):
        self.Session.remove()
        self.engine.dispose()

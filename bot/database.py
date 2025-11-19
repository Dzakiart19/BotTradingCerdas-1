from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
import os

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    ticker = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    signal_source = Column(String(10), default='auto')
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
    user_id = Column(Integer, nullable=False)
    ticker = Column(String(20), nullable=False)
    signal_type = Column(String(10), nullable=False)
    signal_source = Column(String(10), default='auto')
    entry_price = Column(Float, nullable=False)
    indicators = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    accepted = Column(Boolean, default=False)
    rejection_reason = Column(String(255))

class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
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
    original_sl = Column(Float)
    sl_adjustment_count = Column(Integer, default=0)
    max_profit_reached = Column(Float, default=0.0)
    last_price_update = Column(DateTime)

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
        
        self._migrate_database()
        
        self.Session = scoped_session(sessionmaker(bind=self.engine))
    
    def _migrate_database(self):
        """Auto-migrate database schema for new columns"""
        with self.engine.connect() as conn:
            try:
                result = conn.execute(text("PRAGMA table_info(trades)"))
                columns = [row[1] for row in result]
                
                if 'signal_source' not in columns:
                    conn.execute(text("ALTER TABLE trades ADD COLUMN signal_source VARCHAR(10) DEFAULT 'auto'"))
                    conn.commit()
                    print("✅ Database migrated: Added signal_source column to trades table")
                
                if 'user_id' not in columns:
                    conn.execute(text("ALTER TABLE trades ADD COLUMN user_id INTEGER DEFAULT 0"))
                    conn.commit()
                    print("✅ Database migrated: Added user_id column to trades table")
            except Exception as e:
                print(f"⚠️ Migration check for trades table: {e}")
            
            try:
                result = conn.execute(text("PRAGMA table_info(signal_logs)"))
                columns = [row[1] for row in result]
                
                if 'signal_source' not in columns:
                    conn.execute(text("ALTER TABLE signal_logs ADD COLUMN signal_source VARCHAR(10) DEFAULT 'auto'"))
                    conn.commit()
                    print("✅ Database migrated: Added signal_source column to signal_logs table")
                
                if 'user_id' not in columns:
                    conn.execute(text("ALTER TABLE signal_logs ADD COLUMN user_id INTEGER DEFAULT 0"))
                    conn.commit()
                    print("✅ Database migrated: Added user_id column to signal_logs table")
            except Exception as e:
                print(f"⚠️ Migration check for signal_logs table: {e}")
            
            try:
                result = conn.execute(text("PRAGMA table_info(positions)"))
                columns = [row[1] for row in result]
                
                if 'user_id' not in columns:
                    conn.execute(text("ALTER TABLE positions ADD COLUMN user_id INTEGER DEFAULT 0"))
                    conn.commit()
                    print("✅ Database migrated: Added user_id column to positions table")
                
                if 'original_sl' not in columns:
                    conn.execute(text("ALTER TABLE positions ADD COLUMN original_sl REAL"))
                    conn.commit()
                    conn.execute(text("UPDATE positions SET original_sl = stop_loss WHERE original_sl IS NULL"))
                    conn.commit()
                    print("✅ Database migrated: Added original_sl column to positions table and backfilled existing data")
                
                if 'sl_adjustment_count' not in columns:
                    conn.execute(text("ALTER TABLE positions ADD COLUMN sl_adjustment_count INTEGER DEFAULT 0"))
                    conn.commit()
                    conn.execute(text("UPDATE positions SET sl_adjustment_count = 0 WHERE sl_adjustment_count IS NULL"))
                    conn.commit()
                    print("✅ Database migrated: Added sl_adjustment_count column to positions table")
                
                if 'max_profit_reached' not in columns:
                    conn.execute(text("ALTER TABLE positions ADD COLUMN max_profit_reached REAL DEFAULT 0.0"))
                    conn.commit()
                    conn.execute(text("UPDATE positions SET max_profit_reached = 0.0 WHERE max_profit_reached IS NULL"))
                    conn.commit()
                    print("✅ Database migrated: Added max_profit_reached column to positions table")
                
                if 'last_price_update' not in columns:
                    conn.execute(text("ALTER TABLE positions ADD COLUMN last_price_update TIMESTAMP"))
                    conn.commit()
                    conn.execute(text("UPDATE positions SET last_price_update = datetime('now') WHERE last_price_update IS NULL"))
                    conn.commit()
                    print("✅ Database migrated: Added last_price_update column to positions table")
            except Exception as e:
                print(f"⚠️ Migration check for positions table: {e}")
    
    def get_session(self):
        return self.Session()
    
    def close(self):
        self.Session.remove()
        self.engine.dispose()

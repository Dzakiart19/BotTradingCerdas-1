import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(name='TradingBot', log_dir='logs', level=None):
    os.makedirs(log_dir, exist_ok=True)
    
    if level is None:
        log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        level = level_map.get(log_level_str, logging.INFO)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, f'{name.lower()}.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(log_format)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(log_format)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

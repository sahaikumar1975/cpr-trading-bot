"""Configuration Management"""
import os
import pytz
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'Sahai@2025')
    
    FYERS_APP_ID = os.getenv('FYERS_APP_ID', '')
    FYERS_ACCESS_TOKEN = os.getenv('FYERS_ACCESS_TOKEN', '')
    
    CAPITAL = float(os.getenv('CAPITAL', '100000'))
    MAX_RISK_PER_TRADE = float(os.getenv('MAX_RISK_PER_TRADE', '2.0'))
    MAX_DAILY_LOSS = float(os.getenv('MAX_DAILY_LOSS', '5.0'))
    MAX_TRADES_PER_DAY = int(os.getenv('MAX_TRADES_PER_DAY', '4'))
    
    SL_MULTIPLIER = float(os.getenv('SL_MULTIPLIER', '1.5'))
    TP_MULTIPLIER = float(os.getenv('TP_MULTIPLIER', '3.0'))
    
    USE_TRAILING_SL = os.getenv('USE_TRAILING_SL', 'True').lower() == 'true'
    TSL_ACTIVATION = float(os.getenv('TSL_ACTIVATION', '1.5'))
    TSL_OFFSET = float(os.getenv('TSL_OFFSET', '1.0'))
    
    LOT_SIZE_NIFTY = int(os.getenv('LOT_SIZE_NIFTY', '50'))
    LOT_SIZE_BANKNIFTY = int(os.getenv('LOT_SIZE_BANKNIFTY', '15'))
    LOT_SIZE_FINNIFTY = int(os.getenv('LOT_SIZE_FINNIFTY', '40'))
    LOT_SIZE_SENSEX = int(os.getenv('LOT_SIZE_SENSEX', '10'))
    
    STRIKE_SELECTION = os.getenv('STRIKE_SELECTION', 'ATM')
    
    PAPER_TRADING = os.getenv('PAPER_TRADING', 'True').lower() == 'true'
    
    IST = pytz.timezone('Asia/Kolkata')
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        if not cls.WEBHOOK_SECRET:
            errors.append("WEBHOOK_SECRET required")
        if not cls.PAPER_TRADING and not cls.FYERS_APP_ID:
            errors.append("FYERS_APP_ID required for live trading")
        if cls.CAPITAL <= 0:
            errors.append("CAPITAL must be positive")
        if errors:
            raise ValueError(f"Config errors: {', '.join(errors)}")
    
    @classmethod
    def display(cls):
        """Display configuration"""
        print("=" * 50)
        print("CONFIGURATION")
        print("=" * 50)
        print(f"Paper Trading: {cls.PAPER_TRADING}")
        print(f"Capital: ₹{cls.CAPITAL:,.2f}")
        print(f"Max Risk/Trade: {cls.MAX_RISK_PER_TRADE}%")
        print(f"Max Trades/Day: {cls.MAX_TRADES_PER_DAY}")
        print(f"Strike: {cls.STRIKE_SELECTION}")
        print("=" * 50)
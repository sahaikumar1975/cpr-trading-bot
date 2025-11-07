# Setup Guide

## Quick Start

### 1. Install Python
Download Python 3.9+ from python.org

### 2. Clone Repository
```bash
git clone https://github.com/yourusername/cpr-trading-bot.git
cd cpr-trading-bot
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure
```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Generate Fyers Token
```bash
python generate_token.py
```

### 6. Test Locally
```bash
python app.py
```

### 7. Deploy to Render.com
1. Push to GitHub
2. Connect to Render.com
3. Add environment variables
4. Deploy

### 8. Connect TradingView
1. Add Pine Script to chart
2. Create alert with webhook URL
3. Start paper trading

## Detailed Instructions

See main README.md for complete setup guide.
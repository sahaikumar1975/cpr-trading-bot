"""
CPR + Supertrend + RSI Trading Bot - Main Application
Webhook server for automated options trading via Fyers
"""

from flask import Flask, request, jsonify, render_template_string
import os
import json
import logging
from datetime import datetime
from config import Config
from utils.position_manager import PositionManager
from utils.risk_manager import RiskManager
from utils.logger import setup_logger
from fyers_auth import FyersClient

# Setup
app = Flask(__name__)
config = Config()
logger = setup_logger()

# Initialize components
position_manager = PositionManager()
risk_manager = RiskManager(config)
fyers_client = FyersClient(config) if not config.PAPER_TRADING else None

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_expiry_date(instrument):
    """Calculate next weekly expiry (Thursday)"""
    from datetime import timedelta
    now = datetime.now(config.IST)
    days_ahead = 3 - now.weekday()  # Thursday = 3
    if days_ahead <= 0:
        days_ahead += 7
    expiry = now + timedelta(days=days_ahead)
    return expiry.strftime('%y%m%d')

def construct_symbol(instrument, strike, option_type, expiry):
    """Construct Fyers symbol format"""
    month_map = {
        '01': 'JAN', '02': 'FEB', '03': 'MAR', '04': 'APR',
        '05': 'MAY', '06': 'JUN', '07': 'JUL', '08': 'AUG',
        '09': 'SEP', '10': 'OCT', '11': 'NOV', '12': 'DEC'
    }
    
    year = expiry[:2]
    month = month_map[expiry[2:4]]
    day = expiry[4:6]
    
    # Clean instrument name
    clean_inst = instrument.replace("NSE:", "").upper()
    if "NIFTY" in clean_inst and "BANK" not in clean_inst and "FIN" not in clean_inst:
        clean_inst = "NIFTY"
    
    return f"NSE:{clean_inst}{day}{month}{year}{int(strike)}{option_type}"

def calculate_strike(entry_price, instrument, option_type):
    """Calculate ATM/ITM/OTM strike based on config"""
    intervals = {
        'NIFTY': 50,
        'BANKNIFTY': 100,
        'FINNIFTY': 50,
        'SENSEX': 100
    }
    
    interval = intervals.get(instrument, 50)
    atm_strike = round(entry_price / interval) * interval
    
    # Adjust based on selection
    strike_map = {
        'ATM': 0,
        'ITM1': -1 if option_type == 'CE' else 1,
        'ITM2': -2 if option_type == 'CE' else 2,
        'OTM1': 1 if option_type == 'CE' else -1,
        'OTM2': 2 if option_type == 'CE' else -2
    }
    
    offset = strike_map.get(config.STRIKE_SELECTION, 0)
    final_strike = atm_strike + (offset * interval)
    
    return int(final_strike)

def get_lot_size(instrument):
    """Get lot size for instrument"""
    lot_sizes = {
        'NIFTY': config.LOT_SIZE_NIFTY,
        'BANKNIFTY': config.LOT_SIZE_BANKNIFTY,
        'FINNIFTY': config.LOT_SIZE_FINNIFTY,
        'SENSEX': config.LOT_SIZE_SENSEX
    }
    return lot_sizes.get(instrument.upper(), 50)

# ==========================================
# ROUTES
# ==========================================

@app.route('/')
def home():
    """Health check endpoint"""
    stats = position_manager.get_today_stats()
    
    return jsonify({
        "status": "active",
        "service": "CPR Trading Bot",
        "strategy": "CPR + Supertrend + RSI",
        "version": "1.0.0",
        "broker": "FYERS",
        "paper_trading": config.PAPER_TRADING,
        "timestamp": datetime.now(config.IST).isoformat(),
        "today_stats": {
            "trades": stats['total_trades'],
            "pnl": stats['total_pnl'],
            "win_rate": stats.get('win_rate', 0)
        }
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Main webhook endpoint for TradingView alerts
    
    Expected JSON:
    {
        "secret": "your_secret",
        "instrument": "NIFTY",
        "action": "BUY_CALL" or "BUY_PUT",
        "strike": 0 (auto-calculate),
        "entry_price": 21500.50,
        "atr": 120.30
    }
    """
    try:
        data = request.json
        logger.info(f"📥 Webhook received: {json.dumps(data, indent=2)}")
        
        # Security check
        if data.get('secret') != config.WEBHOOK_SECRET:
            logger.warning("⚠️ Unauthorized webhook attempt")
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Check daily limits
        can_trade, message = risk_manager.can_trade(position_manager.get_today_stats())
        if not can_trade:
            logger.warning(f"⚠️ Trade blocked: {message}")
            return jsonify({"status": "blocked", "message": message}), 429
        
        # Extract data
        instrument = data.get('instrument', '').upper()
        action = data.get('action', '').upper()
        entry_price = float(data.get('entry_price', 0))
        atr = float(data.get('atr', 0))
        strike_input = float(data.get('strike', 0))
        
        # Validate
        if not all([instrument, action, entry_price, atr]):
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        # Determine option type
        if action == "BUY_CALL":
            option_type = "CE"
        elif action == "BUY_PUT":
            option_type = "PE"
        else:
            return jsonify({"status": "error", "message": "Invalid action"}), 400
        
        # Calculate strike
        if strike_input == 0:
            strike = calculate_strike(entry_price, instrument, option_type)
        else:
            strike = strike_input
        
        # Get details
        expiry = get_expiry_date(instrument)
        symbol = construct_symbol(instrument, strike, option_type, expiry)
        quantity = get_lot_size(instrument)
        
        # Calculate SL and TP
        if option_type == "CE":
            stop_loss = entry_price - (atr * config.SL_MULTIPLIER)
            take_profit = entry_price + (atr * config.TP_MULTIPLIER)
        else:  # PE
            stop_loss = entry_price + (atr * config.SL_MULTIPLIER)
            take_profit = entry_price - (atr * config.TP_MULTIPLIER)
        
        # Risk calculation
        risk_per_contract = atr * config.SL_MULTIPLIER * quantity
        position_risk = risk_per_contract
        
        # Check risk limits
        if not risk_manager.check_position_risk(position_risk):
            return jsonify({
                "status": "blocked",
                "message": f"Position risk ₹{position_risk:.2f} exceeds limit"
            }), 429
        
        # Create position ID
        timestamp = datetime.now(config.IST).strftime('%H%M%S')
        position_id = f"CPR_{instrument}_{strike}{option_type}_{timestamp}"
        
        # Trade details
        trade_details = {
            "position_id": position_id,
            "strategy": "CPR",
            "instrument": instrument,
            "symbol": symbol,
            "action": action,
            "option_type": option_type,
            "strike": strike,
            "entry_price": entry_price,
            "quantity": quantity,
            "stop_loss": round(stop_loss, 2),
            "take_profit": round(take_profit, 2),
            "atr": atr,
            "expiry": expiry,
            "risk": round(position_risk, 2)
        }
        
        logger.info(f"📊 Trade Details:\n{json.dumps(trade_details, indent=2)}")
        
        # Paper trading mode
        if config.PAPER_TRADING:
            position_manager.add_position(position_id, trade_details)
            logger.info("📝 PAPER TRADING - No actual order placed")
            
            return jsonify({
                "status": "success",
                "mode": "paper_trading",
                "trade": trade_details
            })
        
        # Live trading - Place order via Fyers
        if fyers_client:
            order_result = fyers_client.place_order(
                symbol=symbol,
                quantity=quantity,
                side=1,  # Buy
                order_type="MARKET"
            )
            
            if order_result['success']:
                trade_details['order_id'] = order_result['order_id']
                position_manager.add_position(position_id, trade_details)
                
                logger.info(f"✅ Order placed: {order_result['order_id']}")
                
                return jsonify({
                    "status": "success",
                    "mode": "live_trading",
                    "order_id": order_result['order_id'],
                    "trade": trade_details
                })
            else:
                logger.error(f"❌ Order failed: {order_result['error']}")
                return jsonify({
                    "status": "error",
                    "message": order_result['error']
                }), 500
        else:
            return jsonify({
                "status": "error",
                "message": "Fyers client not initialized"
            }), 500
    
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/positions', methods=['GET'])
def get_positions():
    """Get all open positions"""
    positions = position_manager.get_open_positions()
    return jsonify({
        "status": "success",
        "count": len(positions),
        "positions": positions
    })

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get today's statistics"""
    stats = position_manager.get_today_stats()
    return jsonify({
        "status": "success",
        "stats": stats
    })

@app.route('/trades', methods=['GET'])
def get_trades():
    """Get trade log"""
    trades = position_manager.get_trade_log()
    return jsonify({
        "status": "success",
        "count": len(trades),
        "trades": trades
    })

@app.route('/close/<position_id>', methods=['POST'])
def close_position(position_id):
    """Manually close a position"""
    position = position_manager.get_position(position_id)
    
    if not position:
        return jsonify({"status": "error", "message": "Position not found"}), 404
    
    if position['status'] == 'CLOSED':
        return jsonify({"status": "error", "message": "Position already closed"}), 400
    
    # Get current price (mock for paper trading)
    exit_price = position['entry_price'] * 1.05  # Mock 5% profit
    
    # Close position
    pnl = position_manager.close_position(position_id, exit_price)
    
    logger.info(f"💰 Position closed manually: {position_id} | P&L: ₹{pnl:.2f}")
    
    return jsonify({
        "status": "success",
        "message": "Position closed",
        "pnl": pnl
    })

@app.route('/dashboard')
def dashboard():
    """Simple HTML dashboard"""
    stats = position_manager.get_today_stats()
    positions = position_manager.get_open_positions()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CPR Trading Bot Dashboard</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body { font-family: Arial; background: #1a1a1a; color: #fff; padding: 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .card { background: #2a2a2a; padding: 20px; margin: 10px 0; border-radius: 10px; }
            .metric { display: inline-block; margin: 10px 20px; }
            .value { font-size: 32px; font-weight: bold; }
            .label { font-size: 14px; color: #888; }
            .positive { color: #4CAF50; }
            .negative { color: #f44336; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #444; }
            th { background: #333; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 CPR Trading Bot</h1>
            <p>CPR + Supertrend + RSI Strategy</p>
        </div>
        
        <div class="card">
            <h2>Today's Performance</h2>
            <div class="metric">
                <div class="value %(pnl_class)s">₹%(pnl).2f</div>
                <div class="label">P&L</div>
            </div>
            <div class="metric">
                <div class="value">%(trades)d</div>
                <div class="label">Trades</div>
            </div>
            <div class="metric">
                <div class="value %(wr_class)s">%(win_rate).1f%%</div>
                <div class="label">Win Rate</div>
            </div>
            <div class="metric">
                <div class="value">%(pf).2f</div>
                <div class="label">Profit Factor</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Open Positions: %(open_count)d</h2>
            %(positions_html)s
        </div>
        
        <p style="text-align: center; color: #888; margin-top: 30px;">
            Auto-refreshes every 30 seconds | %(mode)s
        </p>
    </body>
    </html>
    """
    
    # Build positions table
    if positions:
        pos_html = "<table><tr><th>Symbol</th><th>Entry</th><th>SL</th><th>TP</th></tr>"
        for pos_id, pos in positions.items():
            pos_html += f"<tr><td>{pos['symbol']}</td><td>₹{pos['entry_price']}</td><td>₹{pos['stop_loss']}</td><td>₹{pos['take_profit']}</td></tr>"
        pos_html += "</table>"
    else:
        pos_html = "<p>No open positions</p>"
    
    pnl_class = "positive" if stats['total_pnl'] >= 0 else "negative"
    wr_class = "positive" if stats.get('win_rate', 0) >= 60 else "negative"
    
    html = html % {
        'pnl': stats['total_pnl'],
        'pnl_class': pnl_class,
        'trades': stats['total_trades'],
        'win_rate': stats.get('win_rate', 0),
        'wr_class': wr_class,
        'pf': stats.get('profit_factor', 0),
        'open_count': len(positions),
        'positions_html': pos_html,
        'mode': 'PAPER TRADING' if config.PAPER_TRADING else 'LIVE TRADING'
    }
    
    return render_template_string(html)

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}", exc_info=True)
    return jsonify({"status": "error", "message": "Internal server error"}), 500

# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("🚀 CPR Trading Bot Starting...")
    logger.info(f"📊 Mode: {'PAPER TRADING' if config.PAPER_TRADING else 'LIVE TRADING'}")
    logger.info(f"🏦 Broker: Fyers")
    logger.info(f"💰 Capital: ₹{config.CAPITAL:,.2f}")
    logger.info(f"📈 Max Risk/Trade: {config.MAX_RISK_PER_TRADE}%")
    
    app.run(host='0.0.0.0', port=port, debug=False)
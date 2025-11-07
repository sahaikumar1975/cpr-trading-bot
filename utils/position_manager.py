"""Position Manager - Tracks positions and P&L"""
from datetime import datetime
from collections import defaultdict
import pytz

IST = pytz.timezone('Asia/Kolkata')

class PositionManager:
    """Manage trading positions"""
    
    def __init__(self):
        self.positions = {}
        self.daily_stats = defaultdict(lambda: {
            'total_trades': 0, 'closed_trades': 0,
            'winners': 0, 'losers': 0,
            'total_pnl': 0.0, 'gross_profit': 0.0, 'gross_loss': 0.0,
            'consecutive_wins': 0, 'consecutive_losses': 0
        })
        self.trade_log = []
    
    def add_position(self, position_id, details):
        """Add new position"""
        self.positions[position_id] = {
            **details,
            'entry_time': datetime.now(IST).isoformat(),
            'status': 'OPEN'
        }
        today = datetime.now(IST).date().isoformat()
        self.daily_stats[today]['total_trades'] += 1
        return position_id
    
    def close_position(self, position_id, exit_price):
        """Close position and calculate P&L"""
        if position_id not in self.positions:
            return None
        
        pos = self.positions[position_id]
        if pos['status'] == 'CLOSED':
            return None
        
        pos['status'] = 'CLOSED'
        pos['exit_price'] = exit_price
        pos['exit_time'] = datetime.now(IST).isoformat()
        
        pnl = (exit_price - pos['entry_price']) * pos['quantity']
        pos['pnl'] = pnl
        
        today = datetime.now(IST).date().isoformat()
        stats = self.daily_stats[today]
        stats['closed_trades'] += 1
        stats['total_pnl'] += pnl
        
        if pnl > 0:
            stats['winners'] += 1
            stats['gross_profit'] += pnl
            stats['consecutive_wins'] += 1
            stats['consecutive_losses'] = 0
        else:
            stats['losers'] += 1
            stats['gross_loss'] += abs(pnl)
            stats['consecutive_losses'] += 1
            stats['consecutive_wins'] = 0
        
        self.trade_log.append({
            'position_id': position_id,
            'symbol': pos['symbol'],
            'entry': pos['entry_price'],
            'exit': exit_price,
            'pnl': pnl
        })
        
        return pnl
    
    def get_open_positions(self):
        """Get all open positions"""
        return {k: v for k, v in self.positions.items() if v['status'] == 'OPEN'}
    
    def get_today_stats(self):
        """Get today's statistics"""
        today = datetime.now(IST).date().isoformat()
        stats = self.daily_stats[today]
        
        if stats['closed_trades'] > 0:
            stats['win_rate'] = (stats['winners'] / stats['closed_trades']) * 100
            stats['profit_factor'] = (
                stats['gross_profit'] / stats['gross_loss']
                if stats['gross_loss'] > 0 else float('inf')
            )
        else:
            stats['win_rate'] = 0
            stats['profit_factor'] = 0
        
        return stats
    
    def get_trade_log(self):
        """Get trade log"""
        return self.trade_log
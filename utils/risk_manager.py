"""Risk Manager - Enforces risk rules"""

class RiskManager:
    """Risk management and limits"""
    
    def __init__(self, config):
        self.config = config
    
    def can_trade(self, stats):
        """Check if trading allowed"""
        
        if stats['total_trades'] >= self.config.MAX_TRADES_PER_DAY:
            return False, f"Daily limit reached ({self.config.MAX_TRADES_PER_DAY})"
        
        loss_pct = (stats['total_pnl'] / self.config.CAPITAL) * 100
        if stats['total_pnl'] < 0 and abs(loss_pct) >= self.config.MAX_DAILY_LOSS:
            return False, f"Daily loss limit reached ({loss_pct:.2f}%)"
        
        if stats['consecutive_losses'] >= 3:
            return False, "3 consecutive losses. Take a break."
        
        return True, "OK"
    
    def check_position_risk(self, position_risk):
        """Check position risk"""
        max_risk = (self.config.CAPITAL * self.config.MAX_RISK_PER_TRADE) / 100
        return position_risk <= max_risk
    
    def calculate_position_size(self, risk_per_contract):
        """Calculate position size"""
        max_risk = (self.config.CAPITAL * self.config.MAX_RISK_PER_TRADE) / 100
        max_lots = int(max_risk / risk_per_contract)
        return max(1, max_lots) if risk_per_contract <= max_risk else 0
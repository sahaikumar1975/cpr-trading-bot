"""Fyers API Client"""
import logging

logger = logging.getLogger(__name__)

class FyersClient:
    """Fyers API wrapper"""
    
    def __init__(self, config):
        self.config = config
        self.fyers = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Fyers"""
        try:
            from fyers_apiv3 import fyersModel
            
            self.fyers = fyersModel.FyersModel(
                client_id=self.config.FYERS_APP_ID,
                token=self.config.FYERS_ACCESS_TOKEN,
                log_path=""
            )
            
            profile = self.fyers.get_profile()
            if profile['s'] == 'ok':
                logger.info(f"✅ Fyers: {profile['data']['name']}")
                return True
            else:
                logger.error(f"❌ Fyers failed: {profile.get('message')}")
                return False
        except Exception as e:
            logger.error(f"❌ Fyers error: {e}")
            return False
    
    def place_order(self, symbol, quantity, side, order_type="MARKET"):
        """Place order"""
        try:
            data = {
                "symbol": symbol,
                "qty": quantity,
                "type": 2 if order_type == "MARKET" else 1,
                "side": side,
                "productType": "INTRADAY",
                "limitPrice": 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": False
            }
            
            response = self.fyers.place_order(data)
            
            if response['s'] == 'ok':
                logger.info(f"✅ Order: {response['id']}")
                return {"success": True, "order_id": response['id']}
            else:
                logger.error(f"❌ Order failed: {response.get('message')}")
                return {"success": False, "error": response.get('message')}
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return {"success": False, "error": str(e)}
    
    def get_positions(self):
        """Get positions"""
        try:
            response = self.fyers.positions()
            if response['s'] == 'ok':
                return response['netPositions']
            return []
        except Exception as e:
            logger.error(f"Error: {e}")
            return []
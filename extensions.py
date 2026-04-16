"""
Flask extensions initialization
Initialize extensions here and use them in the app
"""
from flask_mail import Mail
from flask_caching import Cache
from flask import current_app
import googlemaps

# Initialize extensions
mail = Mail()
cache = Cache()

def get_gmaps_client():
    """Get Google Maps client with API key from config"""
    api_key = current_app.config.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        current_app.logger.warning("GOOGLE_MAPS_API_KEY not configured")
        return None
    try:
        return googlemaps.Client(key=api_key)
    except Exception as e:
        current_app.logger.error(f"Failed to initialize Google Maps client: {e}")
        return None

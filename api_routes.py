"""
API Routes
Public and internal API endpoints
"""
import logging
import requests
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')


import requests
@api_bp.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'environment': current_app.config.get('ENV', 'unknown')
    }), 200


@api_bp.route('/status', methods=['GET'])
def status():
    """System status"""
    from database import db
    from models import Driver, Order, Delivery, Customer
    
    try:
        stats = {
            'drivers': Driver.query.count(),
            'active_drivers': Driver.query.filter_by(is_online=True).count(),
            'customers': Customer.query.count(),
            'orders': Order.query.count(),
            'deliveries': Delivery.query.count(),
            'completed_deliveries': Delivery.query.filter_by(status='Delivered').count(),
            'active_deliveries': Delivery.query.filter_by(status='In Transit').count(),
        }
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route('/config', methods=['GET'])
def get_config():
    """Get public configuration"""
    return jsonify({
        'routing_service_url': current_app.config.get('ROUTING_SERVICE_URL'),
        'default_base_fare': current_app.config.get('DEFAULT_BASE_FARE'),
        'default_per_km_rate': current_app.config.get('DEFAULT_PER_KM_RATE'),
    }), 200


@api_bp.route('/geocode', methods=['GET', 'POST'])
def geocode():
    """OpenStreetMap geocoding proxy - Accept both GET query params and POST JSON"""
    if request.method == 'GET':
        q = request.args.get('q') or request.args.get('address') or ''
        limit = request.args.get('limit', 5)
        countrycodes = request.args.get('countrycodes', '')
    else:
        data = request.get_json(silent=True) or {}
        q = data.get('q') or data.get('address') or ''
        limit = data.get('limit', 5)
        countrycodes = data.get('countrycodes', '')

    if not q:
        return jsonify([]), 200

    params = {
        'format': 'json',
        'q': q,
        'limit': limit
    }
    if countrycodes:
        params['countrycodes'] = countrycodes

    headers = {
        'User-Agent': current_app.config.get('GEOCODER_USER_AGENT', 'DeliverySystem/1.0 (dev@localhost)'),
        'Accept': 'application/json'
    }

    try:
        resp = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        results = resp.json()
        return jsonify(results), 200
    except Exception as e:
        logger.exception('Geocoding proxy error: %s', e)
        return jsonify({'error': 'geocoding_failed'}), 500

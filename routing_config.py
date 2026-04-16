# routing_config.py - Configuration for routing services
import os
from enum import Enum

class RoutingMode(Enum):
    LIGHTWEIGHT = "lightweight"  # Fast startup, simple routing
    FULL = "full"               # Complete routing with GraphML
    HYBRID = "hybrid"            # Start lightweight, load full on demand
    OPTIMIZED = "optimized"      # High-performance with aggressive caching

class RoutingConfig:
    def __init__(self):
        # Environment-based configuration
        self.mode = RoutingMode(os.environ.get("ROUTING_MODE", "optimized"))
        self.port = int(os.environ.get("ROUTING_PORT", 8011))  # Changed from 8010 to 8011
        self.host = os.environ.get("ROUTING_HOST", "0.0.0.0")
        
        # Performance settings (optimized for high-performance caching)
        self.cache_ttl = int(os.environ.get("ROUTE_CACHE_TTL", 3600))  # 1 hour (increased)
        self.cache_max = int(os.environ.get("ROUTE_CACHE_MAX", 5000))   # 5000 entries (doubled)
        self.location_retention = int(os.environ.get("LOCATION_RETENTION", 7200))  # 2 hours
        
        # Feature flags
        self.enable_websockets = os.environ.get("ENABLE_WEBSOCKETS", "true").lower() == "true"
        self.enable_simple_routing = os.environ.get("ENABLE_SIMPLE_ROUTING", "true").lower() == "true"
        self.enable_lazy_loading = os.environ.get("ENABLE_LAZY_LOADING", "true").lower() == "true"
        
        # Routing precision
        self.coord_decimals = int(os.environ.get("COORD_DECIMALS", 7))
        
    @property
    def is_lightweight(self):
        return self.mode in [RoutingMode.LIGHTWEIGHT, RoutingMode.HYBRID]
    
    @property
    def is_full(self):
        return self.mode == RoutingMode.FULL
    
    def get_service_file(self):
        if self.mode == RoutingMode.LIGHTWEIGHT:
            return "routing_service_lite.py"
        elif self.mode == RoutingMode.FULL:
            return "routing_service.py"
        elif self.mode == RoutingMode.OPTIMIZED:
            return "routing_service_optimized.py"
        else:  # HYBRID
            return "routing_service_lite.py"  # Start with lite, can upgrade
    
    def get_startup_message(self):
        return f"""
Routing Configuration:
- Mode: {self.mode.value}
- Service: {self.get_service_file()}
- Port: {self.port}
- Cache TTL: {self.cache_ttl}s
- Cache Max: {self.cache_max} entries
- Simple Routing: {self.enable_simple_routing}
- WebSockets: {self.enable_websockets}
- Lazy Loading: {self.enable_lazy_loading}
        """

# Global config instance
config = RoutingConfig()

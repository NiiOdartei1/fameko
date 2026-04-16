#!/usr/bin/env python3
# Create a more realistic curved route between two points
import math

def create_curved_route(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng, num_points=20):
    """
    Create a curved route that looks more realistic than a straight line
    by adding intermediate points that follow a gentle arc
    """
    
    # Calculate distance and bearing
    lat_diff = dropoff_lat - pickup_lat
    lng_diff = dropoff_lng - pickup_lng
    
    # Create intermediate points along a curved path
    route_coords = []
    
    for i in range(num_points + 1):
        t = i / num_points  # 0 to 1
        
        # Basic linear interpolation
        lat = pickup_lat + lat_diff * t
        lng = pickup_lng + lng_diff * t
        
        # Add a gentle curve (arc)
        # Maximum curve offset at the midpoint
        curve_factor = math.sin(t * math.pi) * 0.02  # Adjust 0.02 for more/less curve
        
        # Perpendicular offset (creates the curve)
        # Calculate perpendicular direction
        perp_lat = -lng_diff
        perp_lng = lat_diff
        
        # Normalize and apply curve
        length = math.sqrt(perp_lat**2 + perp_lng**2)
        if length > 0:
            perp_lat = perp_lat / length * curve_factor
            perp_lng = perp_lng / length * curve_factor
            
            lat += perp_lat
            lng += perp_lng
        
        route_coords.append([lng, lat])
    
    return route_coords

def test_curved_route():
    # Test with Accra coordinates
    pickup_lat, pickup_lng = 5.6037, -0.1870  # Central Accra
    dropoff_lat, dropoff_lng = 5.703291, -0.2990647  # Amasaman
    
    route = create_curved_route(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
    
    print(f"Generated route with {len(route)} points:")
    print(f"Start: {route[0]}")
    print(f"Mid: {route[len(route)//2]}")
    print(f"End: {route[-1]}")
    
    return route

if __name__ == "__main__":
    test_curved_route()

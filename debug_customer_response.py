import requests
import json

# Simulate a customer placing an order in the Northern region
print("Testing customer route calculation end-to-end:")
print("=" * 60)

# Test 1: With explicit region
print("\n1. Testing WITH region parameter (Northern):")
response = requests.post('http://localhost:5000/route', json={
    'pickup_lat': 10.5,
    'pickup_lng': 1.0,
    'dropoff_lat': 10.7,
    'dropoff_lng': 1.2,
    'driver_region': 'Northern'
}, timeout=10)

if response.status_code == 200:
    data = response.json()
    print(f"   Waypoints received: {len(data.get('waypoints', []))} points")
    print(f"   Coordinates received: {len(data.get('coordinates', []))} points")
    print(f"   Distance: {data.get('distance_km')} km")
    print(f"   Duration: {data.get('duration_minutes')} min")
    
    if len(data.get('waypoints', [])) > 0:
        print(f"   First waypoint: {data['waypoints'][0]} (format: [lat, lng])")
        print(f"   Last waypoint: {data['waypoints'][-1]} (format: [lat, lng])")
    
    if len(data.get('coordinates', [])) > 0:
        print(f"   First coordinate: {data['coordinates'][0]} (format: [lng, lat])")
        print(f"   Last coordinate: {data['coordinates'][-1]} (format: [lng, lat])")
else:
    print(f"   Error: {response.status_code}")
    print(f"   {response.text[:200]}")

# Test 2: Without explicit region (auto-detect)
print("\n2. Testing WITHOUT region parameter (should auto-detect):")
response2 = requests.post('http://localhost:5000/route', json={
    'pickup_lat': 10.5,
    'pickup_lng': 1.0,
    'dropoff_lat': 10.7,
    'dropoff_lng': 1.2
}, timeout=10)

if response2.status_code == 200:
    data2 = response2.json()
    print(f"   Waypoints received: {len(data2.get('waypoints', []))} points")
    print(f"   Distance: {data2.get('distance_km')} km")
    print(f"   Route calculated: {'Yes' if len(data2.get('waypoints', [])) > 0 else 'No'}")
else:
    print(f"   Error: {response2.status_code}")

print("\n" + "=" * 60)
print("If waypoints > 20, route follows real roads")
print("If waypoints ~5-10, route is interpolated/curved")

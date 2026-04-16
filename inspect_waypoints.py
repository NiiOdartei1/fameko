import requests

response = requests.post('http://localhost:5000/route', json={
    'pickup_lat': 9.4,
    'pickup_lng': -0.85,
    'dropoff_lat': 9.6,
    'dropoff_lng': -0.65,
})

data = response.json()
waypoints = data.get('waypoints', [])
coords = data.get('coordinates', [])

print(f"Waypoints: {len(waypoints)}")
print(f"Coordinates: {len(coords)}")
print(f"\nFirst 10 waypoints (lat, lng):")
for i, w in enumerate(waypoints[:10]):
    print(f"  {i+1}. {w}")

print(f"\n... ({len(waypoints)-20} more) ...")

print(f"\nLast 10 waypoints (lat, lng):")
for i, w in enumerate(waypoints[-10:]):
    print(f"  {len(waypoints)-9+i}. {w}")

# Check if waypoints actually form a path
if len(coords) > 1:
    # Sample some distances
    samples = [0, len(coords)//4, len(coords)//2, 3*len(coords)//4, len(coords)-1]
    print(f"\nSample distances between waypoints:")
    for i in range(len(samples)-1):
        idx1, idx2 = samples[i], samples[i+1]
        lat1, lng1 = coords[idx1][1], coords[idx1][0]
        lat2, lng2 = coords[idx2][1], coords[idx2][0]
        dist = ((lat2-lat1)**2 + (lng2-lng1)**2)**0.5 * 111  # Approximate km
        print(f"  Point {idx1} to {idx2}: {dist:.2f} km apart")

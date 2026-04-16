package main

import (
	"container/heap"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"log"
	"math"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"sync"
	"time"

	"github.com/gorilla/mux"
	"github.com/gorilla/websocket"
)

// GraphML structures
type GraphML struct {
	Graph GraphElement `xml:"graph"`
}

type GraphElement struct {
	Nodes []Node `xml:"node"`
	Edges []Edge `xml:"edge"`
}

type Node struct {
	ID    string `xml:"id,attr"`
	Data  []Data `xml:"data"`
	Y     float64
	X     float64
}

type Edge struct {
	Source string `xml:"source,attr"`
	Target string `xml:"target,attr"`
	Data   []Data `xml:"data"`
	Length float64
}

type Data struct {
	Key   string `xml:"key,attr"`
	Value string `xml:",chardata"`
}

// Graph representation
type Graph struct {
	Nodes map[string]*GraphNode
	Edges map[string][]*GraphEdge
}

type GraphNode struct {
	ID  string
	Lat float64
	Lng float64
}

type GraphEdge struct {
	Target string
	Length float64
}

// Request/Response structures
type RouteRequest struct {
	PickupLat    float64 `json:"pickup_lat"`
	PickupLng    float64 `json:"pickup_lng"`
	DropoffLat   float64 `json:"dropoff_lat"`
	DropoffLng   float64 `json:"dropoff_lng"`
	DriverRegion string  `json:"driver_region"`
	Alternatives int     `json:"alternatives"`
	VehicleType  string  `json:"vehicle_type,omitempty"`
	RouteType    string  `json:"route_type,omitempty"`
}

type RouteResponse struct {
	Primary Route `json:"primary"`
}

type Route struct {
	Coordinates    [][]float64 `json:"coordinates"`
	DistanceKm     float64     `json:"distance_km"`
	DistanceM      float64     `json:"distance_m"`
	DurationSeconds int         `json:"duration_seconds"`
	DurationMinutes int         `json:"duration_minutes"`
}

// Global state
var (
	graphs   = make(map[string]*Graph)
	graphsMu sync.RWMutex
	cache    = make(map[string]RouteResponse)
	cacheMu  sync.RWMutex
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			return true // Allow all origins for development
		},
	}
)

func init() {
	// Preload all region graphs
	regions := []string{
		"Northern", "North_East", "Upper_West", "Upper_East",
		"Savannah", "Oti", "Bono_East", "Bono", "Ahafo",
		"Ashanti", "Central", "Eastern", "Greater_Accra",
		"Volta", "Western_North", "Western",
	}

	for _, region := range regions {
		path := filepath.Join("data", region+"_Region_Ghana.graphml")
		if _, err := os.Stat(path); err == nil {
			log.Printf("Preloading %s...", region)
			g, err := loadGraphML(path)
			if err != nil {
				log.Printf("Error loading %s: %v", region, err)
				continue
			}
			graphsMu.Lock()
			graphs[region] = g
			graphsMu.Unlock()
			log.Printf("Loaded %s with %d nodes, %d edges", region, len(g.Nodes), len(g.Edges))
		}
	}
}

func loadGraphML(filePath string) (*Graph, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %w", err)
	}

	var gml GraphML
	if err := xml.Unmarshal(data, &gml); err != nil {
		return nil, fmt.Errorf("failed to parse GraphML: %w", err)
	}

	g := &Graph{
		Nodes: make(map[string]*GraphNode),
		Edges: make(map[string][]*GraphEdge),
	}

	// Parse nodes
	for _, node := range gml.Graph.Nodes {
		n := &GraphNode{ID: node.ID}
		for _, d := range node.Data {
			if d.Key == "d4" {  // y coordinate
				n.Lat, _ = strconv.ParseFloat(d.Value, 64)
			} else if d.Key == "d5" {  // x coordinate
				n.Lng, _ = strconv.ParseFloat(d.Value, 64)
			}
		}
		g.Nodes[node.ID] = n
	}

	// Parse edges
	for _, edge := range gml.Graph.Edges {
		for _, d := range edge.Data {
			if d.Key == "d16" {  // length
				val, _ := strconv.ParseFloat(d.Value, 64)
				g.Edges[edge.Source] = append(g.Edges[edge.Source], &GraphEdge{
					Target: edge.Target,
					Length: val,
				})
				break
			}
		}
	}

	return g, nil
}

func haversine(lat1, lng1, lat2, lng2 float64) float64 {
	const R = 6371000 // Earth radius in meters
	lat1Rad := lat1 * math.Pi / 180
	lat2Rad := lat2 * math.Pi / 180
	dlat := (lat2 - lat1) * math.Pi / 180
	dlng := (lng2 - lng1) * math.Pi / 180

	a := math.Sin(dlat/2)*math.Sin(dlat/2) +
		math.Cos(lat1Rad)*math.Cos(lat2Rad)*math.Sin(dlng/2)*math.Sin(dlng/2)
	c := 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
	return R * c
}

func findNearestNode(g *Graph, lat, lng float64, maxDist float64) (string, float64) {
	var nearest string
	var minDist = maxDist

	for id, node := range g.Nodes {
		dist := haversine(lat, lng, node.Lat, node.Lng)
		if dist < minDist {
			minDist = dist
			nearest = id
		}
	}

	return nearest, minDist
}

// Dijkstra's algorithm with priority queue (much faster)
type PathNode struct {
	NodeID string
	Dist   float64
	Index  int
}

type PriorityQueue []*PathNode

func (pq PriorityQueue) Len() int           { return len(pq) }
func (pq PriorityQueue) Less(i, j int) bool { return pq[i].Dist < pq[j].Dist }
func (pq PriorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
	pq[i].Index = i
	pq[j].Index = j
}

func (pq *PriorityQueue) Push(x interface{}) {
	n := len(*pq)
	item := x.(*PathNode)
	item.Index = n
	*pq = append(*pq, item)
}

func (pq *PriorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	item.Index = -1
	*pq = old[0 : n-1]
	return item
}

func shortestPath(g *Graph, start, end string) ([]string, float64) {
	dist := make(map[string]float64)
	prev := make(map[string]string)

	for id := range g.Nodes {
		dist[id] = math.MaxFloat64
	}
	dist[start] = 0

	pq := make(PriorityQueue, 0)
	heap.Init(&pq)
	heap.Push(&pq, &PathNode{NodeID: start, Dist: 0})

	for pq.Len() > 0 {
		u := heap.Pop(&pq).(*PathNode)

		if u.Dist > dist[u.NodeID] {
			continue
		}

		if u.NodeID == end {
			break
		}

		for _, edge := range g.Edges[u.NodeID] {
			alt := dist[u.NodeID] + edge.Length
			if alt < dist[edge.Target] {
				dist[edge.Target] = alt
				prev[edge.Target] = u.NodeID
				heap.Push(&pq, &PathNode{NodeID: edge.Target, Dist: alt})
			}
		}
	}

	// Reconstruct path
	var path []string
	current := end
	for current != "" {
		path = append([]string{current}, path...)
		current = prev[current]
	}

	return path, dist[end]
}

func pathToCoordinates(g *Graph, path []string) [][]float64 {
	coords := make([][]float64, 0, len(path))
	seen := make(map[string]bool)

	for _, nodeID := range path {
		if node, ok := g.Nodes[nodeID]; ok && !seen[nodeID] {
			coords = append(coords, []float64{node.Lng, node.Lat})
			seen[nodeID] = true
		}
	}

	return coords
}

func routeHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	var req RouteRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	// Check cache
	cacheKey := fmt.Sprintf("route_%.4f_%.4f_%.4f_%.4f", req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng)
	cacheMu.RLock()
	if cached, ok := cache[cacheKey]; ok {
		cacheMu.RUnlock()
		json.NewEncoder(w).Encode(cached)
		return
	}
	cacheMu.RUnlock()

	// Determine region
	region := req.DriverRegion
	if region == "" {
		region = detectRegion(req.PickupLat, req.PickupLng)
	}

	graphsMu.RLock()
	g, ok := graphs[region]
	graphsMu.RUnlock()

	if !ok {
		http.Error(w, fmt.Sprintf("Region %s not found", region), http.StatusBadRequest)
		return
	}

	// Find nearest nodes
	startNode, startDist := findNearestNode(g, req.PickupLat, req.PickupLng, 5000)
	endNode, endDist := findNearestNode(g, req.DropoffLat, req.DropoffLng, 5000)

	if startNode == "" || endNode == "" || startDist > 5000 || endDist > 5000 {
		// Fallback route
		coords := generateCurvedRoute(req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng)
		distance := haversine(req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng)
		duration := int(distance / 15) // ~15 m/s average

		resp := RouteResponse{
			Primary: Route{
				Coordinates:     coords,
				DistanceKm:      distance / 1000,
				DistanceM:       distance,
				DurationSeconds: duration,
				DurationMinutes: duration / 60,
			},
		}

		cacheMu.Lock()
		cache[cacheKey] = resp
		cacheMu.Unlock()

		json.NewEncoder(w).Encode(resp)
		return
	}

	// Calculate shortest path
	path, pathDist := shortestPath(g, startNode, endNode)
	coords := pathToCoordinates(g, path)

	if len(coords) < 2 {
		coords = generateCurvedRoute(req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng)
	}

	distance := haversine(req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng)
	if pathDist < math.MaxFloat64 {
		distance = pathDist
	}
	duration := int(distance / 15)

	resp := RouteResponse{
		Primary: Route{
			Coordinates:     coords,
			DistanceKm:      distance / 1000,
			DistanceM:       distance,
			DurationSeconds: duration,
			DurationMinutes: duration / 60,
		},
	}

	cacheMu.Lock()
	cache[cacheKey] = resp
	cacheMu.Unlock()

	json.NewEncoder(w).Encode(resp)
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":  "healthy",
		"service": "go-routing-service",
		"timestamp": time.Now().UTC(),
	})
}

func websocketRouteHandler(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}
	defer conn.Close()

	log.Printf("[WS] New route calculation client connected")

	for {
		// Read message from client
		_, message, err := conn.ReadMessage()
		if err != nil {
			log.Printf("[WS] Client disconnected: %v", err)
			break
		}

		// Parse request
		var req RouteRequest
		if err := json.Unmarshal(message, &req); err != nil {
			log.Printf("[WS] Invalid request: %v", err)
			conn.WriteJSON(map[string]interface{}{
				"error": "Invalid request format",
			})
			continue
		}

		log.Printf("[WS] Route request received: %+v", req)

		// Create cache key
		cacheKey := fmt.Sprintf("route_%.6f_%.6f_%.6f_%.6f_%s",
			req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng, req.DriverRegion)

		// Check cache
		cacheMu.RLock()
		if cached, ok := cache[cacheKey]; ok {
			cacheMu.RUnlock()
			log.Printf("[WS] Cache hit for route")
			conn.WriteJSON(cached)
			continue
		}
		cacheMu.RUnlock()

		// Determine region
		region := req.DriverRegion
		if region == "" {
			region = detectRegion(req.PickupLat, req.PickupLng)
		}

		graphsMu.RLock()
		g, ok := graphs[region]
		graphsMu.RUnlock()

		if !ok {
			conn.WriteJSON(map[string]interface{}{
				"error": fmt.Sprintf("Region %s not found", region),
			})
			continue
		}

		// Find nearest nodes
		startNode, startDist := findNearestNode(g, req.PickupLat, req.PickupLng, 5000)
		endNode, endDist := findNearestNode(g, req.DropoffLat, req.DropoffLng, 5000)

		if startNode == "" || endNode == "" || startDist > 5000 || endDist > 5000 {
			// Fallback route
			coords := generateCurvedRoute(req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng)
			distance := haversine(req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng)
			duration := int(distance / 15) // ~15 m/s average

			resp := RouteResponse{
				Primary: Route{
					Coordinates:     coords,
					DistanceKm:      distance / 1000,
					DistanceM:       distance,
					DurationSeconds: duration,
					DurationMinutes: duration / 60,
				},
			}

			cacheMu.Lock()
			cache[cacheKey] = resp
			cacheMu.Unlock()

			conn.WriteJSON(resp)
			continue
		}

		// Calculate shortest path
		path, pathDist := shortestPath(g, startNode, endNode)
		coords := pathToCoordinates(g, path)

		if len(coords) < 2 {
			coords = generateCurvedRoute(req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng)
		}

		distance := haversine(req.PickupLat, req.PickupLng, req.DropoffLat, req.DropoffLng)
		if pathDist < math.MaxFloat64 {
			distance = pathDist
		}
		duration := int(distance / 15)

		resp := RouteResponse{
			Primary: Route{
				Coordinates:     coords,
				DistanceKm:      distance / 1000,
				DistanceM:       distance,
				DurationSeconds: duration,
				DurationMinutes: duration / 60,
			},
		}

		cacheMu.Lock()
		cache[cacheKey] = resp
		cacheMu.Unlock()

		log.Printf("[WS] Sending route with %d waypoints", len(coords))
		conn.WriteJSON(resp)
	}
}

func generateCurvedRoute(lat1, lng1, lat2, lng2 float64) [][]float64 {
	coords := make([][]float64, 31)
	for i := 0; i <= 30; i++ {
		t := float64(i) / 30.0
		lat := lat1 + (lat2-lat1)*t
		lng := lng1 + (lng2-lng1)*t

		// Add slight curve
		curve := math.Sin(t*math.Pi) * 0.015
		lat += curve * (lng2 - lng1)
		lng += curve * (lat2 - lat1)

		coords[i] = []float64{lng, lat}
	}
	return coords
}

func detectRegion(lat, lng float64) string {
	regions := map[string][4]float64{
		"Northern":      {8.24, 10.30, -1.30, 0.57},
		"North_East":    {9.94, 10.65, -1.17, 0.40},
		"Upper_East":    {10.33, 11.16, -1.49, 0.03},
		"Upper_West":    {9.68, 11.00, -2.94, -1.49},
		"Savannah":      {8.16, 9.83, -2.75, -0.15},
		"Oti":           {7.10, 8.75, 0.09, 0.65},
		"Bono_East":     {7.34, 8.76, -2.12, -0.13},
		"Bono":          {6.88, 8.40, -3.09, -1.93},
		"Ahafo":         {6.40, 7.18, -2.86, -2.25},
		"Ashanti":       {5.87, 7.59, -2.42, -0.57},
		"Central":       {5.04, 6.27, -2.16, -0.40},
		"Eastern":       {5.71, 6.87, -1.23, 0.14},
		"Greater_Accra": {5.48, 6.10, -0.51, 0.65},
		"Volta":         {5.77, 7.19, 0.12, 1.20},
		"Western_North": {5.38, 6.97, -3.25, -2.14},
		"Western":       {4.74, 5.78, -3.53, -2.74},
	}

	for region, bounds := range regions {
		if lat >= bounds[0] && lat <= bounds[1] && lng >= bounds[2] && lng <= bounds[3] {
			return region
		}
	}
	return "Northern"
}

func main() {
	router := mux.NewRouter()

	router.HandleFunc("/route", routeHandler).Methods("POST")
	router.HandleFunc("/ws/route", websocketRouteHandler).Methods("GET")
	router.HandleFunc("/health", healthHandler).Methods("GET")

	port := ":8012"
	log.Printf("Go Routing Service starting on port %s", port)
	log.Fatal(http.ListenAndServe(port, router))
}

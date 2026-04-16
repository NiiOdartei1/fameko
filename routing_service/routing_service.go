package main

import (
	"context"
	"encoding/json"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/mux"
)

// RouteRequest represents an incoming route request
type RouteRequest struct {
	PickupLat    float64  `json:"pickup_lat"`
	PickupLng    float64  `json:"pickup_lng"`
	DropoffLat   float64  `json:"dropoff_lat"`
	DropoffLng   float64  `json:"dropoff_lng"`
	DriverLat    *float64 `json:"driver_lat,omitempty"`
	DriverLng    *float64 `json:"driver_lng,omitempty"`
	Alternatives int      `json:"alternatives"`
	DetailLevel  string   `json:"detail_level"`
}

// RouteResponse represents the route response
type RouteResponse struct {
	RouteCoords [][]float64   `json:"route_coords"`
	ETAMin      float64       `json:"eta_min"`
	AltRoutes   [][][]float64 `json:"alt_routes"`
	FromCache   bool          `json:"from_cache"`
	FromDriver  bool          `json:"from_driver_location"`
}

// CachedRoute stores route data with metadata
type CachedRoute struct {
	Response  RouteResponse
	Timestamp time.Time
}

// RouteCache provides thread-safe caching
type RouteCache struct {
	routes map[string]CachedRoute
	mu     sync.RWMutex
	ttl    time.Duration
	maxLen int
}

// NewRouteCache creates a new route cache
func NewRouteCache(ttl time.Duration, maxLen int) *RouteCache {
	rc := &RouteCache{
		routes: make(map[string]CachedRoute),
		ttl:    ttl,
		maxLen: maxLen,
	}

	// Start cleanup goroutine
	go rc.cleanupExpired()

	return rc
}

// Get retrieves a route from cache
func (rc *RouteCache) Get(key string) (RouteResponse, bool) {
	rc.mu.RLock()
	defer rc.mu.RUnlock()

	cached, exists := rc.routes[key]
	if !exists {
		return RouteResponse{}, false
	}

	if time.Since(cached.Timestamp) > rc.ttl {
		return RouteResponse{}, false
	}

	return cached.Response, true
}

// Set stores a route in cache
func (rc *RouteCache) Set(key string, response RouteResponse) {
	rc.mu.Lock()
	defer rc.mu.Unlock()

	// If cache is full, remove oldest entries
	if len(rc.routes) >= rc.maxLen {
		oldest := ""
		oldestTime := time.Now()
		for k, v := range rc.routes {
			if v.Timestamp.Before(oldestTime) {
				oldestTime = v.Timestamp
				oldest = k
			}
		}
		if oldest != "" {
			delete(rc.routes, oldest)
		}
	}

	response.FromCache = false
	rc.routes[key] = CachedRoute{
		Response:  response,
		Timestamp: time.Now(),
	}
}

// cleanupExpired removes expired entries
func (rc *RouteCache) cleanupExpired() {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		rc.mu.Lock()
		now := time.Now()
		for k, v := range rc.routes {
			if now.Sub(v.Timestamp) > rc.ttl {
				delete(rc.routes, k)
			}
		}
		rc.mu.Unlock()
	}
}

// RoutingService manages routing with caching and Python backend delegation
type RoutingService struct {
	pythonURL string
	cache     *RouteCache
	client    *http.Client
}

// NewRoutingService creates a new routing service
func NewRoutingService(pythonURL string, cacheTTL time.Duration, cacheMaxLen int) *RoutingService {
	return &RoutingService{
		pythonURL: pythonURL,
		cache:     NewRouteCache(cacheTTL, cacheMaxLen),
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// makeCacheKey creates a cache key from route parameters
func makeCacheKey(pickup_lat, pickup_lng, drop_lat, drop_lng float64, alternatives int, detail_level string, driver_lat, driver_lng *float64) string {
	key := formatFloat(pickup_lat) + "|" + formatFloat(pickup_lng) + "|" +
		formatFloat(drop_lat) + "|" + formatFloat(drop_lng) + "|" +
		strconv.Itoa(alternatives) + "|" + detail_level

	if driver_lat != nil && driver_lng != nil {
		key += "|" + formatFloat(*driver_lat) + "|" + formatFloat(*driver_lng)
	}

	return key
}

// formatFloat formats a float to 7 decimal places
func formatFloat(f float64) string {
	return strconv.FormatFloat(f, 'f', 7, 64)
}

// GetRoute gets a route with caching
func (rs *RoutingService) GetRoute(ctx context.Context, pickupLat, pickupLng, dropoffLat, dropoffLng float64, alternatives int, detailLevel string, driverLat, driverLng *float64) (RouteResponse, error) {
	// Check cache first
	key := makeCacheKey(pickupLat, pickupLng, dropoffLat, dropoffLng, alternatives, detailLevel, driverLat, driverLng)
	if cached, found := rs.cache.Get(key); found {
		log.Printf("Cache hit for key: %s", key[:min(20, len(key))])
		return cached, nil
	}

	log.Printf("Cache miss, fetching from Python service for key: %s", key[:min(20, len(key))])

	// Build request to Python service
	params := "?pickup_lat=" + formatFloat(pickupLat) + "&pickup_lng=" + formatFloat(pickupLng) +
		"&drop_lat=" + formatFloat(dropoffLat) + "&drop_lng=" + formatFloat(dropoffLng) +
		"&alternatives=" + strconv.Itoa(alternatives) + "&detail_level=" + detailLevel

	if driverLat != nil && driverLng != nil {
		params += "&driver_lat=" + formatFloat(*driverLat) + "&driver_lng=" + formatFloat(*driverLng)
	}

	// Call Python service
	url := rs.pythonURL + "/route" + params
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		log.Printf("Error creating request: %v", err)
		return RouteResponse{}, err
	}

	resp, err := rs.client.Do(req)
	if err != nil {
		log.Printf("Error calling Python service: %v", err)
		return RouteResponse{}, err
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		log.Printf("Error decoding response: %v", err)
		return RouteResponse{}, err
	}

	// Convert response to RouteResponse
	response := rs.convertResponse(result, driverLat != nil && driverLng != nil)

	// Cache the result
	rs.cache.Set(key, response)

	return response, nil
}

// convertResponse converts Python service response to RouteResponse
func (rs *RoutingService) convertResponse(data map[string]interface{}, fromDriver bool) RouteResponse {
	response := RouteResponse{
		FromDriver: fromDriver,
		FromCache:  false,
	}

	if coords, ok := data["route_coords"].([]interface{}); ok {
		for _, c := range coords {
			if coord, ok := c.([]interface{}); ok && len(coord) >= 2 {
				lng := toFloat64(coord[0])
				lat := toFloat64(coord[1])
				response.RouteCoords = append(response.RouteCoords, []float64{lng, lat})
			}
		}
	}

	if eta, ok := data["eta_min"].(float64); ok {
		response.ETAMin = eta
	}

	if altRoutes, ok := data["alt_routes"].([]interface{}); ok {
		for _, alt := range altRoutes {
			if altCoords, ok := alt.([]interface{}); ok {
				var route [][]float64
				for _, c := range altCoords {
					if coord, ok := c.([]interface{}); ok && len(coord) >= 2 {
						lng := toFloat64(coord[0])
						lat := toFloat64(coord[1])
						route = append(route, []float64{lng, lat})
					}
				}
				response.AltRoutes = append(response.AltRoutes, route)
			}
		}
	}

	return response
}

// toFloat64 safely converts an interface to float64
func toFloat64(v interface{}) float64 {
	switch val := v.(type) {
	case float64:
		return val
	case int:
		return float64(val)
	case string:
		f, _ := strconv.ParseFloat(val, 64)
		return f
	default:
		return 0
	}
}

// min returns minimum of two integers
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// HTTP Handlers

// handleRoute handles route requests
func (rs *RoutingService) handleRoute(w http.ResponseWriter, r *http.Request) {
	pickupLat, _ := parseFloat(r.URL.Query().Get("pickup_lat"))
	pickupLng, _ := parseFloat(r.URL.Query().Get("pickup_lng"))
	dropoffLat, _ := parseFloat(r.URL.Query().Get("drop_lat"))
	dropoffLng, _ := parseFloat(r.URL.Query().Get("drop_lng"))
	alternatives := parseInt(r.URL.Query().Get("alternatives"), 1)
	detailLevel := r.URL.Query().Get("detail_level")
	if detailLevel == "" {
		detailLevel = "medium"
	}

	var driverLat, driverLng *float64
	if dLat := r.URL.Query().Get("driver_lat"); dLat != "" {
		lat, _ := parseFloat(dLat)
		driverLat = &lat
	}
	if dLng := r.URL.Query().Get("driver_lng"); dLng != "" {
		lng, _ := parseFloat(dLng)
		driverLng = &lng
	}

	route, err := rs.GetRoute(r.Context(), pickupLat, pickupLng, dropoffLat, dropoffLng, alternatives, detailLevel, driverLat, driverLng)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
		return
	}

	route.FromCache = false // Set to false since we just fetched it
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(route)
}

// handleStatus returns service status
func (rs *RoutingService) handleStatus(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status":  "ok",
		"service": "Go Routing Cache & Proxy (High-Performance)",
		"version": "1.0",
	})
}

// handleHealth returns health check
func (rs *RoutingService) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]bool{"healthy": true})
}

// Utility functions

func parseFloat(s string) (float64, bool) {
	if s == "" {
		return 0, false
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, false
	}
	return f, true
}

func parseInt(s string, def int) int {
	if s == "" {
		return def
	}
	i, _ := strconv.Atoi(s)
	return i
}

// main starts the routing service
func main() {
	port := flag.String("port", "8011", "Port to listen on")
	pythonURL := flag.String("python", "http://localhost:8010", "Python routing service URL")
	cacheTTL := flag.Duration("cache-ttl", 60*time.Minute, "Cache TTL")
	cacheMaxLen := flag.Int("cache-max", 2000, "Maximum cache entries")

	flag.Parse()

	rs := NewRoutingService(*pythonURL, *cacheTTL, *cacheMaxLen)

	router := mux.NewRouter()
	router.HandleFunc("/route", rs.handleRoute).Methods("GET")
	router.HandleFunc("/status", rs.handleStatus).Methods("GET")
	router.HandleFunc("/health", rs.handleHealth).Methods("GET")

	server := &http.Server{
		Addr:         "0.0.0.0:" + *port,
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	log.Printf("Starting Go Routing Cache Service on port %s (proxying to %s)", *port, *pythonURL)

	go func() {
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Listen error: %v", err)
		}
	}()

	// Wait for shutdown signal
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	<-sigChan

	log.Println("Shutting down routing cache service...")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Printf("Shutdown error: %v", err)
	}
}

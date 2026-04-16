package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// Location represents driver location data
type Location struct {
	DriverID   int       `json:"driver_id"`
	Lat        float64   `json:"lat"`
	Lng        float64   `json:"lng"`
	Timestamp  time.Time `json:"timestamp"`
	DeliveryID *int      `json:"delivery_id,omitempty"`
}

// ConnectionManager manages WebSocket connections
type ConnectionManager struct {
	drivers            map[int]*websocket.Conn  // driver_id -> ws connection
	monitors           map[*websocket.Conn]bool // monitor connections
	lastKnownLocations map[int]Location         // driver_id -> last location
	mu                 sync.RWMutex
	broadcast          chan Location
}

var (
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			return true // Allow all origins for development
		},
	}
	manager = &ConnectionManager{
		drivers:            make(map[int]*websocket.Conn),
		monitors:           make(map[*websocket.Conn]bool),
		lastKnownLocations: make(map[int]Location),
		broadcast:          make(chan Location, 256),
	}
)

// ===================== CONNECTION MANAGER METHODS =====================

func (cm *ConnectionManager) addDriver(driverID int, conn *websocket.Conn) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	cm.drivers[driverID] = conn
	log.Printf("Driver %d connected\n", driverID)
}

func (cm *ConnectionManager) removeDriver(driverID int) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	delete(cm.drivers, driverID)
	log.Printf("Driver %d disconnected\n", driverID)
}

func (cm *ConnectionManager) addMonitor(conn *websocket.Conn) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	cm.monitors[conn] = true
	log.Println("Monitor connected")
}

func (cm *ConnectionManager) removeMonitor(conn *websocket.Conn) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	delete(cm.monitors, conn)
	log.Println("Monitor disconnected")
}

func (cm *ConnectionManager) storeLocation(loc Location) {
	cm.mu.Lock()
	defer cm.mu.Unlock()
	cm.lastKnownLocations[loc.DriverID] = loc
}

func (cm *ConnectionManager) getLocation(driverID int) *Location {
	cm.mu.RLock()
	defer cm.mu.RUnlock()
	if loc, ok := cm.lastKnownLocations[driverID]; ok {
		return &loc
	}
	return nil
}

func (cm *ConnectionManager) getAllLocations() []Location {
	cm.mu.RLock()
	defer cm.mu.RUnlock()
	locations := make([]Location, 0, len(cm.lastKnownLocations))
	for _, loc := range cm.lastKnownLocations {
		locations = append(locations, loc)
	}
	return locations
}

func (cm *ConnectionManager) broadcastToMonitors(loc Location) {
	cm.mu.RLock()
	monitors := make([]*websocket.Conn, 0, len(cm.monitors))
	for conn := range cm.monitors {
		monitors = append(monitors, conn)
	}
	cm.mu.RUnlock()

	data, _ := json.Marshal(loc)
	for _, conn := range monitors {
		conn.WriteMessage(websocket.TextMessage, data)
	}
}

// ===================== HTTP HANDLERS =====================

// handleDriverWS handles WebSocket connections from drivers
func handleDriverWS(w http.ResponseWriter, r *http.Request) {
	driverIDStr := r.URL.Query().Get("driver_id")
	if driverIDStr == "" {
		http.Error(w, "driver_id required", http.StatusBadRequest)
		return
	}

	var driverID int
	_, err := fmt.Sscanf(driverIDStr, "%d", &driverID)
	if err != nil {
		http.Error(w, "invalid driver_id", http.StatusBadRequest)
		return
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v\n", err)
		return
	}
	defer conn.Close()

	manager.addDriver(driverID, conn)
	defer manager.removeDriver(driverID)

	for {
		var loc Location
		err := conn.ReadJSON(&loc)
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v\n", err)
			}
			break
		}

		loc.DriverID = driverID
		loc.Timestamp = time.Now()

		// Store location
		manager.storeLocation(loc)

		// Broadcast to monitors
		manager.broadcastToMonitors(loc)

		log.Printf("Location update - Driver: %d, Lat: %.4f, Lng: %.4f\n", driverID, loc.Lat, loc.Lng)
	}
}

// handleMonitorWS handles WebSocket connections from monitors/dispatchers
func handleMonitorWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v\n", err)
		return
	}
	defer conn.Close()

	manager.addMonitor(conn)
	defer manager.removeMonitor(conn)

	// Send all current locations to newly connected monitor
	locations := manager.getAllLocations()
	for _, loc := range locations {
		data, _ := json.Marshal(loc)
		conn.WriteMessage(websocket.TextMessage, data)
	}

	// Keep connection open
	for {
		_, _, err := conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Printf("WebSocket error: %v\n", err)
			}
			break
		}
	}
}

// handleLocationHTTP handles HTTP POST requests for location updates
func handleLocationHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var loc Location
	err := json.NewDecoder(r.Body).Decode(&loc)
	if err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if loc.DriverID == 0 {
		http.Error(w, "driver_id required", http.StatusBadRequest)
		return
	}

	loc.Timestamp = time.Now()
	manager.storeLocation(loc)
	manager.broadcastToMonitors(loc)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "ok"})

	log.Printf("HTTP Location update - Driver: %d, Lat: %.4f, Lng: %.4f\n", loc.DriverID, loc.Lat, loc.Lng)
}

// handleGetLocation handles GET requests for driver location
func handleGetLocation(w http.ResponseWriter, r *http.Request) {
	driverIDStr := r.URL.Query().Get("driver_id")
	if driverIDStr == "" {
		http.Error(w, "driver_id required", http.StatusBadRequest)
		return
	}

	var driverID int
	_, err := fmt.Sscanf(driverIDStr, "%d", &driverID)
	if err != nil {
		http.Error(w, "invalid driver_id", http.StatusBadRequest)
		return
	}

	loc := manager.getLocation(driverID)
	if loc == nil {
		http.Error(w, "Location not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(loc)
}

// handleGetAllLocations handles GET requests for all driver locations
func handleGetAllLocations(w http.ResponseWriter, r *http.Request) {
	locations := manager.getAllLocations()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(locations)
}

// handleHealth handles health check requests
func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":          "healthy",
		"service":         "live-location-service",
		"timestamp":       time.Now(),
		"active_drivers":  len(manager.drivers),
		"active_monitors": len(manager.monitors),
	})
}

// ===================== MAIN =====================

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "5001"
	}

	// HTTP Routes
	http.HandleFunc("/ws/driver", handleDriverWS)
	http.HandleFunc("/ws/monitor", handleMonitorWS)
	http.HandleFunc("/location", handleLocationHTTP)
	http.HandleFunc("/location/get", handleGetLocation)
	http.HandleFunc("/locations", handleGetAllLocations)
	http.HandleFunc("/health", handleHealth)

	// Serve a simple HTML page for testing
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html")
		fmt.Fprint(w, `
<!DOCTYPE html>
<html>
<head>
    <title>Live Location Service</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        .section { margin: 20px 0; padding: 10px; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>Live Location Service</h1>
    <p>WebSocket-based real-time driver location tracking</p>
    
    <div class="section">
        <h2>Endpoints</h2>
        <ul>
            <li>WS: /ws/driver?driver_id=123 (Driver location updates)</li>
            <li>WS: /ws/monitor (Monitor/dispatcher updates)</li>
            <li>POST: /location (HTTP location update)</li>
            <li>GET: /location/get?driver_id=123 (Get driver location)</li>
            <li>GET: /locations (Get all driver locations)</li>
            <li>GET: /health (Health check)</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>Example Usage</h2>
        <p><strong>Driver sends location (WebSocket):</strong></p>
        <pre>{
  "driver_id": 123,
  "lat": 5.6037,
  "lng": -0.1869,
  "delivery_id": 1
}</pre>
        <p><strong>Monitor receives broadcasts</strong></p>
    </div>
</body>
</html>
		`)
	})

	log.Printf("Live Location Service starting on port %s\n", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

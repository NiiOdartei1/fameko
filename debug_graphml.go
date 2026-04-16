package main

import (
	"encoding/xml"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
)

// GraphML structures (from routing_service_go.go)
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

func main() {
	region := "Northern"
	graphmlPath := filepath.Join("data", region+"_Region_Ghana.graphml")
	
	fmt.Printf("Loading %s from %s\n", region, graphmlPath)
	fmt.Printf("File exists: ")
	
	if _, err := os.Stat(graphmlPath); err == nil {
		fmt.Println("YES")
	} else {
		fmt.Println("NO")
		return
	}

	data, err := os.ReadFile(graphmlPath)
	if err != nil {
		fmt.Printf("Error reading file: %v\n", err)
		return
	}

	var gml GraphML
	if err := xml.Unmarshal(data, &gml); err != nil {
		fmt.Printf("Error parsing XML: %v\n", err)
		return
	}

	fmt.Printf("Nodes: %d\n", len(gml.Graph.Nodes))
	fmt.Printf("Edges: %d\n", len(gml.Graph.Edges))

	// Check one edge
	if len(gml.Graph.Edges) > 0 {
		edge := gml.Graph.Edges[0]
		fmt.Printf("\nFirst edge: %s -> %s\n", edge.Source, edge.Target)
		fmt.Printf("Edge data: %+v\n", edge.Data)
		for _, d := range edge.Data {
			if d.Key == "length" {
				val, _ := strconv.ParseFloat(d.Value, 64)
				fmt.Printf("Length (original): %s (parsed: %.1f)\n", d.Value, val)
			}
		}
	}
}

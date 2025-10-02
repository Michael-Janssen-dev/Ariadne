package main

import (
	"context"
	"encoding/csv"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	collectorv1 "go.opentelemetry.io/proto/otlp/collector/trace/v1"
	commonv1 "go.opentelemetry.io/proto/otlp/common/v1"
	tracev1 "go.opentelemetry.io/proto/otlp/trace/v1"
	"google.golang.org/grpc"
)

// SpanBuffer manages the collection of spans with size limits
type SpanBuffer struct {
	spans          []*tracev1.Span
	mu             sync.Mutex
	maxSpans       int
	maxSizeBytes   int64
	currentSize    int64
	resourceAttrs  map[string]string
	limitReached   bool
}

// NewSpanBuffer creates a new span buffer
func NewSpanBuffer(maxSpans int, maxSizeMB int) *SpanBuffer {
	return &SpanBuffer{
		spans:         make([]*tracev1.Span, 0),
		maxSpans:      maxSpans,
		maxSizeBytes:  int64(maxSizeMB * 1024 * 1024),
		resourceAttrs: make(map[string]string),
	}
}

// AddSpans adds spans from an OTLP request
func (sb *SpanBuffer) AddSpans(req *collectorv1.ExportTraceServiceRequest) (accepted int, limitReached bool) {
	sb.mu.Lock()
	defer sb.mu.Unlock()

	for _, resourceSpan := range req.ResourceSpans {
		// Extract resource attributes (service name, etc.)
		if resourceSpan.Resource != nil {
			for _, attr := range resourceSpan.Resource.Attributes {
				sb.resourceAttrs[attr.Key] = attributeValueToString(attr.Value)
			}
		}

		for _, scopeSpan := range resourceSpan.ScopeSpans {
			for _, span := range scopeSpan.Spans {
				// Check if we've hit the limits
				if sb.maxSpans > 0 && len(sb.spans) >= sb.maxSpans {
					sb.limitReached = true
					return accepted, true
				}

				// Estimate span size (rough approximation)
				spanSize := int64(len(span.Name) + len(span.TraceId) + len(span.SpanId) + 100)
				for _, attr := range span.Attributes {
					spanSize += int64(len(attr.Key) + 50) // rough estimate for value
				}
				
				if sb.maxSizeBytes > 0 && sb.currentSize+spanSize > sb.maxSizeBytes {
					sb.limitReached = true
					return accepted, true
				}

				// Add the span
				sb.spans = append(sb.spans, span)
				sb.currentSize += spanSize
				accepted++
			}
		}
	}

	return accepted, false
}

// IsLimitReached returns true if buffer has reached its limit
func (sb *SpanBuffer) IsLimitReached() bool {
	sb.mu.Lock()
	defer sb.mu.Unlock()
	return sb.limitReached
}

// ExportToCSV writes all collected spans to a CSV file
func (sb *SpanBuffer) ExportToCSV(filename string) error {
	sb.mu.Lock()
	defer sb.mu.Unlock()

	file, err := os.Create(filename)
	if err != nil {
		return fmt.Errorf("failed to create CSV file: %w", err)
	}
	defer file.Close()

	writer := csv.NewWriter(file)
	defer writer.Flush()

	// Write header
	header := []string{
		"trace_id",
		"span_id",
		"parent_span_id",
		"name",
		"kind",
		"start_time_unix_nano",
		"end_time_unix_nano",
		"status_code",
		"status_message",
		"service_name",
		"attributes",
	}
	if err := writer.Write(header); err != nil {
		return fmt.Errorf("failed to write header: %w", err)
	}

	// Write spans
	serviceName := sb.resourceAttrs["service.name"]
	for _, span := range sb.spans {		
		// Format attributes as key=value pairs
		attrs := ""
		for i, attr := range span.Attributes {
			if i > 0 {
				attrs += "; "
			}
			attrs += fmt.Sprintf("%s=%s", attr.Key, attributeValueToString(attr.Value))
		}

		row := []string{
			fmt.Sprintf("%x", span.TraceId),
			fmt.Sprintf("%x", span.SpanId),
			fmt.Sprintf("%x", span.ParentSpanId),
			span.Name,
			span.Kind.String(),
			fmt.Sprintf("%d", span.StartTimeUnixNano),
			fmt.Sprintf("%d", span.EndTimeUnixNano),
			span.Status.GetCode().String(),
			span.Status.GetMessage(),
			serviceName,
			attrs,
		}

		if err := writer.Write(row); err != nil {
			return fmt.Errorf("failed to write row: %w", err)
		}
	}

	log.Printf("Exported %d spans to %s (%.2f MB)", 
		len(sb.spans), 
		filename, 
		float64(sb.currentSize)/(1024*1024))
	
	return nil
}

// GetStats returns current buffer statistics
func (sb *SpanBuffer) GetStats() (count int, sizeMB float64) {
	sb.mu.Lock()
	defer sb.mu.Unlock()
	return len(sb.spans), float64(sb.currentSize) / (1024 * 1024)
}

// Helper function to convert attribute values to strings
func attributeValueToString(v *commonv1.AnyValue) string {
	if v == nil {
		return ""
	}
	
	switch {
	case v.GetStringValue() != "":
		return v.GetStringValue()
	case v.GetBoolValue():
		return fmt.Sprintf("%t", v.GetBoolValue())
	case v.GetIntValue() != 0:
		return fmt.Sprintf("%d", v.GetIntValue())
	case v.GetDoubleValue() != 0:
		return fmt.Sprintf("%f", v.GetDoubleValue())
	case v.GetArrayValue() != nil:
		return "[array]"
	case v.GetKvlistValue() != nil:
		return "[kvlist]"
	case v.GetBytesValue() != nil:
		return "[bytes]"
	default:
		return ""
	}
}

// TraceServiceServer implements the OTLP gRPC service
type TraceServiceServer struct {
	collectorv1.UnimplementedTraceServiceServer
	buffer *SpanBuffer
}

// Export handles incoming trace data
func (s *TraceServiceServer) Export(ctx context.Context, req *collectorv1.ExportTraceServiceRequest) (*collectorv1.ExportTraceServiceResponse, error) {
	accepted, limitReached := s.buffer.AddSpans(req)
	
	count, sizeMB := s.buffer.GetStats()
	log.Printf("Received %d spans (total: %d spans, %.2f MB)", accepted, count, sizeMB)
	
	if limitReached {
		log.Printf("Buffer limit reached!")
	}

	return &collectorv1.ExportTraceServiceResponse{}, nil
}

func main() {
	// CLI flags
	var (
		port       = flag.Int("port", 4317, "gRPC server port")
		maxSpans   = flag.Int("max-spans", 0, "Maximum number of spans to collect (0 = unlimited)")
		maxSizeMB  = flag.Int("max-size-mb", 0, "Maximum size in MB to collect (0 = unlimited)")
		duration   = flag.Duration("duration", 0, "Collection duration (e.g., 60s, 5m). 0 = run until limit or Ctrl+C")
		output     = flag.String("output", "", "Output CSV file (default: traces_TIMESTAMP.csv)")
		verbose    = flag.Bool("verbose", false, "Enable verbose logging")
	)
	flag.Parse()

	// Validate flags
	if *maxSpans == 0 && *maxSizeMB == 0 && *duration == 0 {
		log.Println("Warning: No limits set. Collection will run until interrupted (Ctrl+C)")
	}

	// Set output filename
	outputFile := *output
	if outputFile == "" {
		outputFile = fmt.Sprintf("traces_%d.csv", time.Now().Unix())
	}

	// Create buffer
	buffer := NewSpanBuffer(*maxSpans, *maxSizeMB)
	
	// Setup gRPC server
	grpcServer := grpc.NewServer()
	server := &TraceServiceServer{buffer: buffer}
	collectorv1.RegisterTraceServiceServer(grpcServer, server)
	
	listener, err := net.Listen("tcp", fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}
	
	// Start server in background
	go func() {
		log.Printf("Starting OTLP receiver on port %d", *port)
		if *maxSpans > 0 {
			log.Printf("  Max spans: %d", *maxSpans)
		}
		if *maxSizeMB > 0 {
			log.Printf("  Max size: %d MB", *maxSizeMB)
		}
		if *duration > 0 {
			log.Printf("  Duration: %s", *duration)
		}
		log.Printf("  Output: %s", outputFile)
		log.Println("Press Ctrl+C to stop collection and export")
		
		if err := grpcServer.Serve(listener); err != nil {
			log.Printf("gRPC server error: %v", err)
		}
	}()
	
	// Setup signal handler
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	
	// Setup duration timer if specified
	var durationTimer *time.Timer
	var durationChan <-chan time.Time
	if *duration > 0 {
		durationTimer = time.NewTimer(*duration)
		durationChan = durationTimer.C
	}
	
	// Setup status ticker
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()
	
	// Main loop
	for {
		select {
		case <-sigChan:
			log.Println("\nReceived interrupt signal, exporting...")
			goto export
			
		case <-durationChan:
			log.Println("\nDuration reached, exporting...")
			goto export
			
		case <-ticker.C:
			if *verbose {
				count, sizeMB := buffer.GetStats()
				log.Printf("Status: %d spans, %.2f MB", count, sizeMB)
			}
			
			// Check if buffer limit reached
			if buffer.IsLimitReached() {
				log.Println("\nBuffer limit reached, exporting...")
				goto export
			}
		}
	}
	
export:
	// Stop accepting new connections
	grpcServer.GracefulStop()
	
	// Export to CSV
	count, sizeMB := buffer.GetStats()
	log.Printf("Final stats: %d spans collected, %.2f MB", count, sizeMB)
	
	if count == 0 {
		log.Println("No spans collected, skipping export")
		return
	}
	
	if err := buffer.ExportToCSV(outputFile); err != nil {
		log.Fatalf("Failed to export: %v", err)
	}
	
	log.Println("Export complete!")
}
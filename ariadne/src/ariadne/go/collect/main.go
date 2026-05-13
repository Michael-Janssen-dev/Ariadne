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
	v1 "go.opentelemetry.io/proto/otlp/trace/v1"
	"google.golang.org/grpc"
	_ "google.golang.org/grpc/encoding/gzip"
)

// SpanWriter manages the collection of spans
type SpanWriter struct {
	writer *csv.Writer
	mu     sync.Mutex
	total  int
}

// NewSpanBuffer creates a new span buffer
func NewSpanBuffer(file *os.File) *SpanWriter {
	return &SpanWriter{
		writer: csv.NewWriter(file),
	}
}

// AddSpans adds spans from an OTLP request
func (sb *SpanWriter) AddSpans(req *collectorv1.ExportTraceServiceRequest) (accepted int) {
	sb.mu.Lock()
	defer sb.mu.Unlock()

	for _, resourceSpan := range req.ResourceSpans {
		// Get service name
		var serviceName string
		if resourceSpan.Resource != nil {
			for _, attr := range resourceSpan.Resource.Attributes {
				if attr.Key == "service.name" {
					serviceName = attributeValueToString(attr.Value)
				}
			}
		}

		for _, scopeSpan := range resourceSpan.ScopeSpans {
			for _, span := range scopeSpan.Spans {
				sb.WriteSpan(span, serviceName)
				accepted++
			}
		}
	}
	sb.total += accepted
	return accepted
}

func (sb *SpanWriter) WriteHeader() error {
	// Write header
	header := []string{
		"trace_id",
		"span_id",
		"parent_span_id",
		"name",
		"kind",
		"start_time",
		"end_time",
		"status_code",
		"status_message",
		"service_name",
		"attributes",
	}
	if err := sb.writer.Write(header); err != nil {
		return fmt.Errorf("failed to write header: %w", err)
	}
	return nil
}

func (sb *SpanWriter) WriteSpan(span *v1.Span, serviceName string) error {
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

	if err := sb.writer.Write(row); err != nil {
		return fmt.Errorf("failed to write row: %w", err)
	}

	return nil
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
	buffer *SpanWriter
}

// Export handles incoming trace data
func (s *TraceServiceServer) Export(ctx context.Context, req *collectorv1.ExportTraceServiceRequest) (*collectorv1.ExportTraceServiceResponse, error) {
	accepted := s.buffer.AddSpans(req)

	log.Printf("Received %d spans", accepted)

	return &collectorv1.ExportTraceServiceResponse{}, nil
}

func main() {
	// CLI flags
	var (
		port     = flag.Int("port", 4317, "gRPC server port")
		duration = flag.Duration("duration", 0, "Collection duration (e.g., 60s, 5m). 0 = run until limit or Ctrl+C")
		output   = flag.String("output", "", "Output CSV file (default: stdout)")
	)
	flag.Parse()

	// Validate duration flag
	if *duration == 0 {
		log.Println("Warning: No duration set. Collection will run until interrupted (Ctrl+C)")
	}

	// Set output filename
	var outputFile *os.File
	if *output == "" {
		outputFile = os.Stdout
	} else {
		file, err := os.Create(*output)
		if err != nil {
			log.Fatalf("")
		}
		defer file.Close()
		outputFile = file
	}

	// Create buffer
	buffer := NewSpanBuffer(outputFile)
	buffer.WriteHeader()

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
		if *duration > 0 {
			log.Printf("  Duration: %s", *duration)
		}
		if *output == "" {
			*output = "stdout"
		}
		log.Printf("  Output: %s", *output)
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

	// Main loop
	for {
		select {
		case <-sigChan:
			log.Println("\nReceived interrupt signal, exporting...")
			goto export

		case <-durationChan:
			log.Println("\nDuration reached, exporting...")
			goto export
		}
	}

export:
	// Stop accepting new connections
	grpcServer.GracefulStop()

	// Export to CSV
	count := buffer.total
	log.Printf("Final stats: %d spans collected", count)

	log.Println("Export complete!")
}

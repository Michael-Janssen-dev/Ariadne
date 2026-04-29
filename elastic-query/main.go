package main

import (
	"bufio"
	"bytes"
	"context"
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"strings"
	"time"

	"github.com/elastic/go-elasticsearch/v8"
)

func main() {
	esURL := flag.String("es", "http://localhost:9200", "Elasticsearch URL")
	indexSubstring := flag.String("index-substring", "span", "Index name substring to match")
	outputPath := flag.String("output", "spans.csv", "Output file path ('-' for stdout)")
	pageSize := flag.Int("page-size", 1000, "Documents per page")
	flag.Parse()

	es, err := elasticsearch.NewClient(elasticsearch.Config{Addresses: []string{*esURL}})
	if err != nil {
		log.Fatalf("create client: %v", err)
	}

	indices, err := findMatchingIndices(es, *indexSubstring)
	if err != nil {
		log.Fatalf("list indices: %v", err)
	}
	if len(indices) == 0 {
		log.Fatalf("no indices match substring %q", *indexSubstring)
	}

	writer, closer, err := openOutput(*outputPath)
	if err != nil {
		log.Fatalf("open output: %v", err)
	}
	defer closer()

	if err := exportIndices(context.Background(), es, indices, *pageSize, writer); err != nil {
		log.Fatalf("export: %v", err)
	}
}

type catIndex struct {
	Index string `json:"index"`
}

type searchResponse struct {
	ScrollID string `json:"_scroll_id"`
	Hits     struct {
		Hits []struct {
			Source map[string]any `json:"_source"`
		} `json:"hits"`
	} `json:"hits"`
}

func findMatchingIndices(es *elasticsearch.Client, substring string) ([]string, error) {
	res, err := es.Cat.Indices(
		es.Cat.Indices.WithFormat("json"),
	)
	if err != nil {
		return nil, fmt.Errorf("cat indices: %w", err)
	}
	defer res.Body.Close()
	if res.IsError() {
		return nil, fmt.Errorf("cat indices error: %s", res.String())
	}

	var items []catIndex
	if err := json.NewDecoder(res.Body).Decode(&items); err != nil {
		return nil, fmt.Errorf("decode indices: %w", err)
	}

	var matches []string
	for _, item := range items {
		if strings.Contains(item.Index, substring) {
			matches = append(matches, item.Index)
		}
	}
	return matches, nil
}

func openOutput(path string) (io.Writer, func(), error) {
	if path == "-" {
		return bufio.NewWriter(os.Stdout), func() {}, nil
	}
	file, err := os.Create(path)
	if err != nil {
		return nil, func() {}, err
	}
	writer := bufio.NewWriter(file)
	return writer, func() {
		_ = writer.Flush()
		_ = file.Close()
	}, nil
}

func exportIndices(ctx context.Context, es *elasticsearch.Client, indices []string, pageSize int, writer io.Writer) error {
	csvWriter := csv.NewWriter(writer)
	if err := csvWriter.Write(csvHeader()); err != nil {
		return fmt.Errorf("write header: %w", err)
	}

	for _, index := range indices {
		if err := exportIndex(ctx, es, index, pageSize, csvWriter); err != nil {
			return fmt.Errorf("export index %s: %w", index, err)
		}
	}

	csvWriter.Flush()
	if err := csvWriter.Error(); err != nil {
		return fmt.Errorf("flush csv: %w", err)
	}

	if buf, ok := writer.(*bufio.Writer); ok {
		return buf.Flush()
	}
	return nil
}

func exportIndex(ctx context.Context, es *elasticsearch.Client, index string, pageSize int, csvWriter *csv.Writer) error {
	bodyBytes, err := json.Marshal(buildSearchBody())
	if err != nil {
		return fmt.Errorf("build search body: %w", err)
	}

	res, err := es.Search(
		es.Search.WithContext(ctx),
		es.Search.WithIndex(index),
		es.Search.WithScroll(2*time.Minute),
		es.Search.WithSize(pageSize),
		es.Search.WithSort("_doc"),
		es.Search.WithBody(bytes.NewReader(bodyBytes)),
	)
	if err != nil {
		return fmt.Errorf("search: %w", err)
	}
	defer res.Body.Close()

	if res.IsError() {
		return fmt.Errorf("search error: %s", res.String())
	}

	var parsed searchResponse
	if err := json.NewDecoder(res.Body).Decode(&parsed); err != nil {
		return fmt.Errorf("decode search: %w", err)
	}

	scrollID := parsed.ScrollID
	if err := writeHits(parsed.Hits.Hits, csvWriter); err != nil {
		return err
	}

	for len(parsed.Hits.Hits) > 0 {
		res, err = es.Scroll(
			es.Scroll.WithContext(ctx),
			es.Scroll.WithScrollID(scrollID),
			es.Scroll.WithScroll(2*time.Minute),
		)
		if err != nil {
			return fmt.Errorf("scroll: %w", err)
		}

		if res.IsError() {
			res.Body.Close()
			return fmt.Errorf("scroll error: %s", res.String())
		}

		parsed = searchResponse{}
		if err := json.NewDecoder(res.Body).Decode(&parsed); err != nil {
			res.Body.Close()
			return fmt.Errorf("decode scroll: %w", err)
		}
		res.Body.Close()
		scrollID = parsed.ScrollID

		if err := writeHits(parsed.Hits.Hits, csvWriter); err != nil {
			return err
		}

		csvWriter.Flush()
	}

	if scrollID != "" {
		_, _ = es.ClearScroll(es.ClearScroll.WithScrollID(scrollID))
	}
	return nil
}

func buildSearchBody() map[string]any {
	return map[string]any{
		"query": map[string]any{
			"match_all": map[string]any{},
		},
		"_source": map[string]any{
			"includes": []string{
				"duration",
				"spanID",
				"traceID",
				"startTime",
				"references.spanID",
				"process.serviceName",
				"operationName",
			},
		},
		"sort": []string{"_doc"},
	}
}

func writeHits(hits []struct {
	Source map[string]any `json:"_source"`
}, csvWriter *csv.Writer) error {
	for _, hit := range hits {
		row := buildRow(hit.Source)
		if err := csvWriter.Write(row); err != nil {
			return fmt.Errorf("write row: %w", err)
		}
	}
	return nil
}

func csvHeader() []string {
	return []string{
		"trace_id",
		"span_id",
		"start_time",
		"end_time",
		"parent_span_id",
		"service_name",
		"name",
	}
}

func buildRow(source map[string]any) []string {
	return []string{
		stringify(source["traceID"]),
		stringify(source["spanID"]),
		stringifyInt(source["startTime"]),
		stringifyInt(startTimePlusDuration(source)),
		stringify(firstReferenceField(source, "spanID")),
		stringify(processServiceName(source)),
		stringify(source["operationName"]),
	}
}

func firstReferenceField(source map[string]any, key string) any {
	if refs := getSlice(source, "references"); len(refs) > 0 {
		if first, ok := refs[0].(map[string]any); ok {
			return first[key]
		}
	}
	return nil
}

func processServiceName(source map[string]any) any {
	if process := getMap(source, "process"); process != nil {
		return process["serviceName"]
	}
	return nil
}

func stringify(value any) string {
	if value == nil {
		return ""
	}
	switch cast := value.(type) {
	case string:
		return cast
	default:
		return fmt.Sprint(value)
	}
}

func stringifyInt(value any) string {
	if value == nil {
		return ""
	}
	switch cast := value.(type) {
	case int:
		return fmt.Sprintf("%d", cast)
	case int64:
		return fmt.Sprintf("%d", cast)
	case float64:
		return fmt.Sprintf("%d", int64(cast))
	case float32:
		return fmt.Sprintf("%d", int64(cast))
	case json.Number:
		if intVal, err := cast.Int64(); err == nil {
			return fmt.Sprintf("%d", intVal)
		}
		if floatVal, err := cast.Float64(); err == nil {
			return fmt.Sprintf("%d", int64(floatVal))
		}
	case string:
		return cast
	default:
		return fmt.Sprint(value)
	}
	return ""
}

func startTimePlusDuration(source map[string]any) any {
	startTime, okStart := toFloat(source["startTime"])
	duration, okDuration := toFloat(source["duration"])
	if !okStart || !okDuration {
		return source["startTime"]
	}
	return startTime + duration
}

func toFloat(value any) (float64, bool) {
	if value == nil {
		return 0, false
	}
	switch cast := value.(type) {
	case float64:
		return cast, true
	case float32:
		return float64(cast), true
	case int:
		return float64(cast), true
	case int64:
		return float64(cast), true
	case json.Number:
		floatVal, err := cast.Float64()
		if err != nil {
			return 0, false
		}
		return floatVal, true
	case string:
		floatVal, err := json.Number(cast).Float64()
		if err != nil {
			return 0, false
		}
		return floatVal, true
	default:
		return 0, false
	}
}

func getMap(src map[string]any, key string) map[string]any {
	if value, ok := src[key]; ok {
		if cast, ok := value.(map[string]any); ok {
			return cast
		}
	}
	return nil
}

func getSlice(src map[string]any, key string) []any {
	if value, ok := src[key]; ok {
		if cast, ok := value.([]any); ok {
			return cast
		}
	}
	return nil
}

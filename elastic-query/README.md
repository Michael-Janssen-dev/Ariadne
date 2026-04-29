# elastic-query

Export selected span fields from Elasticsearch indices whose names contain a substring (default: "span"). Output is CSV.

## Usage

```sh
cd /home/michaelj/Projects/Ariadne/elastic-query
go run . --es http://localhost:9200 --index-substring span --output spans.csv --page-size 1000
```

Write to stdout:

```sh
go run . --output -
```

## Output fields

The exporter writes these CSV columns in order:

- duration
- spanID
- traceID
- startTime
- references[0].spanID
- references[0].traceID
- process.serviceName
- operationName

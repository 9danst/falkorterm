# Local FalkorDB instance (official image).
# Build:  docker build -t falkorterm-db .
# Run:    docker run --rm -p 6379:6379 -p 3000:3000 falkorterm-db
# Or use: docker compose up -d

FROM falkordb/falkordb:latest

EXPOSE 6379 3000

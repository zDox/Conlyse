#!/bin/bash
# Test script to verify development environment setup
# This script checks that all infrastructure services are accessible

set -e

echo "============================================"
echo "ConflictInterface Development Environment Test"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0

test_service() {
    local name=$1
    local test_cmd=$2
    
    echo -n "Testing $name... "
    if eval "$test_cmd" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "Checking if development infrastructure is running..."
echo ""

# Test PostgreSQL
test_service "PostgreSQL connection" "docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -U converter"

# Test Redis
test_service "Redis connection" "docker compose -f docker-compose.dev.yml exec -T redis redis-cli ping | grep -q PONG"

# Test MinIO (using curl on host)
test_service "MinIO S3 API" "curl -f -s http://localhost:9000/minio/health/live"

# Test MinIO Console
test_service "MinIO Console" "curl -f -s http://localhost:9001 | grep -q minio"

# Additional checks
echo ""
echo "Additional Information:"
echo "----------------------"

# Check PostgreSQL version
echo -n "PostgreSQL version: "
docker compose -f docker-compose.dev.yml exec -T postgres psql -U converter -d replays -c "SELECT version();" 2>/dev/null | grep PostgreSQL | head -1 || echo "N/A"

# Check Redis version
echo -n "Redis version: "
docker compose -f docker-compose.dev.yml exec -T redis redis-cli INFO server 2>/dev/null | grep redis_version | cut -d: -f2 || echo "N/A"

# Check if MinIO bucket exists
echo -n "MinIO 'replays' bucket: "
if docker compose -f docker-compose.dev.yml exec -T minio sh -c "mc alias set myminio http://localhost:9000 minioadmin minioadmin >/dev/null 2>&1 && mc ls myminio/replays >/dev/null 2>&1"; then
    echo -e "${GREEN}exists${NC}"
else
    echo -e "${YELLOW}not found (run minio-init)${NC}"
fi

# Check local directories
echo ""
echo "Local Development Directories:"
echo "------------------------------"
for dir in "data/hot_storage" "data/recordings" "data/recordings/metadata"; do
    if [ -d "$dir" ]; then
        echo -e "$dir: ${GREEN}exists${NC}"
    else
        echo -e "$dir: ${YELLOW}missing (create with: mkdir -p $dir)${NC}"
    fi
done

# Summary
echo ""
echo "============================================"
echo "Summary:"
echo "  Passed: ${GREEN}$PASSED${NC}"
echo "  Failed: ${RED}$FAILED${NC}"
echo "============================================"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Your development environment is ready."
    echo "You can now run server-observer and server-converter locally."
    echo ""
    echo "Next steps:"
    echo "  1. Create data directories: mkdir -p data/{hot_storage,recordings}"
    echo "  2. Run converter: server-converter docker/local-dev/server-converter-config.json"
    echo "  3. Run observer: cd tools/server_observer/build && ./server_observer ..."
    echo ""
    echo "See DEVELOPMENT.md for detailed instructions."
    exit 0
else
    echo -e "${RED}✗ Some tests failed!${NC}"
    echo ""
    echo "Make sure the development infrastructure is running:"
    echo "  ./stack.sh start-dev"
    echo ""
    echo "Or manually:"
    echo "  docker compose -f docker-compose.dev.yml up -d"
    exit 1
fi

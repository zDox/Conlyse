#!/bin/bash
# ConflictInterface Docker Stack Management Script

set -e

COMPOSE_CMD="docker compose"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    cat << EOF
ConflictInterface Docker Stack Management

Usage: $0 [command]

Commands:
    start       Start all services
    stop        Stop all services
    restart     Restart all services
    status      Show service status
    logs        Show logs (tail -f)
    build       Rebuild all images
    clean       Stop and remove all containers, networks, and volumes (DATA LOSS!)
    reset       Stop services and remove volumes (DATA LOSS!)
    ps          List running containers
    
    # Specific service commands
    logs-observer       Show Server Observer logs
    logs-converter      Show Server Converter logs
    logs-postgres       Show PostgreSQL logs
    logs-redis          Show Redis logs
    logs-minio          Show MinIO logs
    
    restart-observer    Restart Server Observer
    restart-converter   Restart Server Converter
    
    # Utility commands
    shell-postgres      Open PostgreSQL shell
    shell-redis         Open Redis CLI
    minio-console       Open MinIO console (instructions)
    
    # Development
    build-observer      Rebuild Server Observer image
    build-converter     Rebuild Server Converter image

Examples:
    $0 start            # Start all services
    $0 logs-observer    # View Server Observer logs
    $0 status           # Check service health
EOF
}

check_env() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example${NC}"
        if [ -f .env.example ]; then
            cp .env.example .env
            echo -e "${GREEN}.env file created. Please review and update before starting.${NC}"
        else
            echo -e "${RED}Error: .env.example not found${NC}"
            exit 1
        fi
    fi
}

case "${1:-}" in
    start)
        check_env
        echo -e "${GREEN}Starting all services...${NC}"
        $COMPOSE_CMD up -d
        echo -e "${GREEN}Services started. Check status with: $0 status${NC}"
        ;;
    
    stop)
        echo -e "${YELLOW}Stopping all services...${NC}"
        $COMPOSE_CMD down
        echo -e "${GREEN}Services stopped${NC}"
        ;;
    
    restart)
        echo -e "${YELLOW}Restarting all services...${NC}"
        $COMPOSE_CMD restart
        echo -e "${GREEN}Services restarted${NC}"
        ;;
    
    status)
        $COMPOSE_CMD ps
        ;;
    
    logs)
        $COMPOSE_CMD logs -f
        ;;
    
    logs-observer)
        $COMPOSE_CMD logs -f server-observer
        ;;
    
    logs-converter)
        $COMPOSE_CMD logs -f server-converter
        ;;
    
    logs-postgres)
        $COMPOSE_CMD logs -f postgres
        ;;
    
    logs-redis)
        $COMPOSE_CMD logs -f redis
        ;;
    
    logs-minio)
        $COMPOSE_CMD logs -f minio
        ;;
    
    restart-observer)
        echo -e "${YELLOW}Restarting Server Observer...${NC}"
        $COMPOSE_CMD restart server-observer
        ;;
    
    restart-converter)
        echo -e "${YELLOW}Restarting Server Converter...${NC}"
        $COMPOSE_CMD restart server-converter
        ;;
    
    build)
        echo -e "${YELLOW}Rebuilding all images...${NC}"
        $COMPOSE_CMD build
        echo -e "${GREEN}Build complete${NC}"
        ;;
    
    build-observer)
        echo -e "${YELLOW}Rebuilding Server Observer...${NC}"
        $COMPOSE_CMD build server-observer
        ;;
    
    build-converter)
        echo -e "${YELLOW}Rebuilding Server Converter...${NC}"
        $COMPOSE_CMD build server-converter
        ;;
    
    clean)
        read -p "This will remove all containers, networks, and volumes. Are you sure? (yes/no) " -r
        if [[ $REPLY == "yes" ]]; then
            echo -e "${RED}Cleaning up everything...${NC}"
            $COMPOSE_CMD down -v
            echo -e "${GREEN}Cleanup complete${NC}"
        else
            echo -e "${YELLOW}Cancelled${NC}"
        fi
        ;;
    
    reset)
        read -p "This will stop services and remove all data volumes. Are you sure? (yes/no) " -r
        if [[ $REPLY == "yes" ]]; then
            echo -e "${RED}Resetting stack...${NC}"
            $COMPOSE_CMD down -v
            echo -e "${GREEN}Reset complete. Run '$0 start' to restart${NC}"
        else
            echo -e "${YELLOW}Cancelled${NC}"
        fi
        ;;
    
    ps)
        $COMPOSE_CMD ps -a
        ;;
    
    shell-postgres)
        echo -e "${GREEN}Opening PostgreSQL shell...${NC}"
        $COMPOSE_CMD exec postgres psql -U converter -d replays
        ;;
    
    shell-redis)
        echo -e "${GREEN}Opening Redis CLI...${NC}"
        $COMPOSE_CMD exec redis redis-cli
        ;;
    
    minio-console)
        echo -e "${GREEN}MinIO Console is available at:${NC}"
        echo -e "  URL: ${YELLOW}http://localhost:9001${NC}"
        echo -e "  Username: ${YELLOW}minioadmin${NC} (or value from .env)"
        echo -e "  Password: ${YELLOW}minioadmin${NC} (or value from .env)"
        ;;
    
    help|--help|-h|"")
        print_usage
        ;;
    
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        print_usage
        exit 1
        ;;
esac

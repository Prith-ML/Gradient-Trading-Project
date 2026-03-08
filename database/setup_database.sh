#!/bin/bash
# setup_database.sh - Initialize PostgreSQL database for Twitter data ingestion

set -e

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-twitter_data}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Twitter Data Database Setup ===${NC}\n"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${RED}PostgreSQL is not installed. Please install PostgreSQL first.${NC}"
    exit 1
fi

# Create database if it doesn't exist
echo -e "${BLUE}Creating database: $DB_NAME${NC}"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -c "CREATE DATABASE $DB_NAME"

echo -e "${GREEN}✓ Database created or already exists${NC}\n"

# Create schema
echo -e "${BLUE}Creating database schema...${NC}"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -d $DB_NAME -U $DB_USER -f "$(dirname "$0")/twitter_schema.sql"

echo -e "${GREEN}✓ Schema created successfully${NC}\n"

# Create extensions
echo -e "${BLUE}Installing PostgreSQL extensions...${NC}"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -d $DB_NAME -U $DB_USER << EOF
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
EOF

echo -e "${GREEN}✓ Extensions installed${NC}\n"

# Show summary
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo -e "\nDatabase Details:"
echo -e "  Host: ${BLUE}$DB_HOST${NC}"
echo -e "  Port: ${BLUE}$DB_PORT${NC}"
echo -e "  Database: ${BLUE}$DB_NAME${NC}"
echo -e "  User: ${BLUE}$DB_USER${NC}"
echo -e "\nConnection String:"
echo -e "  ${BLUE}postgresql://$DB_USER:***@$DB_HOST:$DB_PORT/$DB_NAME${NC}"
echo -e "\nNext steps:"
echo -e "  1. Update your . env file with connection credentials"
echo -e "  2. Install Python ETL dependencies: pip install psycopg2 tweepy"
echo -e "  3. Configure Twitter API credentials"
echo -e "  4. Run data ingestion pipeline"

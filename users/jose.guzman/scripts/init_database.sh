#!/bin/bash

# Initialize database environment for VS Code Insiders Extensions

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${GREEN}Initializing database environment...${NC}"

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}Creating .env file from template...${NC}"
        cp .env.example .env
        echo -e "${GREEN}Created .env file. Please update it with your database credentials.${NC}"
    else
        echo -e "${RED}Error: .env.example file not found${NC}"
        exit 1
    fi
fi

# Check for required dependencies
echo -e "${GREEN}Checking dependencies...${NC}"

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Node.js is required but not installed. Please install Node.js first.${NC}"
    exit 1
fi

# Check for npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}npm is required but not installed. Please install npm first.${NC}"
    exit 1
fi

# Initialize package.json if it doesn't exist
if [ ! -f package.json ]; then
    echo -e "${YELLOW}Initializing npm project...${NC}"
    npm init -y
fi

# Install Prisma dependencies
echo -e "${GREEN}Installing Prisma dependencies...${NC}"
npm install --save-dev prisma
npm install @prisma/client @prisma/extension-accelerate

# Check if schema.prisma exists
if [ ! -f schema.prisma ]; then
    echo -e "${YELLOW}Copying Prisma schema...${NC}"
    # Copy the pre-defined schema.prisma if it exists in the project
    if [ -f "${PROJECT_ROOT}/schema.prisma" ]; then
        cp "${PROJECT_ROOT}/schema.prisma" ./schema.prisma
    else
        echo -e "${RED}Error: schema.prisma template not found${NC}"
        exit 1
    fi
fi

# Generate Prisma Client
echo -e "${GREEN}Generating Prisma Client...${NC}"
npx prisma generate --no-engine

echo -e "\n${GREEN}Database environment initialization complete!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Update your .env file with your database credentials"
echo "2. Run 'npx prisma migrate dev' to create the database schema"
echo "3. See docs/database_setup.md for more detailed instructions"

# Add helpful warning about security
echo -e "\n${YELLOW}Security Reminder:${NC}"
echo "- Never commit your .env file to version control"
echo "- Keep your database credentials secure"
echo "- Regularly rotate your API keys and passwords"


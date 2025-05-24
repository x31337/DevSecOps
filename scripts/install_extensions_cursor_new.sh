#!/bin/bash
# Script to install VSCode extensions directly into Cursor IDE's extension directory

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Set paths
CURSOR_EXTENSIONS_DIR="${HOME}/.cursor/extensions"
EXTENSIONS_JSON="${CURSOR_EXTENSIONS_DIR}/extensions.json"
SOURCE_EXTENSIONS_DIR="./extensions"

# Create extensions directory if it doesn't exist
if [ ! -d "$CURSOR_EXTENSIONS_DIR" ]; then
  echo -e "${YELLOW}Creating Cursor extensions directory at ${CURSOR_EXTENSIONS_DIR}${NC}"
  mkdir -p "$CURSOR_EXTENSIONS_DIR"
fi

# Create a backup of extensions.json if it exists
if [ -f "$EXTENSIONS_JSON" ]; then
  BACKUP_FILE="${EXTENSIONS_JSON}.backup.$(date +%Y%m%d%H%M%S)"
  cp "$EXTENSIONS_JSON" "$BACKUP_FILE"
  echo -e "${GREEN}Created backup of extensions.json at ${BACKUP_FILE}${NC}"
else
  # Create an empty extensions.json file
  echo -e "${YELLOW}Creating new extensions.json file${NC}"
  echo '{"extensions":[]}' > "$EXTENSIONS_JSON"
fi

# Create log file
LOG_FILE="cursor_extension_install_$(date +%Y%m%d_%H%M%S).log"
touch "$LOG_FILE"

# Check if source extensions directory exists
if [ ! -d "$SOURCE_EXTENSIONS_DIR" ]; then
  echo -e "${RED}Error: Source extensions directory ${SOURCE_EXTENSIONS_DIR} not found!${NC}"
  exit 1
fi

# Count total extensions in our directory
TOTAL_EXTENSIONS=$(ls -1 ${SOURCE_EXTENSIONS_DIR}/*.vsix 2>/dev/null | wc -l)
if [ "$TOTAL_EXTENSIONS" -eq 0 ]; then
  echo -e "${RED}Error: No .vsix files found in the source extensions directory!${NC}"
  exit 1
fi

echo -e "${GREEN}Found ${TOTAL_EXTENSIONS} extensions in the source directory${NC}"

# Function to extract extension ID and version from filename
parse_extension_filename() {
  local filename="$1"
  local basename=$(basename "$filename" .vsix)
  local id=""
  local version=""
  
  # Try to match different naming patterns
  if [[ "$basename" =~ ^([^@]+)@([0-9]+\.[0-9]+\.[0-9]+.*)$ ]]; then
    # Pattern: publisher.name@version.vsix (e.g., ms-python.python@2023.6.1.vsix)
    id="${BASH_REMATCH[1]}"
    version="${BASH_REMATCH[2]}"
  elif [[ "$basename" =~ ^([^-]+)-([0-9]+\.[0-9]+\.[0-9]+.*)$ ]]; then
    # Pattern: publisher.name-version.vsix (e.g., GitHub.vscode-codeql-1.17.2.vsix)
    id="${BASH_REMATCH[1]}"
    version="${BASH_REMATCH[2]}"
  else
    # If we can't parse, use the basename as ID and set version to 1.0.0
    id="$basename"
    version="1.0.0"
  fi
  
  echo "$id:$version"
}

# Get currently installed extensions
echo -e "${BLUE}Checking currently installed extensions...${NC}"
INSTALLED_EXTENSIONS=()

# Read extensions.json to find installed extensions
if [ -f "$EXTENSIONS_JSON" ]; then
  while IFS= read -r line; do
    if [[ "$line" =~ \"id\":\"([^\"]+)\" ]]; then
      id="${BASH_REMATCH[1]}"
      if [[ "$line" =~ \"version\":\"([^\"]+)\" ]]; then
        version="${BASH_REMATCH[1]}"
        INSTALLED_EXTENSIONS+=("$id:$version")
        echo -e "  ${CYAN}Found installed: $id ($version)${NC}"
      fi
    fi
  done < <(grep -o '"id":"[^"]*"' "$EXTENSIONS_JSON" | grep -o '"version":"[^"]*"')
fi

echo -e "${GREEN}Found ${#INSTALLED_EXTENSIONS[@]} extensions currently installed${NC}"

# Plan which extensions to install
EXTENSIONS_TO_INSTALL=()
EXTENSIONS_TO_SKIP=()

echo -e "\n${BLUE}Analyzing extensions to install...${NC}"
for ext_file in ${SOURCE_EXTENSIONS_DIR}/*.vsix; do
  ext_info=$(parse_extension_filename "$ext_file")
  ext_id="${ext_info%%:*}"
  ext_version="${ext_info#*:}"
  
  # Check if already installed
  ALREADY_INSTALLED=false
  NEEDS_UPDATE=false
  
  for installed_ext in "${INSTALLED_EXTENSIONS[@]}"; do
    installed_id="${installed_ext%%:*}"
    installed_version="${installed_ext#*:}"
    
    # Check if extension ID matches (case insensitive)
    if [[ "${installed_id,,}" == "${ext_id,,}" ]]; then
      ALREADY_INSTALLED=true
      
      # Compare versions
      if [[ "$ext_version" != "$installed_version" ]]; then
        # Simple version comparison
        if [[ "$ext_version" > "$installed_version" ]]; then
          NEEDS_UPDATE=true
          echo -e "  ${YELLOW}Update available: $ext_id ($installed_version → $ext_version)${NC}"
        fi
      fi
      
      break
    fi
  done
  
  if [[ "$ALREADY_INSTALLED" == true && "$NEEDS_UPDATE" == false ]]; then
    EXTENSIONS_TO_SKIP+=("$ext_file:$ext_id:$ext_version")
    echo -e "  ${GREEN}Skip: $ext_id (already installed)${NC}"
  else
    EXTENSIONS_TO_INSTALL+=("$ext_file:$ext_id:$ext_version")
    if [[ "$ALREADY_INSTALLED" == true ]]; then
      echo -e "  ${YELLOW}Update: $ext_id ($ext_version)${NC}"
    else
      echo -e "  ${BLUE}New: $ext_id ($ext_version)${NC}"
    fi
  fi
done

echo -e "\n${GREEN}Installation plan:${NC}"
echo -e "  ${GREEN}Total extensions in source: $TOTAL_EXTENSIONS${NC}"
echo -e "  ${GREEN}Currently installed: ${#INSTALLED_EXTENSIONS[@]}${NC}"
echo -e "  ${YELLOW}To be installed/updated: ${#EXTENSIONS_TO_INSTALL[@]}${NC}"
echo -e "  ${BLUE}To be skipped: ${#EXTENSIONS_TO_SKIP[@]}${NC}"

# If nothing to install, exit
if [ "${#EXTENSIONS_TO_INSTALL[@]}" -eq 0 ]; then
  echo -e "\n${GREEN}All extensions are already installed and up to date!${NC}"
  exit 0
fi

# Ask for confirmation
echo -e "\n${YELLOW}Do you want to proceed with installation? (y/n)${NC}"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
  echo -e "${YELLOW}Installation cancelled.${NC}"
  exit 0
fi

# Prepare extensions.json - read current content
EXTENSIONS_JSON_CONTENT=$(cat "$EXTENSIONS_JSON")

# Function to update extensions.json
update_extensions_json() {
  local id="$1"
  local version="$2"
  local extension_dir="$3"
  
  # Create a simplified entry for the extension
  local new_entry="{\"identifier\":{\"id\":\"$id\"},\"version\":\"$version\",\"location\":{\"$extension_dir\":true}}"
  
  # Check if extension is already in the JSON
  if grep -q "\"id\":\"$id\"" "$EXTENSIONS_JSON"; then
    # Remove the existing entry
    TEMP_JSON=$(grep -v "\"id\":\"$id\"" "$EXTENSIONS_JSON")
    # Add the new entry
    echo "$TEMP_JSON" | sed "s|\"extensions\":\[|\"extensions\":[$new_entry,|" > "$EXTENSIONS_JSON"
  else
    # Add the new entry
    sed -i "s|\"extensions\":\[|\"extensions\":[$new_entry,|" "$EXTENSIONS_JSON"
  fi
  
  # Fix JSON format if needed (replace empty array with proper closing)
  sed -i 's/\[\]/\[\]/g' "$EXTENSIONS_JSON"
  # Fix trailing comma if it's the only entry
  sed -i 's/,\]/]/g' "$EXTENSIONS_JSON"
}

# Initialize counters
INSTALLED=0
FAILED=0

# Install extensions
echo -e "\n${GREEN}Starting installation...${NC}"
for ext_entry in "${EXTENSIONS_TO_INSTALL[@]}"; do
  # Parse the extension entry
  ext_file="${ext_entry%%:*}"
  remaining="${ext_entry#*:}"
  ext_id="${remaining%%:*}"
  ext_version="${remaining#*:}"
  
  ext_filename=$(basename "$ext_file")
  
  echo -e "\n${YELLOW}Installing ($((INSTALLED+FAILED+1))/${#EXTENSIONS_TO_INSTALL[@]}): $ext_id ($ext_version)${NC}"
  echo -e "  ${BLUE}File: $ext_filename${NC}"
  
  # Create target directory with format extension_id-version
  ext_target_dir="$CURSOR_EXTENSIONS_DIR/$ext_id-$ext_version"
  
  # Check if directory already exists
  if [ -d "$ext_target_dir" ]; then
    echo -e "  ${YELLOW}Removing existing directory...${NC}"
    rm -rf "$ext_target_dir"
  fi
  
  # Create the directory and copy the .vsix file
  mkdir -p "$ext_target_dir"
  
  # Copy the entire .vsix file to the extension directory
  echo -e "  ${BLUE}Copying extension...${NC}" | tee -a "$LOG_FILE"
  cp "$ext_file" "$ext_target_dir/extension.vsix" 2>&1 | tee -a "$LOG_FILE"
  
  # Create minimal package.json if it doesn't exist
  if [ ! -f "$ext_target_dir/package.json" ]; then
    echo -e "  ${BLUE}Creating minimal package.json...${NC}" | tee -a "$LOG_FILE"
    echo "{\"name\":\"$ext_id\",\"version\":\"$ext_version\",\"engines\":{\"vscode\":\"^1.70.0\"}}" > "$ext_target_dir/package.json"
  fi
  
  # Update extensions.json
  echo -e "  ${BLUE}Updating extensions registry...${NC}" | tee -a "$LOG_FILE"
  update_extensions_json "$ext_id" "$ext_version" "$ext_target_dir"
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully installed: $ext_id${NC}" | tee -a "$LOG_FILE"
    ((INSTALLED++))
  else
    echo -e "${RED}✗ Failed to install: $ext_id${NC}" | tee -a "$LOG_FILE"
    ((FAILED++))
  fi
  
  # Add a small delay
  sleep 0.5
done

# Fix extensions.json format (remove trailing commas)
sed -i 's/,]/]/g' "$EXTENSIONS_JSON"

# Print summary
echo -e "\n${GREEN}===== Installation Summary =====${NC}"
echo -e "${GREEN}Total extensions to install/update: ${#EXTENSIONS_TO_INSTALL[@]}${NC}"
echo -e "${GREEN}Successfully installed: ${INSTALLED}${NC}"
if [ "$FAILED" -gt 0 ]; then
  echo -e "${RED}Failed to install: ${FAILED}${NC}"
  echo -e "${YELLOW}Check ${LOG_FILE} for details on failures${NC}"
else
  echo -e "${GREEN}All selected extensions installed successfully!${NC}"
fi

echo -e "\n${GREEN}Installation log saved to: ${LOG_FILE}${NC}"

# Final note about skipped extensions
if [ "${#EXTENSIONS_TO_SKIP[@]}" -gt 0 ]; then
  echo -e "\n${BLUE}Note: ${#EXTENSIONS_TO_SKIP[@]} extensions were skipped as they are already installed${NC}"
fi

echo -e "\n${GREEN}Installation complete. Please restart Cursor IDE to activate the extensions.${NC}"


#!/bin/bash
# Script to install missing or newer VSCode extensions into Cursor IDE by direct extraction

# Define colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Set Cursor AppImage path and extensions directory
CURSOR_BIN="${HOME}/Applications/Cursor.AppImage"
CURSOR_EXTENSIONS_DIR="${HOME}/.cursor/extensions"
CURSOR_EXTENSIONS_JSON="$CURSOR_EXTENSIONS_DIR/extensions.json"
TEMP_DIR="/tmp/cursor_extensions_temp"

# Check dependencies
check_dependencies() {
  local missing_deps=()
  
  if ! command -v unzip &> /dev/null; then
    missing_deps+=("unzip")
  fi
  
  if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq not found. Will use basic JSON parsing.${NC}"
  fi
  
  if [ ${#missing_deps[@]} -gt 0 ]; then
    echo -e "${RED}Error: Missing dependencies: ${missing_deps[*]}${NC}"
    echo "Please install the required dependencies and try again."
    echo "On Ubuntu/Debian: sudo apt-get install ${missing_deps[*]}"
    exit 1
  fi
}

# Check if Cursor AppImage exists and is executable
if [ ! -x "$CURSOR_BIN" ]; then
  echo -e "${RED}Error: Cursor AppImage not found at ${CURSOR_BIN} or is not executable.${NC}"
  echo "Please make sure Cursor is installed and the path is correct."
  exit 1
fi

echo -e "${GREEN}Using Cursor AppImage at: ${CURSOR_BIN}${NC}"

# Check if extensions directory exists
if [ ! -d "extensions" ]; then
  echo -e "${RED}Error: extensions directory not found!${NC}"
  echo "Please run this script from the directory containing the 'extensions' folder."
  exit 1
fi

# Check if Cursor extensions directory exists
if [ ! -d "$CURSOR_EXTENSIONS_DIR" ]; then
  echo -e "${YELLOW}Warning: Cursor extensions directory not found at ${CURSOR_EXTENSIONS_DIR}${NC}"
  echo -e "${YELLOW}Creating extensions directory...${NC}"
  mkdir -p "$CURSOR_EXTENSIONS_DIR"
fi

# Create extensions.json if it doesn't exist
if [ ! -f "$CURSOR_EXTENSIONS_JSON" ]; then
  echo -e "${YELLOW}Creating extensions.json file...${NC}"
  echo '{"extensions":[]}' > "$CURSOR_EXTENSIONS_JSON"
fi

# Make backup of extensions.json
cp "$CURSOR_EXTENSIONS_JSON" "${CURSOR_EXTENSIONS_JSON}.backup"
echo -e "${GREEN}Created backup of extensions.json at ${CURSOR_EXTENSIONS_JSON}.backup${NC}"

# Count total extensions in our directory
TOTAL_EXTENSIONS=$(ls -1 extensions/*.vsix 2>/dev/null | wc -l)
if [ "$TOTAL_EXTENSIONS" -eq 0 ]; then
  echo -e "${RED}Error: No .vsix files found in the extensions directory!${NC}"
  exit 1
fi

echo -e "${GREEN}Found ${TOTAL_EXTENSIONS} extensions in the source directory${NC}"

# Create log file
LOG_FILE="cursor_extension_install_$(date +%Y%m%d_%H%M%S).log"
touch "$LOG_FILE"

# Check dependencies
check_dependencies

# Clean up temp directory if it exists
rm -rf "$TEMP_DIR" 2>/dev/null
mkdir -p "$TEMP_DIR"

# Function to extract extension info from a VSIX file
extract_extension_info() {
  local vsix_file="$1"
  local temp_extract_dir="$2"
  
  # Extract VSIX (it's just a ZIP file)
  unzip -q "$vsix_file" -d "$temp_extract_dir"
  
  # Check if package.json exists
  if [ ! -f "$temp_extract_dir/extension/package.json" ]; then
    echo "ERROR:Could not find package.json in VSIX"
    return 1
  fi
  
  # Extract name, publisher, and version from package.json
  local name=""
  local publisher=""
  local version=""
  local display_name=""
  
  if command -v jq &> /dev/null; then
    # Use jq if available
    name=$(jq -r '.name // ""' "$temp_extract_dir/extension/package.json")
    publisher=$(jq -r '.publisher // ""' "$temp_extract_dir/extension/package.json")
    version=$(jq -r '.version // ""' "$temp_extract_dir/extension/package.json")
    display_name=$(jq -r '."displayName" // ""' "$temp_extract_dir/extension/package.json")
  else
    # Fallback to grep/sed
    name=$(grep -o '"name":[^,]*' "$temp_extract_dir/extension/package.json" | head -1 | sed 's/"name"://;s/"//g;s/^ *//;s/ *$//')
    publisher=$(grep -o '"publisher":[^,]*' "$temp_extract_dir/extension/package.json" | head -1 | sed 's/"publisher"://;s/"//g;s/^ *//;s/ *$//')
    version=$(grep -o '"version":[^,]*' "$temp_extract_dir/extension/package.json" | head -1 | sed 's/"version"://;s/"//g;s/^ *//;s/ *$//')
    display_name=$(grep -o '"displayName":[^,]*' "$temp_extract_dir/extension/package.json" | head -1 | sed 's/"displayName"://;s/"//g;s/^ *//;s/ *$//')
  fi
  
  if [ -z "$name" ] || [ -z "$publisher" ] || [ -z "$version" ]; then
    echo "ERROR:Could not extract extension info from package.json"
    return 1
  fi
  
  # Construct extension ID
  local extension_id="${publisher}.${name}"
  echo "$extension_id:$version:$display_name"
}

# Get current installed extensions
echo -e "${BLUE}Analyzing currently installed extensions...${NC}"
INSTALLED_EXTENSIONS=()

# Parse extensions.json for currently installed extensions
if command -v jq &> /dev/null; then
  # Use jq if available
  while IFS= read -r line; do
    if [ ! -z "$line" ]; then
      INSTALLED_EXTENSIONS+=("$line")
      echo -e "  ${CYAN}Found: $line${NC}"
    fi
  done < <(jq -r '.extensions[] | "\(.identifier.id):\(.version)"' "$CURSOR_EXTENSIONS_JSON" 2>/dev/null)
else
  # Basic parsing fallback
  while IFS= read -r line; do
    if [[ $line =~ \"id\":\"([^\"]+)\" ]]; then
      id="${BASH_REMATCH[1]}"
      if [[ $line =~ \"version\":\"([^\"]+)\" ]]; then
        version="${BASH_REMATCH[1]}"
        INSTALLED_EXTENSIONS+=("$id:$version")
        echo -e "  ${CYAN}Found: $id ($version)${NC}"
      fi
    fi
  done < <(grep -o '"identifier":{[^}]*}' "$CURSOR_EXTENSIONS_JSON" | grep -o '"id":"[^"]*"' | grep -o '"version":"[^"]*"')
fi

echo -e "${GREEN}Found ${#INSTALLED_EXTENSIONS[@]} extensions in extensions.json${NC}"

# Build a list of extensions to install
EXTENSIONS_TO_INSTALL=()
EXTENSIONS_TO_SKIP=()

echo -e "\n${BLUE}Analyzing extensions in source directory...${NC}"
for ext_file in extensions/*.vsix; do
  # Create temp dir for this extension
  ext_temp_dir="$TEMP_DIR/$(basename "$ext_file" .vsix)"
  mkdir -p "$ext_temp_dir"
  
  # Extract and get extension info
  ext_info=$(extract_extension_info "$ext_file" "$ext_temp_dir")
  
  if [[ "$ext_info" == ERROR:* ]]; then
    echo -e "  ${RED}Error processing $(basename "$ext_file"): ${ext_info#ERROR:}${NC}"
    continue
  fi
  
  ext_id="${ext_info%%:*}"
  remaining="${ext_info#*:}"
  ext_version="${remaining%%:*}"
  ext_display_name="${remaining#*:}"
  
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
        # Simple version comparison - this could be improved
        if [[ "$ext_version" > "$installed_version" ]]; then
          NEEDS_UPDATE=true
          echo -e "  ${YELLOW}Update available: $ext_id ($installed_version → $ext_version)${NC}"
        fi
      fi
      
      break
    fi
  done
  
  if [[ "$ALREADY_INSTALLED" == true && "$NEEDS_UPDATE" == false ]]; then
    EXTENSIONS_TO_SKIP+=("$ext_file:$ext_id:$ext_version:$ext_display_name:$ext_temp_dir")
    echo -e "  ${GREEN}Skip: $ext_id (already installed)${NC}"
  else
    EXTENSIONS_TO_INSTALL+=("$ext_file:$ext_id:$ext_version:$ext_display_name:$ext_temp_dir")
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
  # Clean up
  rm -rf "$TEMP_DIR"
  exit 0
fi

# Ask for confirmation
echo -e "\n${YELLOW}Do you want to proceed with installation? (y/n)${NC}"
read -r response
if [[ ! "$response" =~ ^[Yy]$ ]]; then
  echo -e "${YELLOW}Installation cancelled.${NC}"
  # Clean up
  rm -rf "$TEMP_DIR"
  exit 0
fi

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
  remaining="${remaining#*:}"
  ext_version="${remaining%%:*}"
  remaining="${remaining#*:}"
  ext_display_name="${remaining%%:*}"
  ext_temp_dir="${remaining#*:}"
  
  ext_filename=$(basename "$ext_file")
  
  echo -e "\n${YELLOW}Installing ($((INSTALLED+FAILED+1))/${#EXTENSIONS_TO_INSTALL[@]}): $ext_id ($ext_version)${NC}"
  echo -e "  ${BLUE}File: $ext_filename${NC}"
  
  # Create target directory
  ext_target_dir="$CURSOR_EXTENSIONS_DIR/$ext_id-$ext_version"
  
  # Check if directory already exists
  if [ -d "$ext_target_dir" ]; then
    echo -e "  ${YELLOW}Directory exists, removing...${NC}"
    rm -rf "$ext_target_dir"
  fi
  
  # Create directory
  mkdir -p "$ext_target_dir"
  
  # Copy extension files
  echo -e "  ${BLUE}Copying extension files...${NC}" | tee -a "$LOG_FILE"
  cp -r "$ext_temp_dir/extension/"* "$ext_target_dir/" 2>&1 | tee -a "$LOG_FILE"
  
  # Update extensions.json
  echo -e "  ${BLUE}Updating extensions registry...${NC}" | tee -a "$LOG_FILE"
  
  # Create new extension entry
  local ext_json_entry="{\"identifier\":{\"id\":\"$ext_id\"},\"version\":\"$ext_version\",\"location\":{\"$ext_target_dir\":true}}"
  
  # Update extensions.json
  if command -v jq &> /dev/null; then
    # Use jq if available
    # Remove existing extension entry if present
    jq --arg id "$ext_id" '.extensions = [.extensions[] | select(.identifier.id != $id)]' "$CURSOR_EXTENSIONS_JSON" > "${CURSOR_EXTENSIONS_JSON}.tmp"
    
    # Add new extension entry
    jq --argjson new "$ext_json_entry" '.extensions += [$new]' "${CURSOR_EXTENSIONS_JSON}.tmp" > "$CURSOR_EXTENSIONS_JSON"
    rm "${CURSOR_EXTENSIONS_JSON}.tmp"
  else
    # Basic approach without jq
    # This is a simplified approach that might not handle all edge cases
    if grep -q "\"id\":\"$ext_id\"" "$CURSOR_EXTENSIONS_JSON"; then
      # Extension exists, update it (this is a very basic implementation)
      sed -i "s|{\"identifier\":{\"id\":\"$ext_id\"},[^}]*}|$ext_json_entry|g" "$CURSOR_EXTENSIONS_JSON"
    else
      # Add new extension
      sed -i "s|\"extensions\":\[|\"extensions\":\[$ext_json_entry,|" "$CURSOR_EXTENSIONS_JSON"
    fi
  fi
  
  if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Successfully installed: $ext_id${NC}" | tee -a "$LOG_FILE"
    ((INSTALLED++))
  else
    echo -e "${RED}✗ Failed to install: $ext_id${NC}" | tee -a "$LOG_FILE"
    ((FAILED++))
  fi
  
  # Add a small delay to prevent overwhelming the system
  sleep 0.5
done

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

# Clean up
echo -e "\n${BLUE}Cleaning up temporary files...${NC}"
rm -rf "$TEMP_DIR"

echo -e "\n${GREEN}Installation complete. Please restart Cursor IDE to activate the extensions.${NC}"


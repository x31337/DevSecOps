#!/bin/bash
# =====================================================================
# Cursor IDE Extension Installer
# =====================================================================
# A comprehensive script to install VS Code extensions into Cursor IDE
# This script combines direct file operations with metadata management
# to ensure proper extension installation and registration.
# 
# Author: x31337
# Repository: https://github.com/x31337/DevSecOps
# =====================================================================

# ANSI color codes for better visual feedback
BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Default settings
SOURCE_EXTENSIONS_DIR="../extensions"
INSTALL_ALL=true
AUTO_YES=false
QUIET=false
VERBOSE=false
DEBUG=false
MAX_PARALLEL=4
DRY_RUN=false

# Function to print the script banner
print_banner() {
    echo -e "${BOLD}┌───────────────────────────────────────────┐${NC}"
    echo -e "${BOLD}│      Cursor IDE Extension Installer       │${NC}"
    echo -e "${BOLD}│                                           │${NC}"
    echo -e "${BOLD}│      For https://cursor.sh IDE            │${NC}"
    echo -e "${BOLD}└───────────────────────────────────────────┘${NC}"
    echo ""
}

# Function to print usage information
print_usage() {
    echo -e "${BOLD}Usage:${NC} $0 [options]"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  -h, --help             Show this help message and exit"
    echo "  -p, --path PATH        Specify Cursor installation path"
    echo "  -s, --source DIR       Specify source extensions directory (default: ${SOURCE_EXTENSIONS_DIR})"
    echo "  -e, --extensions LIST  Comma-separated list of extensions to install (default: all)"
    echo "  -y, --yes              Auto-confirm all prompts"
    echo "  -q, --quiet            Minimal output mode"
    echo "  -v, --verbose          Verbose output mode"
    echo "  -d, --debug            Debug mode with extra information"
    echo "  --dry-run              Simulate installation without making changes"
    echo "  --parallel NUM         Maximum parallel operations (default: ${MAX_PARALLEL})"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  $0 --path ~/Applications/Cursor.AppImage"
    echo "  $0 --source ./my-extensions --extensions github.copilot,ms-python.python"
    echo "  $0 --yes --quiet"
    echo ""
}

# Function to log messages with different levels
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    case "$level" in
        "INFO")
            [ "$QUIET" = false ] && echo -e "${GRAY}[${timestamp}]${NC} ${BLUE}INFO:${NC} $message"
            ;;
        "SUCCESS")
            [ "$QUIET" = false ] && echo -e "${GRAY}[${timestamp}]${NC} ${GREEN}SUCCESS:${NC} $message"
            ;;
        "WARN")
            [ "$QUIET" = false ] && echo -e "${GRAY}[${timestamp}]${NC} ${YELLOW}WARNING:${NC} $message"
            ;;
        "ERROR")
            echo -e "${GRAY}[${timestamp}]${NC} ${RED}ERROR:${NC} $message" >&2
            ;;
        "DEBUG")
            [ "$DEBUG" = true ] && echo -e "${GRAY}[${timestamp}]${NC} ${CYAN}DEBUG:${NC} $message"
            ;;
        "VERBOSE")
            [ "$VERBOSE" = true ] && echo -e "${GRAY}[${timestamp}]${NC} ${GRAY}VERBOSE:${NC} $message"
            ;;
    esac
    
    # Also write to log file
    echo "[${timestamp}] ${level}: $message" >> "$LOG_FILE"
}

# Function to check dependencies
check_dependencies() {
    log "INFO" "Checking dependencies..."
    local missing_deps=()
    
    for dep in "$@"; do
        if ! command -v "$dep" &> /dev/null; then
            missing_deps+=("$dep")
            log "WARN" "Missing dependency: $dep"
        else
            log "DEBUG" "Found dependency: $dep"
        fi
    done
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log "ERROR" "Missing dependencies: ${missing_deps[*]}"
        echo ""
        echo -e "${YELLOW}Please install the required dependencies and try again:${NC}"
        echo "  Ubuntu/Debian: sudo apt-get install ${missing_deps[*]}"
        echo "  macOS: brew install ${missing_deps[*]}"
        echo ""
        return 1
    fi
    
    return 0
}

# Function to extract the VSIX file using the proper format
extract_vsix() {
    local vsix_file="$1"
    local target_dir="$2"
    local temp_dir="$3"
    
    log "DEBUG" "Extracting VSIX file: $vsix_file"
    log "DEBUG" "Target directory: $target_dir"
    log "DEBUG" "Temp directory: $temp_dir"
    
    # Create temp directory if it doesn't exist
    mkdir -p "$temp_dir"
    
    # VSIX files are ZIP files, extract them to the temp directory
    log "VERBOSE" "Extracting VSIX contents to temp directory..."
    if ! unzip -q "$vsix_file" -d "$temp_dir"; then
        log "ERROR" "Failed to extract VSIX file: $vsix_file"
        return 1
    fi
    
    # Create target directory
    mkdir -p "$target_dir"
    
    # Check if extension/ directory exists in the temp dir
    if [ -d "$temp_dir/extension" ]; then
        # Move contents from the extension/ directory to the target
        log "VERBOSE" "Moving extension contents to target directory..."
        cp -r "$temp_dir/extension/"* "$target_dir/"
    else
        # Move all contents to the target
        log "VERBOSE" "Moving all contents to target directory..."
        cp -r "$temp_dir/"* "$target_dir/"
    fi
    
    # Check if we have a package.json file
    if [ ! -f "$target_dir/package.json" ]; then
        log "WARN" "No package.json found in the VSIX file, creating minimal one..."
        # Extract information from the filename or .vsixmanifest if available
        local extension_id=$(basename "$vsix_file" .vsix | sed -E 's/(@|-)([0-9]+\.[0-9]+\.[0-9]+.*)//')
        local version=$(basename "$vsix_file" .vsix | grep -oE '([0-9]+\.[0-9]+\.[0-9]+.*)' || echo "1.0.0")
        
        # Create minimal package.json
        echo "{\"name\":\"$extension_id\",\"version\":\"$version\",\"engines\":{\"vscode\":\"^1.70.0\"}}" > "$target_dir/package.json"
    fi
    
    # Check if we have an extension.vsixmanifest file
    if [ -f "$temp_dir/extension.vsixmanifest" ]; then
        log "VERBOSE" "Found extension.vsixmanifest, copying to target..."
        cp "$temp_dir/extension.vsixmanifest" "$target_dir/.vsixmanifest"
    fi
    
    # Create the .vsixmanifest file if it doesn't exist
    if [ ! -f "$target_dir/.vsixmanifest" ]; then
        log "WARN" "No .vsixmanifest found, creating from package.json..."
        # Extract info from package.json
        if [ -f "$target_dir/package.json" ]; then
            local pkg_name=$(grep -o '"name":[^,]*' "$target_dir/package.json" | head -1 | sed 's/"name"://;s/"//g;s/^ *//;s/ *$//')
            local pkg_version=$(grep -o '"version":[^,]*' "$target_dir/package.json" | head -1 | sed 's/"version"://;s/"//g;s/^ *//;s/ *$//')
            local pkg_publisher=$(grep -o '"publisher":[^,]*' "$target_dir/package.json" | head -1 | sed 's/"publisher"://;s/"//g;s/^ *//;s/ *$//')
            local pkg_displayName=$(grep -o '"displayName":[^,]*' "$target_dir/package.json" | head -1 | sed 's/"displayName"://;s/"//g;s/^ *//;s/ *$//')
            
            # If publisher not found, try to extract from name
            if [ -z "$pkg_publisher" ]; then
                if [[ "$pkg_name" == *"."* ]]; then
                    pkg_publisher="${pkg_name%%.*}"
                    pkg_name="${pkg_name#*.}"
                fi
            fi
            
            # Create basic .vsixmanifest
            cat > "$target_dir/.vsixmanifest" << EOF
<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="${pkg_publisher:-unknown}.${pkg_name}" Version="${pkg_version}" Publisher="${pkg_publisher:-unknown}" />
    <DisplayName>${pkg_displayName:-$pkg_name}</DisplayName>
    <Description>Extension imported from VSIX</Description>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
</PackageManifest>
EOF
        fi
    fi
    
    # Clean up temp directory
    rm -rf "$temp_dir"
    
    return 0
}

# Function to detect the Cursor installation
detect_cursor() {
    log "INFO" "Detecting Cursor IDE installation..."
    
    # Define common Cursor paths to check based on platform
    local cursor_paths=()
    
    # Check for user-specified path first
    if [ -n "$CURSOR_PATH" ]; then
        cursor_paths+=("$CURSOR_PATH")
    fi
    
    # Add platform-specific paths
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS paths
        cursor_paths+=(
            "/Applications/Cursor.app/Contents/MacOS/Cursor"
            "$HOME/Applications/Cursor.app/Contents/MacOS/Cursor"
        )
    else
        # Linux paths
        cursor_paths+=(
            "$HOME/Applications/Cursor.AppImage"
            "$HOME/Applications/Cursor"
            "$HOME/.local/bin/Cursor"
            "$HOME/.local/bin/cursor"
            "/usr/local/bin/cursor"
            "/usr/bin/cursor"
            "/opt/Cursor/cursor"
        )
    fi
    
    # Try to find cursor executable
    for path in "${cursor_paths[@]}"; do
        if [ -x "$path" ]; then
            log "SUCCESS" "Found Cursor IDE at: $path"
            CURSOR_BIN="$path"
            return 0
        elif [ -e "$path" ]; then
            log "WARN" "Found Cursor at $path but it's not executable. Setting permissions..."
            chmod +x "$path"
            if [ -x "$path" ]; then
                log "SUCCESS" "Made Cursor executable at: $path"
                CURSOR_BIN="$path"
                return 0
            else
                log "ERROR" "Failed to make Cursor executable at: $path"
            fi
        fi
    done
    
    # If we get here, we couldn't find Cursor
    log "ERROR" "Cursor IDE not found in any expected location."
    echo ""
    echo -e "${YELLOW}Please specify the Cursor IDE path using --path option:${NC}"
    echo "  $0 --path /path/to/cursor"
    echo ""
    return 1
}

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

# Function to extract extension information from package.json or vsixmanifest
extract_extension_info() {
    local ext_dir="$1"
    local ext_id=""
    local ext_version=""
    local ext_publisher=""
    local ext_name=""
    
    # Try to get info from package.json first
    if [ -f "$ext_dir/package.json" ]; then
        log "DEBUG" "Extracting info from package.json"
        
        # Extract basic info
        ext_name=$(grep -o '"name":[^,]*' "$ext_dir/package.json" | head -1 | sed 's/"name"://;s/"//g;s/^ *//;s/ *$//')
        ext_version=$(grep -o '"version":[^,]*' "$ext_dir/package.json" | head -1 | sed 's/"version"://;s/"//g;s/^ *//;s/ *$//')
        ext_publisher=$(grep -o '"publisher":[^,]*' "$ext_dir/package.json" | head -1 | sed 's/"publisher"://;s/"//g;s/^ *//;s/ *$//')
        
        # If publisher not found, try to extract from name
        if [ -z "$ext_publisher" ]; then
            if [[ "$ext_name" == *"."* ]]; then
                ext_publisher="${ext_name%%.*}"
                ext_name="${ext_name#*.}"
            fi
        fi
        
        # Construct extension ID
        if [ -n "$ext_publisher" ] && [ -n "$ext_name" ]; then
            ext_id="${ext_publisher}.${ext_name}"
        elif [ -n "$ext_name" ]; then
            ext_id="$ext_name"
        fi
    fi
    
    # If we couldn't get info from package.json, try vsixmanifest
    if [ -z "$ext_id" ] || [ -z "$ext_version" ]; then
        if [ -f "$ext_dir/.vsixmanifest" ]; then
            log "DEBUG" "Extracting info from .vsixmanifest"
            
            # Extract Identity attributes
            local identity_line=$(grep -o '<Identity[^>]*>' "$ext_dir/.vsixmanifest")
            
            if [[ "$identity_line" =~ Id=\"([^\"]+)\" ]]; then
                ext_id="${BASH_REMATCH[1]}"
            fi
            
            if [[ "$identity_line" =~ Version=\"([^\"]+)\" ]]; then
                ext_version="${BASH_REMATCH[1]}"
            fi
            
            if [[ "$identity_line" =~ Publisher=\"([^\"]+)\" ]]; then
                ext_publisher="${BASH_REMATCH[1]}"
            fi
        fi
    fi
    
    # If we still don't have an ID, use the directory name
    if [ -z "$ext_id" ]; then
        ext_id=$(basename "$ext_dir")
        # Try to extract version from directory name
        if [[ "$ext_id" =~ ^([^-]+)-([0-9]+\.[0-9]+\.[0-9].*)$ ]]; then
            ext_id="${BASH_REMATCH[1]}"
            ext_version="${BASH_REMATCH[2]}"
        fi
    fi
    
    # Return the extension ID and version
    echo "$ext_id:$ext_version:$ext_publisher"
}

# Function to create or update extensions.json
update_extensions_json() {
    local id="$1"
    local version="$2"
    local extension_dir="$3"
    local publisher="$4"
    
    # Create a more detailed entry for the extension
    local display_name=""
    local description=""
    
    # Try to get display name and description from package.json
    if [ -f "$extension_dir/package.json" ]; then
        display_name=$(grep -o '"displayName":[^,]*' "$extension_dir/package.json" | head -1 | sed 's/"displayName"://;s/"//g;s/^ *//;s/ *$//')
        description=$(grep -o '"description":[^,]*' "$extension_dir/package.json" | head -1 | sed 's/"description"://;s/"//g;s/^ *//;s/ *$//')
    fi
    
    # Create entry with more metadata
    local new_entry="{\"identifier\":{\"id\":\"$id\""
    
    # Add publisher if available
    if [ -n "$publisher" ]; then
        new_entry="$new_entry,\"publisher\":\"$publisher\""
    fi
    
    # Finalize the entry
    new_entry="$new_entry},\"version\":\"$version\",\"location\":{\"$extension_dir\":true}"
    
    # Add display name if available
    if [ -n "$display_name" ]; then
        new_entry="$new_entry,\"displayName\":\"$display_name\""
    fi
    
    # Add description if available
    if [ -n "$description" ]; then
        new_entry="$new_entry,\"description\":\"$description\""
    fi
    
    # Close the entry
    new_entry="$new_entry}"
    
    log "VERBOSE" "Adding entry to extensions.json: $new_entry"
    
    # Check if extension is already in the JSON
    if grep -q "\"id\":\"$id\"" "$EXTENSIONS_JSON"; then
        log "DEBUG" "Removing existing entry for $id from extensions.json"
        # Create temp file without the existing extension entry
        grep -v "\"id\":\"$id\"" "$EXTENSIONS_JSON" > "${EXTENSIONS_JSON}.tmp"
        
        # Add the new entry
        sed -i "s|\"extensions\":\[|\"extensions\":[$new_entry,|" "${EXTENSIONS_JSON}.tmp"
        
        # Replace the original file
        mv "${EXTENSIONS_JSON}.tmp" "$EXTENSIONS_JSON"
    else
        # Add the new entry
        sed -i "s|\"extensions\":\[|\"extensions\":[$new_entry,|" "$EXTENSIONS_JSON"
    fi
    
    # Fix JSON format if needed (replace empty array with proper closing)
    sed -i 's/\[\]/\[\]/g' "$EXTENSIONS_JSON"
    # Fix trailing comma if it's the only entry
    sed -i 's/,\]/]/g' "$EXTENSIONS_JSON"
    
    log "DEBUG" "Updated extensions.json successfully"
}

# Function to install a single extension
install_extension() {
    local ext_file="$1"
    local ext_id="$2"
    local ext_version="$3"
    
    local ext_filename=$(basename "$ext_file")
    local ext_target_dir="$CURSOR_EXTENSIONS_DIR/$ext_id-$ext_version"
    local ext_temp_dir="$TEMP_DIR/$(basename "$ext_file" .vsix)"
    
    log "INFO" "Installing: $ext_id ($ext_version)"
    log "VERBOSE" "Source file: $ext_file"
    log "VERBOSE" "Target directory: $ext_target_dir"
    
    # Simulate installation if dry run
    if [ "$DRY_RUN" = true ]; then
        log "INFO" "DRY RUN: Would install $ext_id to $ext_target_dir"
        return 0
    fi
    
    # Check if directory already exists
    if [ -d "$ext_target_dir" ]; then
        log "WARN" "Removing existing directory for $ext_id"
        rm -rf "$ext_target_dir"
        if [ $? -ne 0 ]; then
            log "ERROR" "Failed to remove existing directory: $ext_target_dir"
            return 1
        fi
    fi
    
    # Create temp directory for extraction
    mkdir -p "$ext_temp_dir"
    
    # Extract VSIX to proper directory structure
    log "VERBOSE" "Extracting VSIX contents..."
    if ! extract_vsix "$ext_file" "$ext_target_dir" "$ext_temp_dir"; then
        log "ERROR" "Failed to extract VSIX file: $ext_file"
        rm -rf "$ext_temp_dir"
        return 1
    fi
    
    # Extract extension metadata
    log "VERBOSE" "Extracting extension metadata..."
    local ext_info=$(extract_extension_info "$ext_target_dir")
    local extracted_id="${ext_info%%:*}"
    local remaining="${ext_info#*:}"
    local extracted_version="${remaining%%:*}"
    local extracted_publisher="${remaining#*:}"
    
    # Use extracted info if better than what we have
    if [ -n "$extracted_id" ] && [ "$extracted_id" != "unknown" ]; then
        ext_id="$extracted_id"
    fi
    
    if [ -n "$extracted_version" ] && [ "$extracted_version" != "unknown" ]; then
        ext_version="$extracted_version"
    fi
    
    # Update extensions.json with rich metadata
    log "VERBOSE" "Updating extensions registry..."
    update_extensions_json "$ext_id" "$ext_version" "$ext_target_dir" "$extracted_publisher"
    if [ $? -ne 0 ]; then
        log "ERROR" "Failed to update extensions.json for $ext_id"
        return 1
    fi
    
    log "SUCCESS" "Successfully installed: $ext_id ($ext_version)"
    return 0
}

# Function to show progress bar
show_progress() {
    local current="$1"
    local total="$2"
    local width=50
    local percent=$((current * 100 / total))
    local completed=$((width * current / total))
    local remaining=$((width - completed))
    
    # Only display if not in quiet mode
    if [ "$QUIET" = false ]; then
        # Create the progress bar
        local bar=$(printf "%${completed}s" | tr ' ' '█')
        local empty=$(printf "%${remaining}s" | tr ' ' '░')
        
        # Print the progress bar
        printf "\r[%s%s] %3d%% (%d/%d)" "$bar" "$empty" "$percent" "$current" "$total"
        
        # Print newline if completed
        if [ "$current" -eq "$total" ]; then
            echo ""
        fi
    fi
}

# Main execution function
main() {
    # Parse command line arguments
    while [[ "$#" -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_banner
                print_usage
                exit 0
                ;;
            -p|--path)
                CURSOR_PATH="$2"
                shift 2
                ;;
            -s|--source)
                SOURCE_EXTENSIONS_DIR="$2"
                shift 2
                ;;
            -e|--extensions)
                EXTENSIONS_LIST="$2"
                INSTALL_ALL=false
                shift 2
                ;;
            -y|--yes)
                AUTO_YES=true
                shift
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -d|--debug)
                DEBUG=true
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --parallel)
                MAX_PARALLEL="$2"
                shift 2
                ;;
            *)
                echo -e "${RED}Error: Unknown option $1${NC}" >&2
                print_usage
                exit 1
                ;;
        esac
    done
    
    # Set up temp directory
    TEMP_DIR="/tmp/cursor_extensions_$(date +%s)"
    mkdir -p "$TEMP_DIR"
    trap 'rm -rf "$TEMP_DIR"' EXIT
    
    # Print banner if not in quiet mode
    [ "$QUIET" = false ] && print_banner
    
    # Set paths
    CURSOR_EXTENSIONS_DIR="${HOME}/.cursor/extensions"
    EXTENSIONS_JSON="${CURSOR_EXTENSIONS_DIR}/extensions.json"
    
    # Create log file
    LOG_FILE="cursor_extension_install_$(date +%Y%m%d_%H%M%S).log"
    touch "$LOG_FILE"
    log "INFO" "Starting Cursor extension installation"
    log "DEBUG" "Arguments: CURSOR_PATH='$CURSOR_PATH', SOURCE_DIR='$SOURCE_EXTENSIONS_DIR', INSTALL_ALL=$INSTALL_ALL"
    
    # Make source path absolute if it's relative
    if [[ ! "$SOURCE_EXTENSIONS_DIR" =~ ^/ ]]; then
        SOURCE_EXTENSIONS_DIR="$(pwd)/$SOURCE_EXTENSIONS_DIR"
        log "DEBUG" "Converting to absolute path: $SOURCE_EXTENSIONS_DIR"
    fi
    
    # Check dependencies
    check_dependencies "unzip" "sed" "grep" || exit 1
    
    # Detect Cursor installation
    detect_cursor || exit 1
    
    # Create extensions directory if it doesn't exist
    if [ ! -d "$CURSOR_EXTENSIONS_DIR" ]; then
        log "WARN" "Cursor extensions directory not found at $CURSOR_EXTENSIONS_DIR"
        log "INFO" "Creating extensions directory..."
        mkdir -p "$CURSOR_EXTENSIONS_DIR"
        if [ $? -ne 0 ]; then
            log "ERROR" "Failed to create Cursor extensions directory"
            exit 1
        fi
    fi
    
    # Create a backup of extensions.json if it exists
    if [ -f "$EXTENSIONS_JSON" ]; then
        BACKUP_FILE="${EXTENSIONS_JSON}.backup.$(date +%Y%m%d%H%M%S)"
        cp "$EXTENSIONS_JSON" "$BACKUP_FILE"
        log "INFO" "Created backup of extensions.json at $BACKUP_FILE"
    else
        # Create an empty extensions.json file
        log "WARN" "extensions.json not found, creating new file"
        echo '{"extensions":[]}' > "$EXTENSIONS_JSON"
    fi
    
    # Check if source extensions directory exists
    if [ ! -d "$SOURCE_EXTENSIONS_DIR" ]; then
        log "ERROR" "Source extensions directory not found: $SOURCE_EXTENSIONS_DIR"
        echo -e "${YELLOW}Please specify a valid source directory using --source option:${NC}"
        echo "  $0 --source /path/to/extensions"
        exit 1
    fi
    
    # Count total extensions in our directory
    VSIX_FILES=()
    while IFS= read -r file; do
        VSIX_FILES+=("$file")
    done < <(find "$SOURCE_EXTENSIONS_DIR" -name "*.vsix" -type f | sort)
    
    TOTAL_EXTENSIONS=${#VSIX_FILES[@]}
    if [ "$TOTAL_EXTENSIONS" -eq 0 ]; then
        log "ERROR" "No .vsix files found in: $SOURCE_EXTENSIONS_DIR"
        exit 1
    fi
    
    log "INFO" "Found $TOTAL_EXTENSIONS extensions in the source directory"
    
    # Get currently installed extensions
    log "INFO" "Checking currently installed extensions..."
    INSTALLED_EXTENSIONS=()
    
    # Read directories in extensions folder to find installed extensions
    while IFS= read -r ext_dir; do
        # Skip non-directory entries and special files
        if [[ -d "$ext_dir" && ! "$ext_dir" =~ extensions\.json ]]; then
            # Extract the base directory name, which is the extension ID with version
            ext_basename=$(basename "$ext_dir")
            
            # Separate ID and version if possible
            if [[ $ext_basename =~ ^([^-]+)-([0-9]+\.[0-9]+\.[0-9].*)$ ]]; then
                ext_id="${BASH_REMATCH[1]}"
                ext_version="${BASH_REMATCH[2]}"
                INSTALLED_EXTENSIONS+=("$ext_id:$ext_version")
                log "VERBOSE" "Found installed: $ext_id ($ext_version)"
            else
                # If we can't parse, just add the whole name
                INSTALLED_EXTENSIONS+=("$ext_basename:unknown")
                log "VERBOSE" "Found installed: $ext_basename (version unknown)"
            fi
        fi
    done < <(find "$CURSOR_EXTENSIONS_DIR" -maxdepth 1 -type d | sort)
    
    log "INFO" "Found ${#INSTALLED_EXTENSIONS[@]} extensions currently installed"
    
    # Plan which extensions to install
    EXTENSIONS_TO_INSTALL=()
    EXTENSIONS_TO_SKIP=()
    
    # Convert the comma-separated list to an array
    if [ "$INSTALL_ALL" = false ] && [ -n "$EXTENSIONS_LIST" ]; then
        IFS=',' read -ra SELECTED_EXTENSIONS <<< "$EXTENSIONS_LIST"
        log "INFO" "Selected extensions to install: ${SELECTED_EXTENSIONS[*]}"
    fi
    
    log "INFO" "Analyzing extensions to install..."
    for ext_file in "${VSIX_FILES[@]}"; do
        ext_info=$(parse_extension_filename "$ext_file")
        ext_id="${ext_info%%:*}"
        ext_version="${ext_info#*:}"
        
        # Skip if not in selected extensions (when not installing all)
        if [ "$INSTALL_ALL" = false ]; then
            SELECTED=false
            for selected in "${SELECTED_EXTENSIONS[@]}"; do
                if [[ "${ext_id,,}" == "${selected,,}" ]]; then
                    SELECTED=true
                    break
                fi
            done
            
            if [ "$SELECTED" = false ]; then
                log "DEBUG" "Skipping non-selected extension: $ext_id"
                continue
            fi
        fi
        
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
                        log "INFO" "Update available: $ext_id ($installed_version → $ext_version)"
                    fi
                fi
                
                break
            fi
        done
        
        if [[ "$ALREADY_INSTALLED" == true && "$NEEDS_UPDATE" == false ]]; then
            EXTENSIONS_TO_SKIP+=("$ext_file:$ext_id:$ext_version")
            log "DEBUG" "Skip: $ext_id (already installed)"
        else
            EXTENSIONS_TO_INSTALL+=("$ext_file:$ext_id:$ext_version")
            if [[ "$ALREADY_INSTALLED" == true ]]; then
                log "DEBUG" "Update: $ext_id ($ext_version)"
            else
                log "DEBUG" "New: $ext_id ($ext_version)"
            fi
        fi
    done
    
    log "INFO" "Installation plan:"
    log "INFO" "  Total extensions in source: $TOTAL_EXTENSIONS"
    log "INFO" "  Currently installed: ${#INSTALLED_EXTENSIONS[@]}"
    log "INFO" "  To be installed/updated: ${#EXTENSIONS_TO_INSTALL[@]}"
    log "INFO" "  To be skipped: ${#EXTENSIONS_TO_SKIP[@]}"
    
    # If nothing to install, exit
    if [ "${#EXTENSIONS_TO_INSTALL[@]}" -eq 0 ]; then
        log "SUCCESS" "All extensions are already installed and up to date!"
        mv "$LOG_FILE" "logs/$LOG_FILE"
        exit 0
    fi
    
    # Display installation plan to user
    if [ "$QUIET" = false ]; then
        echo ""
        echo -e "${BOLD}Installation Plan:${NC}"
        echo -e "  ${BLUE}Total extensions in source:${NC} $TOTAL_EXTENSIONS"
        echo -e "  ${BLUE}Currently installed:${NC} ${#INSTALLED_EXTENSIONS[@]}"
        echo -e "  ${GREEN}To be installed/updated:${NC} ${#EXTENSIONS_TO_INSTALL[@]}"
        echo -e "  ${GRAY}To be skipped:${NC} ${#EXTENSIONS_TO_SKIP[@]}"
        echo ""
        
        # Show extensions to be installed if verbose
        if [ "$VERBOSE" = true ]; then
            echo -e "${BOLD}Extensions to install:${NC}"
            for ext_entry in "${EXTENSIONS_TO_INSTALL[@]}"; do
                ext_file="${ext_entry%%:*}"
                remaining="${ext_entry#*:}"
                ext_id="${remaining%%:*}"
                ext_version="${remaining#*:}"
                echo -e "  ${GREEN}•${NC} $ext_id ($ext_version)"
            done
            echo ""
        fi
    fi
    
    # Ask for confirmation
    if [ "$AUTO_YES" = false ] && [ "$DRY_RUN" = false ]; then
        echo -e "${YELLOW}Do you want to proceed with installation? (y/n)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log "INFO" "Installation cancelled by user"
            mv "$LOG_FILE" "logs/$LOG_FILE"
            exit 0
        fi
    fi
    
    # Initialize counters
    INSTALLED=0
    FAILED=0
    
    # Install extensions
    log "INFO" "Starting installation..."
    
    if [ "$DRY_RUN" = true ]; then
        log "INFO" "DRY RUN mode - no changes will be made"
    fi
    
    # Process extensions
    total_count=${#EXTENSIONS_TO_INSTALL[@]}
    current_count=0
    
    for ext_entry in "${EXTENSIONS_TO_INSTALL[@]}"; do
        ext_file="${ext_entry%%:*}"
        remaining="${ext_entry#*:}"
        ext_id="${remaining%%:*}"
        ext_version="${remaining#*:}"
        
        # Update progress
        ((current_count++))
        show_progress $current_count $total_count
        
        # Install the extension
        install_extension "$ext_file" "$ext_id" "$ext_version"
        
        if [ $? -eq 0 ]; then
            ((INSTALLED++))
        else
            ((FAILED++))
            log "ERROR" "Failed to install: $ext_id"
        fi
    done
    
    # Fix extensions.json format (remove trailing commas)
    sed -i 's/,]/]/g' "$EXTENSIONS_JSON"
    
    # Print summary
    log "INFO" "Installation completed"
    log "INFO" "Total extensions installed/updated: $INSTALLED"
    log "INFO" "Total extensions failed: $FAILED"
    
    if [ "$QUIET" = false ]; then
        echo ""
        echo -e "${BOLD}===== Installation Summary =====${NC}"
        echo -e "${BLUE}Total extensions to install/update:${NC} ${#EXTENSIONS_TO_INSTALL[@]}"
        echo -e "${GREEN}Successfully installed:${NC} ${INSTALLED}"
        
        if [ "$FAILED" -gt 0 ]; then
            echo -e "${RED}Failed to install:${NC} ${FAILED}"
            echo -e "${YELLOW}Check ${LOG_FILE} for details on failures${NC}"
        else
            echo -e "${GREEN}All selected extensions installed successfully!${NC}"
        fi
        
        # Final note about skipped extensions
        if [ "${#EXTENSIONS_TO_SKIP[@]}" -gt 0 ]; then
            echo ""
            echo -e "${BLUE}Note: ${#EXTENSIONS_TO_SKIP[@]} extensions were skipped as they are already installed${NC}"
        fi
        
        echo ""
        echo -e "${GREEN}Installation log saved to: logs/$LOG_FILE${NC}"
        echo ""
        echo -e "${YELLOW}Please restart Cursor IDE to activate the extensions.${NC}"
    fi
    
    # Move log file to logs directory
    mkdir -p logs
    mv "$LOG_FILE" "logs/$LOG_FILE"
    
    # Return appropriate exit code
    if [ "$FAILED" -gt 0 ]; then
        return 1
    else
        return 0
    fi
}

# Execute the main function
main "$@"


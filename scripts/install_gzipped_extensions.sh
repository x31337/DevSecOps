#!/bin/bash
# Cursor IDE Extension Installer for gzipped VSIX files
# Modified version to handle gzipped VSIX files

# Set script variables
SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
TIMESTAMP=$(date "+%Y%m%d_%H%M%S")
LOG_DIR="${SCRIPT_DIR}/logs"
TEMP_DIR="/tmp/cursor_extensions_${TIMESTAMP}"
LOG_FILE="${LOG_DIR}/cursor_extension_install_${TIMESTAMP}.log"

# Default configuration
CURSOR_PATH=""
SOURCE_DIR="${SCRIPT_DIR}/extensions"
SPECIFIC_EXTENSIONS=""
AUTO_CONFIRM=false
QUIET_MODE=false
VERBOSE_MODE=false
DEBUG_MODE=false
DRY_RUN=false
MAX_PARALLEL=4

# Terminal colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print banner
print_banner() {
    echo -e "┌───────────────────────────────────────────┐"
    echo -e "│      Cursor IDE Extension Installer       │"
    echo -e "│      (Gzipped VSIX Support Edition)       │"
    echo -e "│      For https://cursor.sh IDE            │"
    echo -e "└───────────────────────────────────────────┘"
    echo ""
}

# Function to print help
print_help() {
    echo "Usage: $SCRIPT_NAME [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help             Show this help message and exit"
    echo "  -p, --path PATH        Specify Cursor installation path"
    echo "  -s, --source DIR       Specify source extensions directory (default: ./extensions)"
    echo "  -e, --extensions LIST  Comma-separated list of extensions to install (default: all)"
    echo "  -y, --yes              Auto-confirm all prompts"
    echo "  -q, --quiet            Minimal output mode"
    echo "  -v, --verbose          Verbose output mode"
    echo "  -d, --debug            Debug mode with extra information"
    echo "  --dry-run              Simulate installation without making changes"
    echo "  --parallel NUM         Maximum parallel operations (default: 4)"
    echo ""
    echo "Examples:"
    echo "  $SCRIPT_NAME --path ~/Applications/Cursor.AppImage"
    echo "  $SCRIPT_NAME --source ./my-extensions --extensions github.copilot,ms-python.python"
    echo "  $SCRIPT_NAME --yes --quiet"
}

# Logging functions
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    echo -e "[${timestamp}] ${level}: ${message}" >> "${LOG_FILE}"
    
    if [[ "$QUIET_MODE" == "false" ]] || [[ "$level" == "ERROR" ]]; then
        case "$level" in
            "INFO")
                echo -e "[${timestamp}] ${BLUE}INFO${NC}: ${message}"
                ;;
            "SUCCESS")
                echo -e "[${timestamp}] ${GREEN}SUCCESS${NC}: ${message}"
                ;;
            "WARNING")
                echo -e "[${timestamp}] ${YELLOW}WARNING${NC}: ${message}"
                ;;
            "ERROR")
                echo -e "[${timestamp}] ${RED}ERROR${NC}: ${message}"
                ;;
            "DEBUG")
                if [[ "$DEBUG_MODE" == "true" ]]; then
                    echo -e "[${timestamp}] ${MAGENTA}DEBUG${NC}: ${message}"
                fi
                ;;
            *)
                echo -e "[${timestamp}] ${message}"
                ;;
        esac
    fi
}

# Check if a file is gzipped
is_gzipped() {
    local file="$1"
    local magic=$(dd if="$file" bs=2 count=1 2>/dev/null | hexdump -n 2 -e '1/1 "%02x"')
    
    # Check for gzip magic number (1f8b)
    if [[ "$magic" == "1f8b" ]]; then
        return 0  # true
    else
        return 1  # false
    fi
}

# Decompress a gzipped file to a temporary location
decompress_gzip() {
    local src_file="$1"
    local dest_dir="$2"
    local filename=$(basename "$src_file")
    local output_file="${dest_dir}/${filename}.unzipped"
    
    log "DEBUG" "Decompressing gzipped file: $src_file to $output_file"
    
    mkdir -p "$dest_dir"
    
    if gzip -cd "$src_file" > "$output_file" 2>/dev/null; then
        echo "$output_file"
        return 0
    else
        log "ERROR" "Failed to decompress file: $src_file"
        return 1
    fi
}

# Function to parse command-line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                print_banner
                print_help
                exit 0
                ;;
            -p|--path)
                CURSOR_PATH="$2"
                shift 2
                ;;
            -s|--source)
                SOURCE_DIR="$2"
                shift 2
                ;;
            -e|--extensions)
                SPECIFIC_EXTENSIONS="$2"
                shift 2
                ;;
            -y|--yes)
                AUTO_CONFIRM=true
                shift
                ;;
            -q|--quiet)
                QUIET_MODE=true
                shift
                ;;
            -v|--verbose)
                VERBOSE_MODE=true
                shift
                ;;
            -d|--debug)
                DEBUG_MODE=true
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
                log "ERROR" "Unknown option: $1"
                print_help
                exit 1
                ;;
        esac
    done
}

# Function to check dependencies
check_dependencies() {
    log "INFO" "Checking dependencies..."
    
    # Check for unzip
    if ! command -v unzip &> /dev/null; then
        log "ERROR" "unzip is not installed. Please install it first."
        exit 1
    fi
    
    # Check for gzip
    if ! command -v gzip &> /dev/null; then
        log "ERROR" "gzip is not installed. Please install it first."
        exit 1
    fi
    
    # Check for mktemp
    if ! command -v mktemp &> /dev/null; then
        log "ERROR" "mktemp is not installed. Please install it first."
        exit 1
    fi
}

# Find Cursor IDE installation
find_cursor_installation() {
    log "INFO" "Detecting Cursor IDE installation..."
    
    if [[ -n "$CURSOR_PATH" ]]; then
        if [[ -f "$CURSOR_PATH" ]]; then
            log "SUCCESS" "Found Cursor IDE at: $CURSOR_PATH"
            return 0
        else
            log "ERROR" "Specified Cursor path does not exist: $CURSOR_PATH"
            exit 1
        fi
    fi
    
    # Try common locations
    local common_locations=(
        "$HOME/Applications/Cursor.AppImage"
        "$HOME/.local/bin/Cursor.AppImage"
        "$HOME/bin/Cursor.AppImage"
        "/usr/local/bin/Cursor.AppImage"
        "/opt/Cursor/Cursor.AppImage"
    )
    
    for location in "${common_locations[@]}"; do
        if [[ -f "$location" ]]; then
            CURSOR_PATH="$location"
            log "SUCCESS" "Found Cursor IDE at: $CURSOR_PATH"
            return 0
        fi
    done
    
    log "ERROR" "Could not find Cursor IDE installation. Please specify path with --path."
    exit 1
}

# Get Cursor extensions directory
get_cursor_extensions_dir() {
    local extensions_dir="$HOME/.cursor/extensions"
    
    if [[ ! -d "$extensions_dir" ]]; then
        log "WARNING" "Cursor extensions directory not found at: $extensions_dir"
        
        if [[ "$AUTO_CONFIRM" == "false" ]]; then
            read -p "Create extensions directory? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log "ERROR" "Aborted by user."
                exit 1
            fi
        fi
        
        mkdir -p "$extensions_dir"
        log "INFO" "Created extensions directory: $extensions_dir"
    fi
    
    echo "$extensions_dir"
}

# Backup extensions.json file
backup_extensions_json() {
    local extensions_dir="$1"
    local extensions_json="${extensions_dir}/extensions.json"
    
    if [[ -f "$extensions_json" ]]; then
        local backup_file="${extensions_json}.backup.$(date +%Y%m%d%H%M%S)"
        
        if [[ "$DRY_RUN" == "false" ]]; then
            cp "$extensions_json" "$backup_file"
            log "INFO" "Created backup of extensions.json at $backup_file"
        else
            log "INFO" "[DRY RUN] Would create backup of extensions.json at $backup_file"
        fi
    else
        log "INFO" "No existing extensions.json found. Will create a new one."
    fi
}

# Extract extension ID from filename
extract_extension_id() {
    local filename="$1"
    local basename=$(basename "$filename")
    
    # Handle different naming patterns
    if [[ "$basename" =~ ^([^@]+)@.+ ]]; then
        # Format: publisher.extension@version.vsix
        echo "${BASH_REMATCH[1]}"
    elif [[ "$basename" =~ ^([^-]+)-([^-]+)(-(.+))?.vsix$ ]]; then
        # Format: publisher.extension-version.vsix
        echo "${BASH_REMATCH[1]}"
    else
        # Unknown format, return empty
        echo ""
    fi
}

# Extract extension version from filename
extract_extension_version() {
    local filename="$1"
    local basename=$(basename "$filename")
    
    # Handle different naming patterns
    if [[ "$basename" =~ ^[^@]+@(.+)\.vsix$ ]]; then
        # Format: publisher.extension@version.vsix
        echo "${BASH_REMATCH[1]}"
    elif [[ "$basename" =~ ^[^-]+-([^-]+)(-(.+))?.vsix$ ]]; then
        # Format: publisher.extension-version.vsix
        echo "${BASH_REMATCH[1]}"
    else
        # Unknown format, return empty
        echo ""
    fi
}

# Install a single extension
install_extension() {
    local vsix_file="$1"
    local extensions_dir="$2"
    local extension_id=$(extract_extension_id "$vsix_file")
    local version=$(extract_extension_version "$vsix_file")
    
    if [[ -z "$extension_id" ]]; then
        log "ERROR" "Could not determine extension ID from filename: $(basename "$vsix_file")"
        return 1
    fi
    
    log "INFO" "Installing: $extension_id ($version)"
    
    # Create target directory
    local target_dir="${extensions_dir}/${extension_id}-${version}"
    
    if [[ -d "$target_dir" ]]; then
        log "WARNING" "Removing existing directory for $extension_id"
        if [[ "$DRY_RUN" == "false" ]]; then
            rm -rf "$target_dir"
        fi
    fi
    
    if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "$target_dir"
        
        # Check if the file is gzipped
        if is_gzipped "$vsix_file"; then
            log "DEBUG" "Detected gzipped VSIX file: $vsix_file"
            local temp_file=$(decompress_gzip "$vsix_file" "$TEMP_DIR")
            
            if [[ $? -ne 0 ]]; then
                log "ERROR" "Failed to decompress gzipped file: $vsix_file"
                return 1
            fi
            
            vsix_file="$temp_file"
        fi
        
        # Now extract the VSIX file (which should be a ZIP file)
        log "DEBUG" "[$vsix_file]"
        if ! unzip -q "$vsix_file" -d "$target_dir"; then
            log "ERROR" "Failed to extract VSIX file: $vsix_file"
            
            # Try another approach with less strict ZIP handling
            if ! unzip -q -FF "$vsix_file" -d "$target_dir"; then
                log "ERROR" "Failed to extract VSIX file with recovery mode: $vsix_file"
                return 1
            fi
        fi
        
        return 0
    else
        log "INFO" "[DRY RUN] Would install $extension_id ($version) to $target_dir"
        return 0
    fi
}

# Main function
main() {
    print_banner
    
    # Parse command-line arguments
    parse_args "$@"
    
    # Create log directory if it doesn't exist
    mkdir -p "$LOG_DIR"
    
    # Create temp directory for decompressed files
    mkdir -p "$TEMP_DIR"
    
    # Initialize log file
    echo "# Cursor IDE Extension Installation Log - $(date)" > "$LOG_FILE"
    echo "# Command: $0 $*" >> "$LOG_FILE"
    echo "---" >> "$LOG_FILE"
    
    # Start logging
    log "INFO" "Starting Cursor extension installation"
    
    # Check dependencies
    check_dependencies
    
    # Find Cursor installation
    find_cursor_installation
    
    # Get Cursor extensions directory
    extensions_dir=$(get_cursor_extensions_dir)
    
    # Backup existing extensions.json
    backup_extensions_json "$extensions_dir"
    
    # Check source directory
    if [[ ! -d "$SOURCE_DIR" ]]; then
        log "ERROR" "Source extensions directory not found: $SOURCE_DIR"
        echo "Please specify a valid source directory using --source option:"
        echo "  $SCRIPT_NAME --source /path/to/extensions"
        exit 1
    fi
    
    # Get all VSIX files from source directory
    vsix_files=()
    while IFS= read -r -d $'\0' file; do
        vsix_files+=("$file")
    done < <(find "$SOURCE_DIR" -type f -name "*.vsix" -print0 | sort -z)
    
    # Check if we found any extensions
    if [[ ${#vsix_files[@]} -eq 0 ]]; then
        log "ERROR" "No .vsix files found in $SOURCE_DIR"
        exit 1
    fi
    
    log "INFO" "Found ${#vsix_files[@]} extensions in the source directory"
    
    # Get currently installed extensions
    current_extensions=()
    if [[ -d "$extensions_dir" ]]; then
        while IFS= read -r -d $'\0' dir; do
            if [[ -d "$dir" ]]; then
                current_extensions+=("$(basename "$dir")")
            fi
        done < <(find "$extensions_dir" -mindepth 1 -maxdepth 1 -type d -print0)
    fi
    
    log "INFO" "Found ${#current_extensions[@]} extensions currently installed"
    
    # Filter extensions if specific ones are requested
    selected_vsix_files=()
    if [[ -n "$SPECIFIC_EXTENSIONS" ]]; then
        IFS=',' read -ra extension_ids <<< "$SPECIFIC_EXTENSIONS"
        
        log "INFO" "Selected extensions to install: ${extension_ids[*]}"
        
        for vsix_file in "${vsix_files[@]}"; do
            id=$(extract_extension_id "$vsix_file")
            for extension_id in "${extension_ids[@]}"; do
                if [[ "$id" == "$extension_id" ]]; then
                    selected_vsix_files+=("$vsix_file")
                    break
                fi
            done
        done
    else
        selected_vsix_files=("${vsix_files[@]}")
    fi
    
    # Build installation plan
    install_plan=()
    skip_list=()
    
    log "INFO" "Analyzing extensions to install..."
    
    for vsix_file in "${selected_vsix_files[@]}"; do
        ext_id=$(extract_extension_id "$vsix_file")
        ext_version=$(extract_extension_version "$vsix_file")
        
        # Check if we need to update this extension
        update_needed=true
        current_version=""
        
        for current_ext in "${current_extensions[@]}"; do
            if [[ "$current_ext" =~ ^${ext_id}-([^-]+)$ ]]; then
                current_version="${BASH_REMATCH[1]}"
                
                if [[ "$current_version" == "$ext_version" ]]; then
                    update_needed=false
                    skip_list+=("$ext_id ($ext_version) - already installed")
                    break
                else
                    log "INFO" "Update available: $ext_id ($current_version → $ext_version)"
                    break
                fi
            fi
        done
        
        if [[ "$update_needed" == "true" ]]; then
            install_plan+=("$vsix_file")
        fi
    done
    
    # Show installation plan
    log "INFO" "Installation plan:"
    log "INFO" "  Total extensions in source: ${#vsix_files[@]}"
    log "INFO" "  Currently installed: ${#current_extensions[@]}"
    log "INFO" "  To be installed/updated: ${#install_plan[@]}"
    log "INFO" "  To be skipped: ${#skip_list[@]}"
    
    echo ""
    echo "Installation Plan:"
    echo "  Total extensions in source: ${#vsix_files[@]}"
    echo "  Currently installed: ${#current_extensions[@]}"
    echo "  To be installed/updated: ${#install_plan[@]}"
    echo "  To be skipped: ${#skip_list[@]}"
    echo ""
    
    # Confirm installation if not auto-confirmed
    if [[ "$AUTO_CONFIRM" == "false" ]] && [[ ${#install_plan[@]} -gt 0 ]]; then
        read -p "Proceed with installation? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "INFO" "Installation cancelled by user."
            exit 0
        fi
    fi
    
    # Start installation
    if [[ ${#install_plan[@]} -gt 0 ]]; then
        log "INFO" "Starting installation..."
        
        total_extensions=${#install_plan[@]}
        installed_count=0
        failed_count=0
        
        # Create array to store installation results
        declare -A install_results
        
        # Process extensions
        for ((i=0; i<${#install_plan[@]}; i++)); do
            vsix_file="${install_plan[$i]}"
            ext_id=$(extract_extension_id "$vsix_file")
            
            # Show progress bar
            progress=$((100 * i / total_extensions))
            bar_length=25
            filled_length=$((bar_length * i / total_extensions))
            bar=""
            for ((j=0; j<bar_length; j++)); do
                if [[ $j -lt $filled_length ]]; then
                    bar+="█"
                else
                    bar+="░"
                fi
            done
            
            if [[ "$QUIET_MODE" == "false" ]]; then
                echo -ne "[${bar}] $((i*100/total_extensions))% (${i}/${total_extensions})\r"
            fi
            
            # Install extension
            if install_extension "$vsix_file" "$extensions_dir"; then
                install_results["$ext_id"]="success"
                ((installed_count++))
            else
                install_results["$ext_id"]="failed"
                ((failed_count++))
            fi
        done
        
        # Show final progress bar
        if [[ "$QUIET_MODE" == "false" ]]; then
            bar=""
            for ((j=0; j<bar_length; j++)); do
                bar+="█"
            done
            echo -ne "[${bar}] 100% (${total_extensions}/${total_extensions})\r"
            echo -e "\n"
        fi
    else
        log "INFO" "No extensions to install or update."
    fi
    
    # Generate new extensions.json if needed
    if [[ "$DRY_RUN" == "false" ]]; then
        log "INFO" "Installation completed"
        log "INFO" "Total extensions installed/updated: $installed_count"
        log "INFO" "Total extensions failed: $failed_count"
        
        # Generate a summary report
        echo ""
        echo "===== Installation Summary ====="
        echo "Total extensions to install/update: ${#install_plan[@]}"
        echo "Successfully installed: $installed_count"
        echo "Failed to install: $failed_count"
        if [[ $failed_count -gt 0 ]]; then
            echo "Check ${LOG_FILE##*/} for details on failures"
        fi
        
        if [[ ${#skip_list[@]} -gt 0 ]]; then
            echo ""
            echo "Note: ${#skip_list[@]} extensions were skipped as they are already installed"
        fi
        
        echo ""
        echo "Installation log saved to: ${LOG_FILE}"
        echo ""
        echo "Please restart Cursor IDE to activate the extensions."
    else
        log "INFO" "[DRY RUN] Installation simulation completed"
    fi
    
    # Clean up temp directory
    rm -rf "$TEMP_DIR"
}

# Execute main function with all arguments
main "$@"


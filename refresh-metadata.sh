#!/bin/bash
# Script to run the remeta

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Default values
JELLYFIN_HOST=${JELLYFIN_HOST:-""}
JELLYFIN_API_KEY=${JELLYFIN_API_KEY:-""}
JELLYFIN_USER_ID=${JELLYFIN_USER_ID:-""}
REFRESH_INTERVAL=${REFRESH_INTERVAL:-30}
RUN_ONCE=${RUN_ONCE:-""}
DEBUG=${DEBUG:-""}
ADDITIONAL_ARGS=${ADDITIONAL_ARGS:-""}

# Display usage information
function show_usage {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --host HOST            Jellyfin server URL"
    echo "  -k, --api-key KEY          Jellyfin API key"
    echo "  -u, --user-id ID           User ID to filter items"
    echo "  -t, --item-types TYPES     Comma-separated list of item types to refresh"
    echo "  -m, --replace-metadata     Replace all metadata"
    echo "  -i, --replace-images       Replace all images"
    echo "  -p, --regenerate-trickplay Regenerate trickplay images"
    echo "  -d, --delay SECONDS        Delay between API requests in seconds"
    echo "  -v, --verbose              Enable verbose logging"
    echo "  -d, --debug                Enable debug mode with request/response dumps"
    echo "  -o, --run-once             Run once and exit (default is to run periodically)"
    echo "  -n, --interval MINUTES     Interval in minutes between refresh runs (default: 30)"
    echo "  --help                     Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  JELLYFIN_HOST              Jellyfin server URL"
    echo "  JELLYFIN_API_KEY           Jellyfin API key"
    echo "  JELLYFIN_USER_ID           User ID to filter items"
    echo ""
    echo "Example:"
    echo "  $0 --host https://jellyfin.example.com --api-key YOUR_API_KEY --item-types Movie,Series"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--host)
            JELLYFIN_HOST="$2"
            shift 2
            ;;
        -k|--api-key)
            JELLYFIN_API_KEY="$2"
            shift 2
            ;;
        -u|--user-id)
            JELLYFIN_USER_ID="$2"
            shift 2
            ;;
        -t|--item-types)
            ADDITIONAL_ARGS="$ADDITIONAL_ARGS --item-types $2"
            shift 2
            ;;
        -m|--replace-metadata)
            ADDITIONAL_ARGS="$ADDITIONAL_ARGS --replace-all-metadata"
            shift
            ;;
        -i|--replace-images)
            ADDITIONAL_ARGS="$ADDITIONAL_ARGS --replace-all-images"
            shift
            ;;
        -p|--regenerate-trickplay)
            ADDITIONAL_ARGS="$ADDITIONAL_ARGS --regenerate-trickplay"
            shift
            ;;
        -d|--delay)
            ADDITIONAL_ARGS="$ADDITIONAL_ARGS --delay $2"
            shift 2
            ;;
        -v|--verbose)
            ADDITIONAL_ARGS="$ADDITIONAL_ARGS --verbose"
            shift
            ;;
        -d|--debug)
            DEBUG="true"
            ADDITIONAL_ARGS="$ADDITIONAL_ARGS --debug"
            shift
            ;;
        -o|--run-once)
            RUN_ONCE="true"
            ADDITIONAL_ARGS="$ADDITIONAL_ARGS --run-once"
            shift
            ;;
        -n|--interval)
            REFRESH_INTERVAL="$2"
            ADDITIONAL_ARGS="$ADDITIONAL_ARGS --interval $2"
            shift 2
            ;;
        --help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

# Check required parameters
if [ -z "$JELLYFIN_HOST" ]; then
    echo "Error: Jellyfin host is required"
    echo "Please provide it via --host option or JELLYFIN_HOST environment variable"
    exit 1
fi

if [ -z "$JELLYFIN_API_KEY" ]; then
    echo "Error: Jellyfin API key is required"
    echo "Please provide it via --api-key option or JELLYFIN_API_KEY environment variable"
    exit 1
fi

# Prepare command
CMD="python remeta.py --host $JELLYFIN_HOST --api-key $JELLYFIN_API_KEY"

if [ ! -z "$JELLYFIN_USER_ID" ]; then
    CMD="$CMD --user-id $JELLYFIN_USER_ID"
fi

CMD="$CMD $ADDITIONAL_ARGS"

# Run the command
echo "Running: $CMD"
eval $CMD
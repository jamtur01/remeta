# remeta

A tool to refresh metadata for season items in a Jellyfin server. This tool can be run as a standalone Python script or within a Docker container.

## Features

- Refreshes metadata for all items in a Jellyfin server
- Runs periodically (default: every 30 minutes)
- Configurable refresh options (full refresh, replace metadata, replace images, etc.)
- Docker support for easy deployment
- Configurable via environment variables or command-line arguments

## Requirements

- Python 3.6+
- Jellyfin server with API access
- API key with appropriate permissions
- python-dotenv (for .env file support)

## Installation

### Option 1: Using Python

1. Clone this repository:

   ```
   git clone https://github.com/jamtur01/remeta.git
   cd remeta
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

### Option 2: Using Docker

1. Build the Docker image:
   ```
   docker build -t remeta .
   ```

## Usage

### Running with Python

#### Using Command Line Arguments

```bash
python remeta.py --host https://your-jellyfin-server.com --api-key YOUR_API_KEY [options]
```

#### Using a .env File

1. Create a .env file in the same directory as the script:

   ```
   JELLYFIN_HOST=https://your-jellyfin-server.com
   JELLYFIN_API_KEY=your_api_key_here
   JELLYFIN_USER_ID=your_user_id_here
   ```

2. Run the script without command line arguments:

   ```bash
   python remeta.py [options]
   ```

   The script will automatically load the configuration from the .env file.

### Running with Docker

```bash
docker run --rm \
  -e JELLYFIN_HOST=https://your-jellyfin-server.com \
  -e JELLYFIN_API_KEY=YOUR_API_KEY \
  remeta [options]
```

### Command-line Options

| Option                   | Description                                                        | Default                                 |
| ------------------------ | ------------------------------------------------------------------ | --------------------------------------- |
| `--host`                 | Jellyfin server URL                                                | Environment variable `JELLYFIN_HOST`    |
| `--api-key`              | Jellyfin API key                                                   | Environment variable `JELLYFIN_API_KEY` |
| `--user-id`              | User ID to filter items                                            | Environment variable `JELLYFIN_USER_ID` |
| `--batch-size`           | Number of items to process in parallel                             | 20                                      |
| `--delay`                | Delay between API requests in seconds                              | 1.0                                     |
| `--refresh-mode`         | Metadata refresh mode (None, ValidationOnly, Default, FullRefresh) | FullRefresh                             |
| `--replace-all-metadata` | Replace all metadata                                               | False                                   |
| `--replace-all-images`   | Replace all images                                                 | False                                   |
| `--regenerate-trickplay` | Regenerate trickplay images                                        | False                                   |
| `--item-types`           | Comma-separated list of item types to refresh                      | All types                               |
| `--verbose`              | Enable verbose logging                                             | False                                   |
| `--run-once`             | Run once and exit                                                  | False                                   |
| `--interval`             | Interval in minutes between refresh runs                           | 30                                      |

## Examples

### Refresh all items with default settings

```bash
python remeta.py --host https://your-jellyfin-server.com --api-key YOUR_API_KEY
```

### Refresh only movies and series with full metadata replacement

```bash
python remeta.py \
  --host https://your-jellyfin-server.com \
  --api-key YOUR_API_KEY \
  --item-types Movie,Series \
  --replace-all-metadata
```

### Run once without periodic execution

```bash
python remeta.py \
  --host https://your-jellyfin-server.com \
  --api-key YOUR_API_KEY \
  --run-once
```

### Run every 15 minutes instead of the default 30 minutes

```bash
python remeta.py \
  --host https://your-jellyfin-server.com \
  --api-key YOUR_API_KEY \
  --interval 15
```

### Using Docker with environment variables

```bash
docker run --rm \
  -e JELLYFIN_HOST=https://your-jellyfin-server.com \
  -e JELLYFIN_API_KEY=YOUR_API_KEY \
  -e JELLYFIN_USER_ID=YOUR_USER_ID \
  remeta --replace-all-metadata --item-types Movie,Series
```

## Scheduling with Cron

You can set up a cron job to run the metadata refresher periodically:

```
# Run metadata refresh every day at 3:00 AM
0 3 * * * docker run --rm -e JELLYFIN_HOST=https://your-jellyfin-server.com -e JELLYFIN_API_KEY=YOUR_API_KEY remeta
```

## License

MIT

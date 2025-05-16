#!/usr/bin/env python3
"""
remeta

This script connects to a Jellyfin server and refreshes metadata for all items.
It can be run as a standalone script or within a Docker container.
By default, it runs periodically every 30 minutes.

Usage:
    python remeta.py --host <jellyfin_host> --api-key <api_key> [--options]

Environment variables:
    JELLYFIN_HOST: Jellyfin server URL
    JELLYFIN_API_KEY: Jellyfin API key

Configuration:
    The script supports loading environment variables from a .env file.
    Create a .env file in the same directory as the script with the following format:
    
    JELLYFIN_HOST=https://your-jellyfin-server.com
    JELLYFIN_API_KEY=your_api_key_here

Periodic Execution:
    By default, the script runs every 30 minutes. You can customize this with:
    --run-once: Run once and exit
    --interval <minutes>: Set the interval between refresh runs (default: 30 minutes)
"""

import argparse
import logging
import os
import sys
import time
from typing import Dict, List, Optional, Union
import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('jellyfin-metadata-refresher')

class JellyfinMetadataRefresher:
    """Class to handle refreshing metadata for Jellyfin items."""

    def __init__(
        self,
        host: str,
        api_key: str,
        batch_size: int = 20,
        delay: float = 1.0,
        refresh_mode: str = "FullRefresh",
        replace_all_metadata: bool = False,
        replace_all_images: bool = False,
        regenerate_trickplay: bool = False,
        item_types: Optional[List[str]] = ["Season"],  # Default to Season type only
        debug: bool = False
    ):
        """
        Initialize the remeta.
        
        Args:
            host: Jellyfin server URL
            api_key: Jellyfin API key
            batch_size: Number of items to process in parallel
            delay: Delay between API requests in seconds
            refresh_mode: Metadata refresh mode (None, ValidationOnly, Default, FullRefresh)
            replace_all_metadata: Whether to replace all metadata
            replace_all_images: Whether to replace all images
            regenerate_trickplay: Whether to regenerate trickplay images
            item_types: List of item types to refresh (e.g., ["Movie", "Series"])
            debug: Whether to enable debug mode with request/response dumps
        """
        # Ensure host is properly formatted
        if not host.startswith(('http://', 'https://')):
            host = f"http://{host}"
        
        # Ensure host doesn't end with a trailing slash
        self.host = host.rstrip('/')
        self.api_key = api_key
        self.batch_size = batch_size
        self.delay = delay
        self.refresh_mode = refresh_mode
        self.replace_all_metadata = replace_all_metadata
        self.replace_all_images = replace_all_images
        self.regenerate_trickplay = regenerate_trickplay
        self.item_types = item_types
        self.debug = debug
        
        # Set up headers for API requests
        self.headers = {
            'X-Emby-Token': api_key,
            'Content-Type': 'application/json'
        }
        
        logger.info(f"Initialized remeta for {host}")
        
        # Verify connection to the server
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify connection to the Jellyfin server."""
        url = f"{self.host}/System/Info/Public"
        try:
            response = requests.get(url, timeout=10)
            
            # Dump request/response details if debug mode is enabled
            self._dump_request_response('GET', url, headers={}, response=response)
            
            response.raise_for_status()
            server_info = response.json()
            logger.info(f"Successfully connected to Jellyfin server: {server_info.get('ServerName', 'Unknown')} (Version: {server_info.get('Version', 'Unknown')})")
        except RequestException as e:
            logger.warning(f"Could not verify connection to Jellyfin server: {e}")
            logger.warning("Will attempt to proceed anyway, but this may indicate a problem with the server URL or network connection.")
            
            # Dump request/response details if debug mode is enabled
            self._dump_request_response('GET', url, headers={}, error=e)
    
    def _dump_request_response(self, method: str, url: str, params: Dict = None, headers: Dict = None,
                              response: requests.Response = None, error: Exception = None):
        """
        Dump request and response details for debugging.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Request parameters
            headers: Request headers
            response: Response object (if available)
            error: Exception (if an error occurred)
        """
        if not self.debug:
            logger.debug("Debug mode is enabled but self.debug is False - no request/response dumps will be shown")
            return
            
        logger.debug("Dumping request/response details...")
            
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        logger.debug(f"\n{'=' * 80}\n{timestamp} - REQUEST/RESPONSE DUMP\n{'=' * 80}")
        logger.debug(f"REQUEST: {method} {url}")
        
        if params:
            logger.debug(f"PARAMS:\n{json.dumps(params, indent=2)}")
            
        if headers:
            # Create a copy of headers to avoid modifying the original
            safe_headers = headers.copy()
            # Mask sensitive information
            if 'X-Emby-Token' in safe_headers:
                safe_headers['X-Emby-Token'] = '***MASKED***'
            logger.debug(f"HEADERS:\n{json.dumps(safe_headers, indent=2)}")
        
        if response:
            logger.debug(f"RESPONSE STATUS: {response.status_code}")
            logger.debug(f"RESPONSE HEADERS:\n{json.dumps(dict(response.headers), indent=2)}")
            
            try:
                if response.text:
                    # Try to parse as JSON for pretty printing
                    try:
                        json_response = response.json()
                        logger.debug(f"RESPONSE BODY (JSON):\n{json.dumps(json_response, indent=2)}")
                    except ValueError:
                        # Not JSON, log as text
                        logger.debug(f"RESPONSE BODY (TEXT):\n{response.text[:1000]}")
                        if len(response.text) > 1000:
                            logger.debug("... (truncated)")
                else:
                    logger.debug("RESPONSE BODY: <empty>")
            except Exception as e:
                logger.debug(f"Error parsing response: {e}")
        
        if error:
            logger.debug(f"ERROR: {error}")
            
        logger.debug(f"{'=' * 80}\n")
        
    def get_items(self, parent_id: Optional[str] = None) -> List[Dict]:
        """
        Get items from the Jellyfin server.
        
        Args:
            parent_id: Optional parent ID to filter items
            
        Returns:
            List of items
        """
        # Use the Items endpoint with proper filters
        url = f"{self.host}/Items"
        logger.debug("Using the Items endpoint with includeItemTypes=Season filter")
        
        params = {}
        if parent_id:
            params['parentId'] = parent_id
        
        # Always include item types filter if specified (even if empty list)
        if self.item_types is not None:
            params['includeItemTypes'] = ','.join(self.item_types)
            logger.debug(f"Filtering by item types: {self.item_types}")
        
        # Add additional parameters to get more items at once
        params['recursive'] = 'true'
        params['fields'] = 'Path,ProviderIds,SeriesName'
        params['limit'] = 1000
        
        try:
            logger.debug(f"Making request to {url} with params: {params}")
            
            if self.debug:
                logger.debug("===== GET ITEMS REQUEST DETAILS =====")
                logger.debug(f"URL: {url}")
                logger.debug(f"Headers: {self.headers}")
                logger.debug(f"Params: {params}")
                logger.debug("====================================")
                
            response = requests.get(url, headers=self.headers, params=params)
            
            # Dump request/response details if debug mode is enabled
            self._dump_request_response('GET', url, params, self.headers, response)
            
            response.raise_for_status()
            
            # Check if response is empty
            if not response.text:
                logger.error("Received empty response from server")
                return []
            
            try:
                data = response.json()
                return data.get('Items', [])
            except ValueError as e:
                # Check if we're getting an HTML response (likely a login page)
                if response.text.strip().startswith('<!DOCTYPE html>') or '<html' in response.text:
                    logger.error("Received HTML instead of JSON - your request is being redirected to an authentication page")
                    logger.error("This usually happens when your API key is invalid or when a reverse proxy/authentication system is intercepting the request")
                    
                    # Try to extract the login page URL
                    auth_url = None
                    if 'base href=' in response.text:
                        import re
                        base_match = re.search(r'<base href="([^"]+)"', response.text)
                        if base_match:
                            auth_url = base_match.group(1)
                    
                    if auth_url:
                        logger.error(f"Authentication system detected: {auth_url}")
                        logger.error("Please check your API key or authentication configuration")
                
                logger.error(f"Error parsing JSON response: {e}")
                
                if self.debug:
                    logger.debug("===== JSON PARSING ERROR DETAILS =====")
                    logger.debug(f"Response status code: {response.status_code}")
                    logger.debug(f"Response headers: {dict(response.headers)}")
                    logger.debug(f"Raw response content: '{response.text}'")
                    logger.debug(f"Response content length: {len(response.text)}")
                    logger.debug("=====================================")
                else:
                    logger.debug(f"Response content: {response.text[:200]}...")
                return []
                
        except RequestException as e:
            logger.error(f"Error getting items: {e}")
            
            # Log error details for Bad Request
            if "400 Client Error: Bad Request" in str(e):
                logger.error("Received 400 Bad Request error. This might be due to invalid parameters.")
            
            # Dump request/response details if debug mode is enabled
            self._dump_request_response('GET', url, params, self.headers, error=e)
            return []
    
    def refresh_item(self, item_id: str) -> bool:
        """
        Refresh metadata for a specific item.
        
        Args:
            item_id: Item ID to refresh
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.host}/Items/{item_id}/Refresh"
        
        params = {
            'metadataRefreshMode': self.refresh_mode,
            'imageRefreshMode': self.refresh_mode,
            'replaceAllMetadata': str(self.replace_all_metadata).lower(),
            'replaceAllImages': str(self.replace_all_images).lower(),
            'regenerateTrickplay': str(self.regenerate_trickplay).lower()
        }
        
        try:
            logger.debug(f"Refreshing item {item_id} with params: {params}")
            response = requests.post(url, headers=self.headers, params=params, timeout=30)
            
            # Dump request/response details if debug mode is enabled
            self._dump_request_response('POST', url, params, self.headers, response)
            
            # Check for successful status code
            if response.status_code == 204:
                # 204 No Content status code means success but with an empty response body (this is normal)
                logger.debug(f"Successfully refreshed item {item_id}")
                return True
            elif response.status_code == 401:
                logger.error(f"Authentication error (401) when refreshing item {item_id}. Check your API key.")
                return False
            elif response.status_code == 404:
                logger.error(f"Item not found (404) when refreshing item {item_id}.")
                return False
            else:
                response.raise_for_status()
                return True
                
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error when refreshing item {item_id}. The server might be busy.")
            self._dump_request_response('POST', url, params, self.headers, error=e)
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error when refreshing item {item_id}. Check your network connection and server URL.")
            self._dump_request_response('POST', url, params, self.headers, error=e)
            return False
        except RequestException as e:
            logger.error(f"Error refreshing item {item_id}: {e}")
            self._dump_request_response('POST', url, params, self.headers, error=e)
            return False
    
    def refresh_all_items(self, max_retries: int = 3) -> Dict[str, int]:
        """
        Refresh metadata for all items.
        
        Args:
            max_retries: Maximum number of retries for failed items
            
        Returns:
            Dictionary with count of successful and failed refreshes
        """
        # Get all items
        try:
            items = self.get_items()
            
            # Force filter items to only include seasons
            filtered_items = []
            for item in items:
                item_type = item.get('Type', 'Unknown')
                if item_type == 'Season':
                    filtered_items.append(item)
                else:
                    logger.debug(f"Filtering out non-Season item: {item.get('Name', 'Unknown')} (Type: {item_type})")
            
            items = filtered_items
            total_items = len(items)
            
            if total_items == 0:
                logger.warning("No Season items found to refresh. Check your server connection and user permissions.")
                return {'success': 0, 'failed': 0, 'skipped': 0}
                
            logger.info(f"Found {total_items} Season items to refresh")
            
            # Log item type distribution for debugging
            if self.debug:
                type_counts = {}
                for item in items:
                    item_type = item.get('Type', 'Unknown')
                    type_counts[item_type] = type_counts.get(item_type, 0) + 1
                
                logger.debug("Item type distribution:")
                for item_type, count in type_counts.items():
                    logger.debug(f"  - {item_type}: {count} items")
                
                if self.item_types:
                    logger.debug(f"Will only process items of types: {self.item_types}")
            
        except Exception as e:
            logger.error(f"Error getting items: {e}")
            return {'success': 0, 'failed': 0, 'skipped': 0}
        
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        failed_items = []
        
        # Process all items
        for i, item in enumerate(items, 1):
            item_id = item['Id']
            item_name = item.get('Name', 'Unknown')
            item_type = item.get('Type', 'Unknown')
            
            # Skip items that don't match our target types if item_types is specified
            if self.item_types and item_type not in self.item_types:
                logger.debug(f"Skipping {item_type}: {item_name} (ID: {item_id}) - not in target item types {self.item_types}")
                results['skipped'] += 1
                continue
                
            # Get the series name if available
            series_name = item.get('SeriesName', '')
            if series_name:
                logger.info(f"[{i}/{total_items}] Refreshing {item_type}: {series_name} - {item_name} (ID: {item_id})")
            else:
                logger.info(f"[{i}/{total_items}] Refreshing {item_type}: {item_name} (ID: {item_id})")
            
            # Try to refresh the item
            if self.refresh_item(item_id):
                results['success'] += 1
                # Include series name in success message if available
                series_name = item.get('SeriesName', '')
                if series_name:
                    logger.info(f"Successfully refreshed {series_name} - {item_name}")
                else:
                    logger.info(f"Successfully refreshed {item_name}")
            else:
                # Add to failed items for retry
                series_name = item.get('SeriesName', '')
                failed_items.append((item_id, item_name, item_type, series_name))
                if series_name:
                    logger.warning(f"Failed to refresh {series_name} - {item_name}, will retry later")
                else:
                    logger.warning(f"Failed to refresh {item_name}, will retry later")
            
            # Add delay between requests to avoid overwhelming the server
            if i < total_items:
                time.sleep(self.delay)
        
        # Retry failed items
        if failed_items:
            logger.info(f"Retrying {len(failed_items)} failed items...")
            
            for retry in range(max_retries):
                if not failed_items:
                    break
                    
                logger.info(f"Retry attempt {retry + 1}/{max_retries}")
                still_failed = []
                
                for item_id, item_name, item_type, series_name in failed_items:
                    if series_name:
                        logger.info(f"Retrying {item_type}: {series_name} - {item_name} (ID: {item_id})")
                    else:
                        logger.info(f"Retrying {item_type}: {item_name} (ID: {item_id})")
                    
                    # Try to refresh the item again
                    if self.refresh_item(item_id):
                        results['success'] += 1
                        if series_name:
                            logger.info(f"Successfully refreshed {series_name} - {item_name} on retry")
                        else:
                            logger.info(f"Successfully refreshed {item_name} on retry")
                    else:
                        still_failed.append((item_id, item_name, item_type, series_name))
                        if series_name:
                            logger.warning(f"Failed to refresh {series_name} - {item_name} on retry")
                        else:
                            logger.warning(f"Failed to refresh {item_name} on retry")
                    
                    # Add delay between requests
                    time.sleep(self.delay)
                
                # Update failed items list for next retry
                failed_items = still_failed
                
                if not failed_items:
                    logger.info("All retries successful!")
                    break
            
            # Update final count of failed items
            results['failed'] = len(failed_items)
            
            # Log failed items
            if failed_items:
                logger.warning(f"Failed to refresh {len(failed_items)} items after {max_retries} retries:")
                for item_id, item_name, item_type, series_name in failed_items:
                    if series_name:
                        logger.warning(f"  - {item_type}: {series_name} - {item_name} (ID: {item_id})")
                    else:
                        logger.warning(f"  - {item_type}: {item_name} (ID: {item_id})")
        
        return results

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Refresh metadata for Jellyfin items')
    
    # Required arguments
    parser.add_argument('--host', help='Jellyfin server URL')
    parser.add_argument('--api-key', help='Jellyfin API key')
    
    # Optional arguments
    parser.add_argument('--batch-size', type=int, default=20, help='Number of items to process in parallel')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between API requests in seconds')
    parser.add_argument('--refresh-mode', choices=['None', 'ValidationOnly', 'Default', 'FullRefresh'],
                        default='FullRefresh', help='Metadata refresh mode')
    parser.add_argument('--replace-all-metadata', action='store_true', help='Replace all metadata')
    parser.add_argument('--replace-all-images', action='store_true', help='Replace all images')
    parser.add_argument('--regenerate-trickplay', action='store_true', help='Regenerate trickplay images')
    parser.add_argument('--item-types', help='Comma-separated list of item types to refresh (default: Season)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode with request/response dumps')
    parser.add_argument('--run-once', action='store_true', help='Run once and exit (default is to run periodically)')
    parser.add_argument('--interval', type=int, default=30, help='Interval in minutes between refresh runs (default: 30)')
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    args = parse_arguments()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check for debug mode in environment variables
    debug_mode = args.debug or os.environ.get('DEBUG') is not None
    
    # If debug mode is enabled, force DEBUG log level
    if debug_mode:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled - request/response dumps will be shown")
    
    # Get configuration from environment variables if not provided as arguments
    host = args.host or os.environ.get('JELLYFIN_HOST')
    api_key = args.api_key or os.environ.get('JELLYFIN_API_KEY')
    
    # Check for environment variables for periodic execution
    run_once = args.run_once or os.environ.get('RUN_ONCE') is not None
    
    # Get interval from environment variable if not provided as argument
    interval = args.interval
    if os.environ.get('REFRESH_INTERVAL'):
        try:
            env_interval = int(os.environ.get('REFRESH_INTERVAL'))
            if env_interval > 0:
                interval = env_interval
        except ValueError:
            logger.warning("Invalid REFRESH_INTERVAL in environment variables. Using default.")
    
    # Validate required parameters
    if not host:
        logger.error("Jellyfin host is required. Provide it via --host argument or JELLYFIN_HOST environment variable.")
        return 1
    
    if not api_key:
        logger.error("Jellyfin API key is required. Provide it via --api-key argument or JELLYFIN_API_KEY environment variable.")
        return 1
    
    # Parse item types if provided
    item_types = None
    if args.item_types:
        item_types = [item_type.strip() for item_type in args.item_types.split(',')]
    
    # Create refresher instance
    refresher = JellyfinMetadataRefresher(
        host=host,
        api_key=api_key,
        batch_size=args.batch_size,
        delay=args.delay,
        refresh_mode=args.refresh_mode,
        replace_all_metadata=args.replace_all_metadata,
        replace_all_images=args.replace_all_images,
        regenerate_trickplay=args.regenerate_trickplay,
        item_types=item_types,
        debug=debug_mode
    )
    
    # Convert interval from minutes to seconds
    interval_seconds = interval * 60
    
    # Run once or periodically based on command line arguments or environment variables
    if run_once:
        return run_refresh(refresher)
    else:
        logger.info(f"Running in periodic mode. Will refresh metadata every {interval} minutes.")
        
        try:
            while True:
                # Run the refresh process
                run_refresh(refresher)
                
                # Wait for the next interval
                logger.info(f"Waiting {interval} minutes until the next refresh...")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt. Exiting...")
            return 0
    
    return 0

def run_refresh(refresher):
    """Run a single refresh process."""
    try:
        # Refresh all items
        logger.info("Starting metadata refresh process")
        start_time = time.time()
        results = refresher.refresh_all_items()
        end_time = time.time()
        
        # Log results
        logger.info(f"Metadata refresh completed in {end_time - start_time:.2f} seconds")
        logger.info(f"Successfully refreshed {results['success']} items")
        
        if 'skipped' in results and results['skipped'] > 0:
            logger.info(f"Skipped {results['skipped']} items")
            
        if results['failed'] > 0:
            logger.warning(f"Failed to refresh {results['failed']} items")
        else:
            logger.info("All items were refreshed successfully!")
        
        return 0
    except Exception as e:
        logger.error(f"Error during refresh process: {e}")
        logger.debug(f"Exception details: {str(e)}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
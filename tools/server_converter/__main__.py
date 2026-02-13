"""
CLI entry point for the server converter tool.
"""
import argparse
import logging
import sys
from pathlib import Path

from tools.server_converter.config import ServerConverterConfig
from tools.server_converter.converter import ServerConverter


def setup_logging(level: int = logging.INFO):
    """Configure logging for the server converter."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Server Converter - Process game responses from Redis to replay files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run server converter with config file
  server-converter config.json
  
  # Run with verbose logging
  server-converter config.json -v
  
  # Run for a limited number of iterations (useful for testing)
  server-converter config.json --max-iterations 10

Configuration file should contain:
  - redis: Redis connection and stream settings
  - storage: Hot storage directory and optional S3 cold storage settings
  - database: PostgreSQL database connection parameters
  - batch_size: Number of messages to process per batch (default: 10)
  - check_interval_seconds: Seconds to wait between checks (default: 5)
        """
    )
    
    parser.add_argument(
        'config',
        type=Path,
        help='Path to the configuration JSON file'
    )
    
    parser.add_argument(
        '--max-iterations',
        type=int,
        help='Maximum number of iterations to run (default: run forever)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging (DEBUG level)'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (only ERROR level)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    if args.quiet:
        log_level = logging.ERROR
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
        
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    # Load configuration
    try:
        config = ServerConverterConfig.from_file(args.config)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
        
    # Create and run converter
    try:
        converter = ServerConverter(config)
        converter.run(max_iterations=args.max_iterations)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running server converter: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

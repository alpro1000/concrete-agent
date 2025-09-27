#!/usr/bin/env python3
"""
TZD Reader CLI
Command line interface for Technical Assignment Reader
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path to import agents
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.tzd_reader.agent import tzd_reader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tzd_reader_cli.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="TZD Reader CLI - Technical Assignment Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tzd_reader_cli.py --files doc1.pdf doc2.docx --engine gpt
  python tzd_reader_cli.py --files *.pdf --engine claude --base-dir ./projects
  python tzd_reader_cli.py --files task.pdf --output result.json --verbose
        """
    )
    
    parser.add_argument(
        "--files", 
        nargs="+", 
        required=True,
        help="List of files to analyze (PDF, DOCX, TXT)"
    )
    
    parser.add_argument(
        "--engine",
        choices=["gpt", "claude"],
        default="gpt",
        help="AI engine to use (default: gpt)"
    )
    
    parser.add_argument(
        "--base-dir",
        type=str,
        help="Base directory for file access restriction"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (default: print to stdout)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    try:
        logger.info("Starting TZD Reader CLI")
        logger.info(f"Files to process: {args.files}")
        logger.info(f"AI engine: {args.engine}")
        if args.base_dir:
            logger.info(f"Base directory: {args.base_dir}")
        
        # Run analysis
        result = tzd_reader(
            files=args.files,
            engine=args.engine,
            base_dir=args.base_dir
        )
        
        # Format output
        output_json = json.dumps(result, ensure_ascii=False, indent=2)
        
        # Save or print result
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_json)
            logger.info(f"Results saved to: {args.output}")
        else:
            print(output_json)
        
        # Log summary
        metadata = result.get('processing_metadata', {})
        logger.info(f"✅ Analysis completed successfully")
        logger.info(f"   Files processed: {metadata.get('processed_files', 0)}")
        logger.info(f"   Processing time: {metadata.get('processing_time_seconds', 0)} seconds")
        logger.info(f"   AI model: {result.get('ai_model', 'unknown')}")
        
        if result.get('processing_error'):
            logger.warning("⚠️ Analysis completed with errors")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
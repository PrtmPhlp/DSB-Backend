#!/usr/bin/env python3
# ------------------------------------------------
"""
Example for runner as a module
"""

import argparse

from rich_argparse import RawDescriptionRichHelpFormatter

import format_json
import schema
import scraper
from logger import setup_logger

# DEFAULT VALUES
RAW_FILE = "json/scraped.json"
SCHEMA_FILE = "schema/schema.json"


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: An object containing the parsed arguments.
    """
    ascii_art = r"""
     ___      ___  ___ ___
    | _ \_  _|   \/ __| _ )
    |  _/ || | |) \__ \ _ \
    |_|  \_, |___/|___/___/
         |__/
    """
    parser = argparse.ArgumentParser(
        prog="python src/scraper.py",
        description=ascii_art +
        "\nThis script scrapes data from dsbmobile.com to retrieve class replacements.",
        # Ensures raw formatting for the art
        formatter_class=RawDescriptionRichHelpFormatter)
    parser.add_argument(
        "--version", action="version", version="[argparse.prog]%(prog)s[/] version [i]1.1.0[/]"
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Set verbosity level to DEBUG")
    parser.add_argument("-c", "--course", type=str, nargs="?", default="MSS12",
                        help="Select the course to scrape. Default: MSS12")
    parser.add_argument('-p', "--print-output",
                        action='store_true', help='Print output to console')
    parser.add_argument(
        "-o", "--output-dir", type=str, nargs="?", default="json/formatted.json",
        help="Output directory for JSON files. Default: json/formatted.json"
    )
    parser.add_argument(
        "-d", "--development", action="store_true", default=False,
        help="Dont exit when no changes are detected"
    )
    return parser.parse_args()


def main() -> bool:
    """Main function that orchestrates the scraping and processing of DSB data."""
    logger = setup_logger(__name__)

    # Parse arguments
    args: argparse.Namespace = parse_args()
    args.raw_file = RAW_FILE
    args.schema_file = SCHEMA_FILE
    logger.debug("Parsed arguments: %s", args)

    if args.verbose:
        logger.debug("Verbose mode enabled")

    # Scrape data
    changes_detected = scraper.main(args)

    if not changes_detected and not args.development:
        logger.info("No changes detected in scraped data. Exiting...")
        return True

    # Format data
    format_json.main(args.course, args.raw_file, args.output_dir)

    # Validate data
    schema.main(args.schema_file, args.output_dir)

    return True


if __name__ == "__main__":
    main()

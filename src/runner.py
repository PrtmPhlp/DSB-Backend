#!/usr/bin/env python3
# ------------------------------------------------
"""
Example for runner as a module
"""

import argparse
from rich_argparse import RawDescriptionRichHelpFormatter

import scraper
import format_json
import schema

INPUT_FILE = "json/scraped.json"
SCHEMA_FILE = "json/schema.json"


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
    return parser.parse_args()


args: argparse.Namespace = parse_args()
# print(args)

scraper.main(args)
format_json.main(args.course, INPUT_FILE, args.output_dir)
schema.main(SCHEMA_FILE, args.output_dir)

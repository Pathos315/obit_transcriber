#!/usr/bin/env python
import argparse

from src.config import DATA_DIR
from src.downloader import download_obituaries
from src.transcriber import transcribe_images


def setup_command_line_args():
    parser = argparse.ArgumentParser(
        prog="obitnav",
        description="Navigates the Bay Area Reporter obituary archives website, downloading obituaries or transcribing them.",
        epilog="Example usage: <...> download 1991 1999",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download obituaries")
    download_parser.add_argument(
        "yearfrom", type=str, help="Year to begin downloads from (e.g., 1991)"
    )
    download_parser.add_argument(
        "--yearto",
        type=str,
        nargs="?",
        help="End of range for downloads from (e.g., 1999)",
    )

    # Transcribe command
    process_parser = subparsers.add_parser(
        "transcribe", help="Transcribe obituary images"
    )
    process_parser.add_argument(
        "--directory",
        type=str,
        nargs="?",
        default=DATA_DIR,
        help="Directory with obituary images to be transcribed",
    )
    process_parser.add_argument(
        "--spellcheck", action="store_true", help="Apply spellchecking"
    )

    args = parser.parse_args()
    return parser, args


def execute_download(args: argparse.Namespace) -> None:

    if args.yearfrom and args.yearto:  # At least one argument must be provided
        download_obituaries(args.yearfrom, args.yearto)
    elif args.yearfrom and not args.yearto:
        # If only one argument is provided, set the year_to to the same value
        download_obituaries(args.yearfrom, args.yearfrom)
    else:
        print("Please provide a year to begin downloads from.")


def execute_transcription(args: argparse.Namespace) -> None:
    if args.directory:
        transcribe_images(args.directory, args.spellcheck)
    else:
        transcribe_images(DATA_DIR, args.spellcheck)


def main():
    parser, args = setup_command_line_args()

    if args.command == "download":
        execute_download(args)
    elif args.command == "transcribe":
        execute_transcription(args)
    else:
        parser.print_help()
        exit(1)


if __name__ == "__main__":
    main()

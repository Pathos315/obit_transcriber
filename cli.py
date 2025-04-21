# cli.py
import argparse

from obit_transcriber.obit_downloader import download_obituaries
from obit_transcriber.obit_transcriber import transcribe_images


def main():
    parser = argparse.ArgumentParser(description="Obituary Reader")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Download command
    download_parser = subparsers.add_parser("download", help="Download obituaries")
    download_parser.add_argument(
        "init_year", type=str, help="Year to begin downloads from (e.g., 1991)"
    )
    download_parser.add_argument(
        "end_year", type=str, help="End of range for downloads from (e.g., 1999)"
    )

    # Transcribe command
    process_parser = subparsers.add_parser(
        "transcribe", help="Transcribe obituary images"
    )
    process_parser.add_argument(
        "directory", type=str, help="Directory with obituary images to be transcribed"
    )
    process_parser.add_argument(
        "--spellcheck", action="store_true", help="Apply spellchecking"
    )

    args = parser.parse_args()

    if args.command == "download":
        download_obituaries(args.year)
    elif args.command == "process":
        transcribe_images(args.directory, args.spellcheck)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

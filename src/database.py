"""
Module for storing obituary data in a spreadsheet or database.

This module provides functionality to:
1. Store transcribed text from obituary images in a SQLite database
2. Associate images with their source URLs
3. Extract metadata from image filenames
4. Export data to CSV or Excel formats
"""

import csv
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.logger import logger


@dataclass
class ObituaryRecord:
    """Data class to store obituary information."""

    image_path: str
    text_content: str
    obituary_url: Optional[str] = None
    year: Optional[str] = None
    month: Optional[str] = None
    day: Optional[str] = None
    name: Optional[str] = None

    @classmethod
    def from_image_path(
        cls, image_path: str, text_content: str, obituary_url: Optional[str] = None
    ):
        """
        Create an ObituaryRecord from an image path, extracting metadata from the filename.

        Args:
            image_path: Path to the image file
            text_content: Transcribed text content
            obituary_url: Original URL of the obituary (optional)

        Returns:
            ObituaryRecord: A new ObituaryRecord with extracted metadata
        """
        # Extract filename without extension
        path = Path(image_path)
        filename = path.stem

        # Try to extract date components (assuming format like "19910110_Alt_Russell_Darl")
        year = month = day = name = None

        # If we have a pattern like YYYYMMDD_Name
        match = re.match(r"(\d{4})(\d{2})(\d{2})_(.*)", filename)
        if match:
            year, month, day, name = match.groups()

            name = format_name(name)  # Replace underscores with spaces for readability

        return cls(
            image_path=str(path),
            text_content=text_content,
            obituary_url=obituary_url,
            year=year,
            month=month,
            day=day,
            name=name,
        )


class ObituaryDatabase:
    """Class to handle database operations for obituary data."""

    def __init__(self, db_path: str = "obituaries.db"):
        """
        Initialize the database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        logger.info(f"Initialized database at {db_path}")

    def create_tables(self):
        """Create the necessary tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS obituaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            text_content TEXT NOT NULL,
            obituary_url TEXT,
            year TEXT,
            month TEXT,
            day TEXT,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        self.conn.commit()

    def add_record(self, record: ObituaryRecord) -> int:
        """
        Add a new obituary record to the database.

        Args:
            record: The ObituaryRecord to add

        Returns:
            int: The ID of the newly added record
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
        INSERT INTO obituaries
        (image_path, text_content, obituary_url, year, month, day, name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                record.image_path,
                record.text_content,
                record.obituary_url,
                record.year,
                record.month,
                record.day,
                record.name,
            ),
        )
        self.conn.commit()
        logger.debug(f"Added record for {record.image_path}")
        if cursor.lastrowid is None:
            raise ValueError("Failed to insert record into the database.")
        return cursor.lastrowid

    def get_all_records(self) -> List[ObituaryRecord]:
        """
        Retrieve all obituary records from the database.

        Returns:
            List[ObituaryRecord]: A list of all obituary records
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT image_path, text_content, obituary_url, year, month, day, name FROM obituaries"
        )
        rows = cursor.fetchall()

        return [
            ObituaryRecord(
                image_path=row[0],
                text_content=row[1],
                obituary_url=row[2],
                year=row[3],
                month=row[4],
                day=row[5],
                name=row[6],
            )
            for row in rows
        ]

    def search_records(self, query: str) -> List[ObituaryRecord]:
        """
        Search for obituary records matching the query.

        Args:
            query: Search query string

        Returns:
            List[ObituaryRecord]: A list of matching obituary records
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
        SELECT image_path, text_content, obituary_url, year, month, day, name
        FROM obituaries
        WHERE text_content LIKE ? OR name LIKE ?
        """,
            (f"%{query}%", f"%{query}%"),
        )
        rows = cursor.fetchall()

        return [
            ObituaryRecord(
                image_path=row[0],
                text_content=row[1],
                obituary_url=row[2],
                year=row[3],
                month=row[4],
                day=row[5],
                name=row[6],
            )
            for row in rows
        ]

    def get_record_by_image_path(self, image_path: str) -> Optional[ObituaryRecord]:
        """
        Get a record by its image path.

        Args:
            image_path: The image path to search for

        Returns:
            ObituaryRecord or None: The matching record, or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
        SELECT image_path, text_content, obituary_url, year, month, day, name
        FROM obituaries
        WHERE image_path = ?
        """,
            (image_path,),
        )
        row = cursor.fetchone()

        if row:
            return ObituaryRecord(
                image_path=row[0],
                text_content=row[1],
                obituary_url=row[2],
                year=row[3],
                month=row[4],
                day=row[5],
                name=row[6],
            )
        return None

    def update_url(self, image_path: str, url: str) -> bool:
        """
        Update the URL for a record.

        Args:
            image_path: The image path of the record to update
            url: The new URL

        Returns:
            bool: True if successful, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
        UPDATE obituaries
        SET obituary_url = ?
        WHERE image_path = ?
        """,
            (url, image_path),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def export_to_csv(self, output_path: str = "obituaries.csv"):
        """
        Export all obituary records to a CSV file.

        Args:
            output_path: Path to save the CSV file
        """
        records = self.get_all_records()

        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "image_path",
                "text_content",
                "obituary_url",
                "year",
                "month",
                "day",
                "name",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for record in records:
                writer.writerow(
                    {
                        "image_path": record.image_path,
                        "text_content": record.text_content,
                        "obituary_url": record.obituary_url,
                        "year": record.year,
                        "month": record.month,
                        "day": record.day,
                        "name": record.name,
                    }
                )

        logger.info(f"Exported {len(records)} records to {output_path}")

    def export_to_excel(self, output_path: str = "obituaries.xlsx"):
        """
        Export all obituary records to an Excel file.

        Args:
            output_path: Path to save the Excel file
        """
        records = self.get_all_records()

        df = pd.DataFrame(
            [
                {
                    "image_path": record.image_path,
                    "text_content": record.text_content,
                    "obituary_url": record.obituary_url,
                    "year": record.year,
                    "month": record.month,
                    "day": record.day,
                    "name": record.name,
                }
                for record in records
            ]
        )

        df.to_excel(output_path, index=False)  # type: ignore

        logger.info(f"Exported {len(records)} records to {output_path}")

    def close(self):
        """Close the database connection."""
        self.conn.close()
        logger.debug("Database connection closed")


def store_transcription(
    image_path: str,
    text_content: str,
    obituary_url: Optional[str] = None,
    db_path: Optional[str] = None,
) -> ObituaryRecord:
    """
    Store a transcription in the database.

    Args:
        image_path: Path to the image file
        text_content: Transcribed text content
        obituary_url: Original URL of the obituary (optional)
        db_path: Path to the database file (optional)

    Returns:
        ObituaryRecord: The stored obituary record
    """
    record = ObituaryRecord.from_image_path(image_path, text_content, obituary_url)

    if db_path:
        db = ObituaryDatabase(db_path)
        db.add_record(record)
        db.close()

    return record


def format_name(snake_case_name: str) -> str:
    """
    Convert a snake_case name to the format "Last, First Middle".

    Example:
        Alt_Russell_Darl => Alt, Russell Darl

    Args:
        snake_case_name: Name in snake_case format

    Returns:
        str: Formatted name
    """
    if not snake_case_name:
        return ""

    name_parts = snake_case_name.split("_")

    if len(name_parts) < 2:
        return snake_case_name

    last_name = name_parts[0]
    first_and_middle = " ".join(name_parts[1:])

    return f"{last_name}, {first_and_middle}"

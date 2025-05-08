"""
Module for storing obituary data in a spreadsheet or database.

This module provides functionality to:
1. Store transcribed text from obituary images in a SQLite database
2. Associate images with their source URLs
3. Extract metadata from image filenames
4. Export data to CSV or Excel formats
"""

import csv
from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
import re
import sqlite3
from typing import Any, List, Optional

from PIL import Image
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
    date_published: Optional[date] = None
    name: Optional[str] = None
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    image: Optional[bytes] = None

    @classmethod
    def from_image_path(
        cls,
        image_path: str,
        text_content: str,
        raw_image: Image.Image,
        obituary_url: Optional[str] = None,
    ):
        """
        Create an ObituaryRecord from an image path, extracting metadata from the filename.

        Args:
            image_path: Path to the image file
            text_content: Transcribed text content
            raw_image: The PIL Image object
            obituary_url: Original URL of the obituary (optional)

        Returns:
            ObituaryRecord: A new ObituaryRecord with extracted metadata
        """
        # Extract filename without extension
        path = Path(image_path)
        filename = path.stem

        # Try to extract date components (assuming format like "19910110_Alt_Russell_Darl")
        year = month = day = name = last_name = first_name = image_data = None
        date_published = None

        # Resize the image to a manageable size to reduce memory usage
        max_size = (1024, 1024)  # Example maximum dimensions
        raw_image.thumbnail(max_size)

        # Compress the image and save it to an in-memory buffer
        buffer = BytesIO()
        raw_image.save(
            buffer,
            format="JPEG",
            quality=85,
            optimize=True,
        )  # Adjust quality as needed
        image_data = buffer.getvalue()

        # If we have a pattern like YYYYMMDD_Name
        match = re.match(r"(\d{4})(\d{2})(\d{2})_(.*)", filename)
        if match:
            year, month, day, name = match.groups()

            # Create a date object if year, month, and day are valid
            try:
                date_published = date(int(year), int(month), int(day))
            except (ValueError, TypeError):
                # If the date is invalid, keep it as None
                date_published = None

            full_name, first_name, last_name = format_name(
                name
            )  # Replace underscores with spaces for readability
            name = full_name  # Assign the full name to the `name` variable

        return cls(
            image_path=str(path),
            text_content=text_content,
            obituary_url=obituary_url,
            year=year,
            month=month,
            day=day,
            date_published=date_published,
            name=name,
            last_name=last_name,
            first_name=first_name,
            image=image_data,
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
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")
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
            year CHAR(4),
            month CHAR(2),
            day CHAR(2),
            date_published DATE,
            name TEXT,
            last_name TEXT,
            first_name TEXT,
            image BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )
        self.conn.commit()

    def add_column_if_not_exists(
        self, table_name: str, column_name: str, column_type: str
    ):
        """
        Add a column to a table if it doesn't already exist.

        Args:
            table_name: Name of the table
            column_name: Name of the column to add
            column_type: SQL type of the column
        """
        cursor = self.conn.cursor()

        # Check if column exists
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [info[1] for info in cursor.fetchall()]

        if column_name not in columns:
            logger.info(f"Adding column {column_name} to table {table_name}")
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )
            self.conn.commit()

            # If we're adding a date_published column, populate it from existing data
            if (
                column_name == "date_published"
                and "year" in columns
                and "month" in columns
                and "day" in columns
            ):
                self.populate_date_published()
        else:
            logger.debug(f"Column {column_name} already exists in table {table_name}")

    def populate_date_published(self):
        """
        Populate the date_published column from year, month, and day columns.
        This is used when adding the date_published column to an existing table.
        """
        cursor = self.conn.cursor()

        # Get all records with year, month, day but no date_published
        cursor.execute(
            """
            SELECT id, year, month, day
            FROM obituaries
            WHERE date_published IS NULL
            AND year IS NOT NULL
            AND month IS NOT NULL
            AND day IS NOT NULL
            """
        )

        records = cursor.fetchall()
        updated_count = 0

        for record_id, year, month, day in records:
            try:
                # Create date object
                date_obj = date(int(year), int(month), int(day))

                # Update record
                cursor.execute(
                    "UPDATE obituaries SET date_published = ? WHERE id = ?",
                    (date_obj, record_id),
                )
                updated_count += 1
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not create date for record {record_id}: {e}")

        self.conn.commit()
        logger.info(f"Updated date_published for {updated_count} records")

    def add_record(self, record: ObituaryRecord) -> int:
        """
        Add a new obituary record to the database.

        Args:
            record: The ObituaryRecord to add

        Returns:
            int: The ID of the newly added record
        """
        # Ensure the date_published column exists
        self.add_column_if_not_exists("obituaries", "date_published", "DATE")

        cursor = self.conn.cursor()
        cursor.execute(
            """
        INSERT INTO obituaries
        (image_path, text_content, obituary_url, year, month, day, date_published, name, last_name, first_name, image)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                record.image_path,
                record.text_content,
                record.obituary_url,
                record.year,
                record.month,
                record.day,
                record.date_published,
                record.name,
                record.last_name,
                record.first_name,
                record.image,
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
            "SELECT image_path, text_content, obituary_url, year, month, day, date_published, name, last_name, first_name, image FROM obituaries"
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
                date_published=row[6],
                name=row[7],
                last_name=row[8],
                first_name=row[9],
                image=row[10],
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
        SELECT image_path, text_content, obituary_url, year, month, day, date_published, name, last_name, first_name, image
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
                date_published=row[6],
                name=row[7],
                last_name=row[8],
                first_name=row[9],
                image=row[10],
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
        SELECT image_path, text_content, obituary_url, year, month, day, date_published, name, last_name, first_name, image
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
                date_published=row[6],
                name=row[7],
                last_name=row[8],
                first_name=row[9],
                image=row[10],
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
                "date_published",
                "name",
                "last_name",
                "first_name",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for record in records:
                # Format the date as a string if it exists
                date_str = (
                    record.date_published.strftime("%B %d, %Y")
                    if record.date_published
                    else None
                )

                writer.writerow(
                    {
                        "image_path": record.image_path,
                        "text_content": record.text_content,
                        "obituary_url": record.obituary_url,
                        "year": record.year,
                        "month": record.month,
                        "day": record.day,
                        "date_published": date_str,
                        "name": record.name,
                        "last_name": record.last_name,
                        "first_name": record.first_name,
                    }
                    # Exclude the image field as it contains binary data and is not suitable for CSV export
                )

        logger.info(f"Exported {len(records)} records to {output_path}")

    def export_to_excel(self, output_path: str = "obituaries.xlsx"):
        """
        Export all obituary records to an Excel file.

        Args:
            output_path: Path to save the Excel file
        """
        records = self.get_all_records()

        # Convert date objects to formatted strings for Excel
        data: list[dict[str, Any]] = []
        for record in records:
            # Format the date as a string if it exists
            date_str = (
                record.date_published.strftime("%B %d, %Y")
                if record.date_published
                else None
            )

            data.append(
                {
                    "image_path": record.image_path,
                    "text_content": record.text_content,
                    "obituary_url": record.obituary_url,
                    "year": record.year,
                    "month": record.month,
                    "day": record.day,
                    "date_published": date_str,
                    "name": record.name,
                    "last_name": record.last_name,
                    "first_name": record.first_name,
                    # Exclude the image field as it contains binary data
                }
            )

        df = pd.DataFrame(data)
        # The `# type: ignore` is used here because the `pandas` library's type stubs may not fully support the `to_excel` method.
        df.to_excel(output_path, index=False)  # type: ignore

        logger.info(f"Exported {len(records)} records to {output_path}")

    def close(self):
        """Close the database connection."""
        try:
            self.conn.close()
            logger.debug("Database connection closed")
        except sqlite3.Error as e:
            logger.error(f"Error occurred while closing the database connection: {e}")


def store_transcription(
    image_path: str,
    text_content: str,
    raw_image: Image.Image,
    obituary_url: Optional[str] = None,
    db: Optional[ObituaryDatabase] = None,
    db_path: Optional[str] = None,
) -> ObituaryRecord:
    """
    Store a transcription in the database.

    Args:
        image_path: Path to the image file
        text_content: Transcribed text content
        raw_image: The PIL Image object
        obituary_url: Original URL of the obituary (optional)
        db: An existing ObituaryDatabase instance (optional)
        db_path: Path to the database file (optional, used if db is not provided)

    Returns:
        ObituaryRecord: The stored obituary record
    """
    record = ObituaryRecord.from_image_path(
        image_path, text_content, raw_image, obituary_url
    )

    if db is None and db_path:
        db = ObituaryDatabase(db_path)

    if db:
        db.add_record(record)

    return record


def format_name(
    snake_case_name: str,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Convert a snake_case name to a tuple of (full name, first name, last name).

    Example:
        Alt_Russell_Darl => ("Alt, Russell Darl", "Russell Darl", "Alt")

    Args:
        snake_case_name: Name in snake_case format

    Returns:
        tuple: A tuple containing the full name, first name, and last name
    """
    if not snake_case_name:
        return "", "", ""

    name_parts = snake_case_name.split("_")

    if len(name_parts) < 2:
        return snake_case_name, None, None

    last_name = name_parts[0].strip()
    first_and_middle = " ".join(name_parts[1:]).strip()
    full_name = f"{last_name}, {first_and_middle}"

    return full_name, first_and_middle, last_name


def add_date_column_to_existing_database(db_path: str = "obituaries.db"):
    """
    Add a date_published column to an existing database and populate it
    from the year, month, and day columns.

    Args:
        db_path: Path to the SQLite database file
    """
    # Open the database
    db = ObituaryDatabase(db_path)

    # Add the column (the method will handle checking if it already exists)
    db.add_column_if_not_exists("obituaries", "date_published", "DATE")

    # Populate the column from existing data
    db.populate_date_published()

    # Close the connection
    db.close()

    logger.info(f"Added and populated date_published column in {db_path}")

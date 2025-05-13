from pathlib import Path
import re
import time
from typing import List, Optional, Sequence, Tuple
from urllib.parse import unquote

from playwright.sync_api import Playwright, sync_playwright
import requests
from requests import adapters
import tqdm

import src.config as config
from src.logger import logger


def ensure_directory_exists(path: str | Path) -> Path:
    """Create directory if it doesn't exist and return the Path object.
    Args:
        path (str | Path): The directory path to create
    Returns:
        The direcrtory path as a Path object.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def extract_filename_from_url(obituary_url: str) -> Optional[str]:
    """
    Extract a clean filename from an obituary URL.

    Example:
    "http://obit.glbthistory.org/olo/display.jsp?name=19910110_Alt_Russell_Darl" ->
    "19910110_Alt_Russell_Darl"
    Args:
        obituary_url: The obituary URL to extract the filename from
    Returns:
        str | None: The extracted filename or None if extraction fails
    """
    # Extract the name parameter
    name_match = re.search(r"display\.jsp\?name=([^&]+)", obituary_url)
    return None if not name_match else unquote(name_match.group(1))


def run(
    playwright: Playwright, year_from: str = "1999", year_to: str = "2000"
) -> List[str | None]:
    """
    Run the Playwright browser to scrape obituary links from the GLBT History website.
    This function uses the Playwright library to automate the browser and extract
    obituary links from the search page.

    It navigates to the search page, sets the search parameters, and retrieves
    the links to the obituaries for the specified year.
    Returns a list of obituary links.

    Args:
        playwright: The Playwright instance to use for browser automation
        year: The year to search for obituaries (default is "1991")
    Raises:
        ValueError: If the year is not valid
    Returns:
        list[str]: A list of obituary links for the specified year
    Example:
    ```
    [
        "http://obit.glbthistory.org/olo/display.jsp?name=19910110_Alt_Russell_Darl",
        "http://obit.glbthistory.org/olo/display.jsp?name=19910111_Brown_James_E",
        ...
    ]

    """
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # Navigate to the search page
    logger.info(f"Navigating to the search page...")
    page.goto("http://obit.glbthistory.org/olo/index.jsp")

    # Set the search parameters
    page.locator('select[name="yearfrom"]').select_option(year_from)
    page.locator('select[name="monthto"]').select_option("12")
    page.locator('select[name="yearto"]').select_option(year_to)

    # Click the search button
    search_button = page.get_by_role(
        "cell",
        name=f"Select a date range to show all obituaries in the database within that range. From: January {year_from} To: December {year_to} Search",
        exact=True,
    ).get_by_role("button")
    search_button.click()
    links = page.get_by_role("link").all()

    # Filter out the "index.jsp" link
    obituary_links = [
        link.get_attribute("href")
        for link in links
        if link.get_attribute("href") != "index.jsp"
    ]

    context.close()
    browser.close()
    return obituary_links


def transform_url_to_image_path(display_url: str, index: int = 0) -> Optional[str]:
    """
    Transform a display URL to an image URL for the GLBT History obituary database.
    Now supports multiple image indices (0, 1, 2).

    Example:
    "http://obit.glbthistory.org/olo/display.jsp?name=19910110_Alt_Russell_Darl" ->
    "http://obit.glbthistory.org/olo/imagedb/1991/01/10/19910110_Alt_Russell_Darl/m19910110_0.jpg"

    Args:
        display_url: The display URL to transform
        index: The image index to use (0, 1, or 2)
    Returns:
        str | None: The transformed image URL or None if the transformation fails
    """
    # Extract the name parameter
    name_param = extract_filename_from_url(display_url)

    # Extract date components (assuming first 8 chars are YYYYMMDD)
    if not name_param:
        return None

    if len(name_param) < 8:
        return None

    date_str, year, month, day = extract_date_components(name_param)

    # Extract base domain
    base_domain_full = re.match(r"(https?://[^/]+/[^/]+)/", display_url)

    if not base_domain_full:
        return None

    base_domain = base_domain_full.group(1)

    # Construct the image URL with the specified index
    image_url: str = (
        f"{base_domain}/imagedb/{year}/{month}/{day}/{name_param}/m{date_str}_{index}.jpg"
    )

    return image_url


def extract_date_components(name_param: str) -> tuple[str, str, str, str]:
    """
    Extract date components from the name parameter.
    Args:
        name_param: The name parameter from the URL
    Returns:
        tuple[str, str, str, str]: A tuple containing the date string,
                                   year, month, and day
    Example:
        "19910110_Alt_Russell_Darl" -> ("19910110", "1991", "01", "10")
    """
    date_str = name_param[:8]
    year = date_str[:4]
    month = date_str[4:6]
    day = date_str[6:8]
    return date_str, year, month, day


def bulk_download_obituaries(obituary_links: Sequence[str]) -> None:
    """
    Download all obituaries from the list of links.
    This function creates a directory for saving the images and
    iterates through the list of obituary links to download each image.
    Args:
        obituary_links: List of obituary links to download
    Raises:
        requests.RequestException: If the download fails
        IOError: If file writing fails
    """
    # Create directory for saving images
    save_dir = config.DATA_DIR
    ensure_directory_exists(save_dir)

    # Process each obituary:
    for obituary_link in tqdm.tqdm(
        obituary_links,
        total=len(obituary_links),
        desc="Downloading obituaries: ",
        unit="obituary",
    ):
        with requests.Session() as client:
            configure_http_client(client)
            try:
                download_obituary_image(obituary_link, client)
            except Exception as e:
                logger.error(f"Error processing {obituary_link}: {e}")
                continue


def prepare_file_path(filename: str) -> Path:
    """
    Prepare the file path for saving the obituary image.

    Args:
        filename: The extracted filename from the URL

    Returns:
        Path: The file path where the image should be saved
    """
    # Extract year from the filename to determine directory
    if len(filename) >= 4:
        year = filename[:4]
        # Create year directory if it doesn't exist
        year_dir = config.DATA_DIR / year
        ensure_directory_exists(year_dir)
        return year_dir / f"{filename}.jpg"
    else:
        # Use base directory if year can't be determined
        return config.DATA_DIR / f"{filename}.jpg"


def download_single_image(
        href: str,
        index: int,
        file_path: Path,
        client: requests.Session,
        ) -> bool:
    """
    Attempt to download a single image with the specified index.

    Args:
        href: The base URL
        index: The image index to try
        file_path: The path where the image should be saved
        client: The HTTP client session

    Returns:
        bool: True if download succeeded, False otherwise
    """
    try:
        # Get the image URL with the specified index
        image_url = transform_url_to_image_path(href, index)
        if not image_url:
            logger.warning(f"Failed to transform URL to image path with index {index}")
            return False

        # Download the image
        contents = download_image(image_url, client)
        if contents is None:
            logger.warning(f"Failed to download image from URL: {image_url}")
            return False

        # Adjust file path for alternative indices
        actual_file_path = file_path
        if index > 0:
            actual_file_path = file_path.with_stem(f"{file_path.stem}_{index}")

        # Save the image
        with open(actual_file_path, "wb") as f:
            f.write(contents)

        logger.debug(f"Downloaded {image_url} to {actual_file_path}")
        return True

    except requests.RequestException as e:
        logger.warning(f"Failed to download with index {index}: {e}")
        return False


def try_alternative_indices(href: str, file_path: Path, client: requests.Session) -> int:
    """
    Try downloading images with alternative indices (1 and 2).

    Args:
        href: The base URL
        file_path: The path where the image should be saved
        client: The HTTP client session

    Returns:
        int: The number of successful downloads
    """
    success_count = 0

    for index in [1, 2]:
        if download_single_image(href, index, file_path, client):
            success_count += 1

    return success_count


def download_obituary_image(obituary_link: str, client: requests.Session) -> None:
    """
    Download an obituary image and save it to disk in the appropriate year folder.
    If index 0 fails, it will try to download both index 1 and index 2.

    Args:
        obituary_link: Link to the obituary page
        client: Configured HTTP client session

    Raises:
        ValueError: If URL transformation fails
        requests.RequestException: If all download attempts fail
        IOError: If file writing fails
    """
    try:
        # Prepare the base URL
        href = f"http://obit.glbthistory.org/olo/{obituary_link}"

        # Extract filename from URL
        filename = extract_filename_from_url(href)
        if not filename:
            raise ValueError(f"Failed to extract filename from URL: {href}")

        # Prepare file path
        file_path = prepare_file_path(filename)

        # First try with index 0
        if download_single_image(href, 0, file_path, client):
            return  # Success with index 0, no need to try others

        # If index 0 failed, try alternative indices
        logger.warning(f"Failed to download with index 0. Trying indices 1 and 2...")
        success_count = try_alternative_indices(href, file_path, client)

        # Check if at least one alternative download succeeded
        if success_count == 0:
            raise ValueError(f"Failed to download obituary image with any index for {filename}")
        else:
            logger.info(f"Successfully downloaded {success_count} alternative images for {filename}")

    except Exception as e:
        logger.error(f"Failed to download obituary image: {e}")
        raise


def download_image(image_url: str, client: requests.Session) -> Optional[bytes]:
    """
    Download the image from the given URL using the provided HTTP client.
    This function handles the actual HTTP request and response.

    Args:
        image_url: URL of the image to download
        client: Configured HTTP client session
    Returns:
        bytes: The content of the downloaded image
    Raises:
        requests.RequestException: If the download fails
        IOError: If file writing fails
    """
    # Ensure the URL is valid
    if not image_url.startswith("http"):
        logger.error(f"Invalid URL: {image_url}")
        return None
    try:
        response = client.get(
            image_url,
            timeout=config.REQUEST_TIMEOUT,
        )
        time.sleep(
            config.RATE_LIMIT_DELAY
        )  # Rate limit to avoid overwhelming the server
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logger.error(f"Failed to download {image_url}: {e}")
        raise


def build_image_download_path(obituary_link: str) -> Tuple[Path, str]:
    """
    Build the image download path and URL for a given obituary link.
    This function is used to determine where to save the downloaded image
    and the URL to download it from.
    Args:
        obituary_link: Link to the obituary page
    Returns:
        tuple[Path, str]: A tuple containing the file path and image URL
    """
    href = f"http://obit.glbthistory.org/olo/{obituary_link}"
    filename = extract_filename_from_url(href)
    file_path: Path = config.DATA_DIR / f"{filename}.jpg"
    image_url: str = transform_url_to_image_path(href)  # type: ignore
    return file_path, image_url


def configure_http_client(client: requests.Session) -> None:
    """
    Configure the HTTP client with a custom adapter and headers.
    This is used to set up connection pooling and other settings.
    Args:
        client: The HTTP client session to configure
    """
    adapter = adapters.HTTPAdapter(
        pool_connections=25, pool_maxsize=25, pool_block=True
    )
    client.mount("http://", adapter)
    client.mount("https://", adapter)
    client.headers.update(
        {
            "User-Agent": config.USER_AGENT,
        }
    )


def download_obituaries(year_from: str, year_to: str) -> None:
    """
    Main function to download obituaries.
    This function initializes the Playwright browser, scrapes the obituary links,
    and downloads the images for each obituary.
    """
    with sync_playwright() as playwright:
        obituary_links = run(playwright, year_from, year_to)
        bulk_download_obituaries(obituary_links)  # type: ignore

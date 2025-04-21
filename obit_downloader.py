import re
import time
from pathlib import Path
from urllib.parse import unquote

import config
import requests
import tqdm
from logger import logger
from playwright.sync_api import Playwright, sync_playwright


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


def extract_filename_from_url(obituary_url: str) -> str | None:
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
    playwright: Playwright, init_year: str = "1999", end_year: str = "2000"
) -> list[str]:
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
    page.locator('select[name="yearfrom"]').select_option(init_year)
    page.locator('select[name="monthto"]').select_option("12")
    page.locator('select[name="yearto"]').select_option(end_year)

    # Click the search button
    search_button = page.get_by_role(
        "cell",
        name=f"Select a date range to show all obituaries in the database within that range. From: January {init_year} To: December {end_year} Search",
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


def transform_url_to_image_path(display_url: str) -> str | None:
    """
    Transform a display URL to an image URL for the GLBT History obituary database.

    Example:
    "http://obit.glbthistory.org/olo/display.jsp?name=19910110_Alt_Russell_Darl" ->
    "http://obit.glbthistory.org/olo/imagedb/1991/01/10/19910110_Alt_Russell_Darl/m19910110_0.jpg"

    Args:
        display_url: The display URL to transform
    Returns:
        str | None: The transformed image URL or None if the transformation fails
    """
    # Extract the name parameter
    name_param = extract_filename_from_url(display_url)

    # Extract date components (assuming first 8 chars are YYYYMMDD)
    if len(name_param) < 8:
        return None

    date_str, year, month, day = extract_date_components(name_param)

    # Extract base domain
    base_domain = re.match(r"(https?://[^/]+/[^/]+)/", display_url).group(1)

    # Construct the image URL
    image_url: str = (
        f"{base_domain}/imagedb/{year}/{month}/{day}/{name_param}/m{date_str}_0.jpg"
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


def bulk_download_obituaries(obituary_links: list[str]) -> None:
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


def download_obituary_image(obituary_link: str, client: requests.Session) -> None:
    """
    Download an obituary image and save it to disk in the appropriate year folder.

    Args:
        obituary_link: Link to the obituary page
        client: Configured HTTP client session

    Raises:
        ValueError: If URL transformation fails
        requests.RequestException: If download fails
        IOError: If file writing fails
    """
    try:
        href = f"http://obit.glbthistory.org/olo/{obituary_link}"
        filename = extract_filename_from_url(href)
        if not filename:
            raise ValueError(f"Failed to extract filename from URL: {href}")

        # Extract year from the filename to determine directory
        if len(filename) >= 4:
            year = filename[:4]
            # Create year directory if it doesn't exist
            year_dir = config.DATA_DIR / year
            ensure_directory_exists(year_dir)
            file_path = year_dir / f"{filename}.jpg"
        else:
            # Use base directory if year can't be determined
            file_path = config.DATA_DIR / f"{filename}.jpg"

        # Get the image URL
        image_url = transform_url_to_image_path(href)
        if not image_url:
            raise ValueError(f"Failed to transform URL to image path: {href}")

        # Download and save the image
        contents = download_image(image_url, client)

        with open(file_path, "wb") as f:
            f.write(contents)

        logger.debug(f"Downloaded {image_url} to {file_path}")
    except Exception as e:
        logger.error(f"Failed to download obituary image: {e}")
        raise


def download_image(image_url: str, client: requests.Session) -> bytes:
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


def build_image_download_path(obituary_link: str) -> tuple[Path, str]:
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
    image_url: str = transform_url_to_image_path(href)
    return file_path, image_url


def configure_http_client(client: requests.Session) -> None:
    """
    Configure the HTTP client with a custom adapter and headers.
    This is used to set up connection pooling and other settings.
    Args:
        client: The HTTP client session to configure
    """
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=25, pool_maxsize=25, pool_block=True
    )
    client.mount("http://", adapter)
    client.mount("https://", adapter)
    client.headers.update(
        {
            "User-Agent": config.USER_AGENT,
        }
    )


def download_obituaries() -> None:
    """
    Main function to download obituaries.
    This function initializes the Playwright browser, scrapes the obituary links,
    and downloads the images for each obituary.
    """
    with sync_playwright() as playwright:
        obituary_links = run(playwright)
        bulk_download_obituaries(obituary_links)


if __name__ == "__main__":
    download_obituaries()

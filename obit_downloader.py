import os
from pathlib import Path
import re
import time
from urllib.parse import unquote

import requests
from playwright.sync_api import Playwright, sync_playwright

YEAR = input(
    "Enter the desired year (e.g. 1980, 1991): "
)  # Change this to the desired year


client = requests.sessions.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=25, pool_maxsize=25, pool_block=True
)
client.mount("http://", adapter)
client.mount("https://", adapter)
client.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
)


def ensure_directory_exists(path: str | Path) -> Path:
    """Create directory if it doesn't exist and return the Path object."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def extract_filename_from_url(obituary_url):
    """
    Extract a clean filename from an obituary URL.

    Example:
    "http://obit.glbthistory.org/olo/display.jsp?name=19910110_Alt_Russell_Darl" ->
    "19910110_Alt_Russell_Darl.jpg"
    """
    # Extract the name parameter
    name_match = re.search(r"display\.jsp\?name=([^&]+)", obituary_url)
    if not name_match:
        return None
    return unquote(name_match.group(1))


def run(playwright: Playwright) -> list[str]:
    """
    Run the Playwright browser to scrape obituary links from the GLBT History website.
    This function uses the Playwright library to automate the browser and extract
    obituary links from the search page.

    It navigates to the search page, sets the search parameters, and retrieves
    the links to the obituaries for the specified year.
    Returns a list of obituary links.

    :param playwright: Playwright instance
    :return: List of obituary links

    Example:
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
    print(f"Navigating to the search page...")
    page.goto("http://obit.glbthistory.org/olo/index.jsp")

    # Set the search parameters
    page.locator('select[name="yearfrom"]').select_option(YEAR)
    page.locator('select[name="monthto"]').select_option("12")
    page.locator('select[name="yearto"]').select_option(YEAR)

    # Click the search button
    search_button = page.get_by_role(
        "cell",
        name=f"Select a date range to show all obituaries in the database within that range. From: January {YEAR} To: December {YEAR} Search",
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
    """
    # Extract the name parameter
    name_param = extract_filename_from_url(display_url)

    # Extract date components (assuming first 8 chars are YYYYMMDD)
    if len(name_param) < 8:
        return None

    date_str = name_param[:8]
    year = date_str[:4]
    month = date_str[4:6]
    day = date_str[6:8]

    # Extract base domain
    base_domain = re.match(r"(https?://[^/]+/[^/]+)/", display_url).group(1)

    # Construct the image URL
    image_url = (
        f"{base_domain}/imagedb/{year}/{month}/{day}/{name_param}/m{date_str}_0.jpg"
    )

    return image_url


def bulk_download_obituaries(obituary_links: list[str]) -> None:
    """
    Download all obituaries from the list of links.
    """
    print(f"Found {len(obituary_links)} obituary links")
    with open("obituary_links.txt", "w") as f:
        f.writelines(obituary_links)

    # Create directory for saving images
    save_dir = f"obituaries/{YEAR}"
    ensure_directory_exists(save_dir)

    # Process each obituary:
    for i, obituary_link in enumerate(obituary_links):
        try:
            print(f"Processing {i + 1}/{len(obituary_links)}: {obituary_link}")
            href = f"http://obit.glbthistory.org/olo/{obituary_link}"
            image_url = transform_url_to_image_path(href)

            filename = extract_filename_from_url(href)
            file_path = os.path.join(save_dir, f"{filename}.jpg")

            with open(file_path, "wb") as f:
                response = client.get(image_url)
                f.write(response.content)
                time.sleep(1)  # Rate limit to avoid overwhelming the server

        except Exception as e:
            print(f"Error processing {obituary_link}: {e}")
            continue


if __name__ == "__main__":
    with sync_playwright() as playwright:
        obituary_links = run(playwright)
        bulk_download_obituaries(obituary_links)

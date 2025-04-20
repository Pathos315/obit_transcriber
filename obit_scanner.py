import os
import re
import time
from urllib.parse import unquote

import requests
from playwright.sync_api import Playwright, sync_playwright

YEAR = input(
    "Enter the desired year (e.g. 1980, 1991): "
)  # Change this to the desired year


def ensure_directory_exists(path):
    """Create directory if it doesn't exist"""
    if not os.path.exists(path):
        os.makedirs(path)


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

    # Get and decode the name parameter
    name_param = unquote(name_match.group(1))

    # Create the filename
    filename = f"{name_param}.jpg"

    return filename


def run(playwright: Playwright) -> list[str]:
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


def transform_url_to_image_path(display_url):
    """
    Transform a display URL to an image URL for the GLBT History obituary database.

    Example:
    "http://obit.glbthistory.org/olo/display.jsp?name=19910110_Alt_Russell_Darl" ->
    "http://obit.glbthistory.org/olo/imagedb/1991/01/10/19910110_Alt_Russell_Darl/m19910110_0.jpg"
    """
    # Extract the name parameter
    name_match = re.search(r"display\.jsp\?name=([^&]+)", display_url)
    if not name_match:
        return None

    # Get and decode the name parameter
    name_param = unquote(name_match.group(1))

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


def bulk_download_obituaries(obituary_links: list[str]):
    """
    Download all obituaries from the list of links.
    """
    print(f"Found {len(obituary_links)} obituary links")
    with open("obituary_links.txt", "w") as f:
        f.writelines(obituary_links)

    # Create directory for saving images
    save_dir = f"obituaries/{YEAR}"
    ensure_directory_exists(save_dir)

    # Process each obituary
    with requests.sessions.Session() as session:
        for i, obituary_link in enumerate(obituary_links):
            try:
                print(f"Processing {i + 1}/{len(obituary_links)}: {obituary_link}")
                href = f"http://obit.glbthistory.org/olo/{obituary_link}"
                image_url = transform_url_to_image_path(href)

                filename = extract_filename_from_url(href)
                file_path = os.path.join(save_dir, f"{filename}")

                with open(file_path, "wb") as f:
                    response = session.get(image_url)
                    f.write(response.content)
                    time.sleep(1)  # Rate limit to avoid overwhelming the server

            except Exception as e:
                print(f"Error processing {obituary_link}: {e}")
                continue


if __name__ == "__main__":
    with sync_playwright() as playwright:
        obituary_links = run(playwright)
        bulk_download_obituaries(obituary_links)

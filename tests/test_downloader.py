from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.downloader import download_obituary_image


@patch("src.downloader.ensure_directory_exists")
@patch("src.downloader.download_image")
@patch("builtins.open", new_callable=MagicMock)
def test_download_obituary_image_success(
    mock_open, mock_download_image, mock_ensure_directory_exists
):
    # Mock configuration
    mock_client = MagicMock(spec=requests.Session)
    mock_download_image.return_value = b"image_data"
    mock_ensure_directory_exists.return_value = Path("/mock/path")

    # Mock functions
    obituary_link = "display.jsp?name=19910110_Alt_Russell_Darl"
    mock_image_url = "http://obit.glbthistory.org/olo/imagedb/1991/01/10/19910110_Alt_Russell_Darl/m19910110_0.jpg"

    with patch(
        "src.downloader.extract_filename_from_url",
        return_value="19910110_Alt_Russell_Darl",
    ):
        with patch(
            "src.downloader.transform_url_to_image_path", return_value=mock_image_url
        ):
            # Call the function
            download_obituary_image(obituary_link, mock_client)

    # Assertions
    mock_ensure_directory_exists.assert_called_once_with(Path("/mock/path/1991"))
    mock_download_image.assert_called_once_with(mock_image_url, mock_client)
    mock_open.assert_called_once_with(
        Path("/mock/path/1991/19910110_Alt_Russell_Darl.jpg"), "wb"
    )
    mock_open().write.assert_called_once_with(b"image_data")


@patch("src.downloader.download_image")
def test_download_obituary_image_invalid_filename(mock_download_image):
    mock_client = MagicMock(spec=requests.Session)
    obituary_link = "invalid_link"

    with patch("src.downloader.extract_filename_from_url", return_value=None):
        with pytest.raises(
            ValueError,
            match="Failed to extract filename from URL: http://obit.glbthistory.org/olo/invalid_link",
        ):
            download_obituary_image(obituary_link, mock_client)

    mock_download_image.assert_not_called()


@patch("src.downloader.download_image")
def test_download_obituary_image_invalid_image_url(mock_download_image):
    mock_client = MagicMock(spec=requests.Session)
    obituary_link = "display.jsp?name=19910110_Alt_Russell_Darl"

    with patch(
        "src.downloader.extract_filename_from_url",
        return_value="19910110_Alt_Russell_Darl",
    ):
        with patch("src.downloader.transform_url_to_image_path", return_value=None):
            with pytest.raises(
                ValueError,
                match="Failed to transform URL to image path: http://obit.glbthistory.org/olo/display.jsp?name=19910110_Alt_Russell_Darl",
            ):
                download_obituary_image(obituary_link, mock_client)

    mock_download_image.assert_not_called()


@patch("src.downloader.download_image")
def test_download_obituary_image_download_failure(mock_download_image):
    mock_client = MagicMock(spec=requests.Session)
    obituary_link = "display.jsp?name=19910110_Alt_Russell_Darl"
    mock_image_url = "http://obit.glbthistory.org/olo/imagedb/1991/01/10/19910110_Alt_Russell_Darl/m19910110_0.jpg"

    mock_download_image.return_value = None

    with patch(
        "src.downloader.extract_filename_from_url",
        return_value="19910110_Alt_Russell_Darl",
    ):
        with patch(
            "src.downloader.transform_url_to_image_path", return_value=mock_image_url
        ):
            with pytest.raises(
                ValueError,
                match="Failed to download image from URL: http://obit.glbthistory.org/olo/imagedb/1991/01/10/19910110_Alt_Russell_Darl/m19910110_0.jpg",
            ):
                download_obituary_image(obituary_link, mock_client)


def test_download_image_success(mock_sleep):
    mock_client = MagicMock(spec=requests.Session)
    mock_response = MagicMock()
    mock_response.content = b"image_data"
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    # Add import for config
    from src import config

    image_url = "http://example.com/image.jpg"
    result = download_image(image_url, mock_client)

    mock_client.get.assert_called_once_with(image_url, timeout=config.REQUEST_TIMEOUT)
    mock_response.raise_for_status.assert_called_once()
    assert result == b"image_data"


@patch("src.downloader.time.sleep", return_value=None)
def test_download_image_invalid_url(mock_sleep):
    mock_client = MagicMock(spec=requests.Session)
    image_url = "invalid_url"

    result = download_image(image_url, mock_client)

    mock_client.get.assert_not_called()
    assert result is None


@patch("src.downloader.time.sleep", return_value=None)
def test_download_image_request_exception(mock_sleep):
    mock_client = MagicMock(spec=requests.Session)
    mock_client.get.side_effect = requests.RequestException("Request failed")

    image_url = "http://example.com/image.jpg"

    with pytest.raises(requests.RequestException, match="Request failed"):
        download_image(image_url, mock_client)

    mock_client.get.assert_called_once_with(image_url, timeout=config.REQUEST_TIMEOUT)


@patch("src.downloader.time.sleep", return_value=None)
def test_download_image_http_error(mock_sleep):
    mock_client = MagicMock(spec=requests.Session)
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("HTTP error")
    mock_client.get.return_value = mock_response

    image_url = "http://example.com/image.jpg"

    with pytest.raises(requests.HTTPError, match="HTTP error"):
        download_image(image_url, mock_client)

    mock_client.get.assert_called_once_with(image_url, timeout=config.REQUEST_TIMEOUT)
    mock_response.raise_for_status.assert_called_once()

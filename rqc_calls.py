from datetime import datetime, timezone

import requests
from requests import RequestException

from plugins.rqc_adapter.config import API_VERSION, API_BASE_URL, REQUEST_TIMEOUT
from plugins.rqc_adapter.plugin_settings import VERSION
from utils.models import Version


def call_mhs_apikeycheck(journal_id: str, api_key: str) -> dict:
    """
    Verify API key with the RQC service.

    Args:
        journal_id: The ID of the journal to check
        api_key: The API key to validate

    Returns:
        int: HTTP status code on simple success
        dict: Response data if available and valid

    Raises:
        RequestException: If the request fails
    TODO:
        Display error to the user. Improve error handling...
    """
    url = f'{API_BASE_URL}/mhs_apikeycheck/{journal_id}'
    return call_rqc_api(url, api_key)

def call_mhs_submission(journal_id: str, api_key: str, submission_id, post_data: str) -> dict:
    """
    TODO
    """
    url = f'{API_BASE_URL}/mhs_submission/{journal_id}/{submission_id}'
    return call_rqc_api(journal_id, api_key, use_post=True, post_data=post_data)


def call_rqc_api(url: str, api_key: str, use_post=False, post_data=None) -> dict:
    result = {
        "success": False,
        "http_status_code": None,
        "message": None,
    }

    try:
        #database access somewhere else is better
        current_version = Version.objects.all().order_by('-number').first()
        if not current_version:
            raise ValueError("No version information available")

        headers = {
            'X-Rqc-Api-Version': API_VERSION,
            'X-Rqc-Mhs-Version': f'Janeway {current_version.number}',
            'X-Rqc-Mhs-Adapter': f'RQC-Adapter {VERSION}',
            'X-Rqc-Time': datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z',
            'Authorization': f'Bearer {api_key}',
        }

        if use_post:
            response = requests.post(
                url,
                json=post_data,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
        else:
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

        result["http_status_code"] = response.status_code
        result["success"] = response.ok
        try:
            response_data = response.json()
            if "user_message" in response_data:
                result["message"] = response_data["user_message"]
            elif "error" in response_data:
                result["message"] = response_data["error"]
            # Return info if json exists but no message - is this needed?
            elif not response.ok:
                result["message"] = f"Request failed: {response.reason}"
        except ValueError:
            result["message"] = f"Request failed and no error message was provided. Request status: {response.reason}"
        return result

    except RequestException as e:
        result["message"] = f"Connection Error: {str(e)}"
        return result




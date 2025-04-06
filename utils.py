import base64
import os
from datetime import datetime, timezone

import requests
from requests import RequestException

from django.conf import settings

from core.models import SettingValue
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
    TBD:
        Display error to the user. Improve error handling...
    """
    url = f'{API_BASE_URL}/mhs_apikeycheck/{journal_id}'
    return call_rqc_api(url, api_key)

def set_journal_id(journal_id: str) -> dict:
    """
    Set the journal id.

    Args:
        journal_id: The journal ID to set

    Returns:
        A dictionary with status and message

    Raises:
        SettingValue.DoesNotExist: If the setting doesn't exist
    """
    if not journal_id or not isinstance(journal_id, str):
        return {"status": "error", "message": "Invalid journal ID"}

    try:
        journal_id_setting = SettingValue.objects.get(setting__name='rqc_journal_id')
        journal_id_setting.value = journal_id
        journal_id_setting.save()
        return {"status": "success", "message": "Journal Id updated successfully"}
    except SettingValue.DoesNotExist:
        return {"status": "error", "message": "Journal Id setting not found"}
    except Exception as e:
        return {"status": "error", "message": f"Error updating journal Id: {str(e)}"}

def set_journal_api_key(journal_api_key: str) -> dict:
    """
    Set the journal API key.
    Args:
        journal_api_key: The API key to set
    Returns:
        A dictionary with status and message
    Raises:
        SettingValue.DoesNotExist: If the setting doesn't exist'
    """
    if not journal_api_key or not isinstance(journal_api_key, str):
        return {"status": "error", "message": "Invalid journal API key"}
    try:
        journal_api_key_setting = SettingValue.objects.get(setting__name='rqc_journal_api_key')
        journal_api_key_setting.value = journal_api_key
        journal_api_key_setting.save()
        return {"status": "success", "message": "Journal API key updated successfully"}
    except SettingValue.DoesNotExist:
        return {"status": "error", "message": "Journal API key setting not found"}
    except Exception as e:
        return {"status": "error", "message": f"Error updating journal API key: {str(e)}"}


def call_mhs_submission(journal_id: str, api_key: str, submission_id, post_data: str) -> dict:
    """
    TBD
    """
    url = f'{API_BASE_URL}/mhs_submission/{journal_id}/{submission_id}'
    return call_rqc_api(journal_id, api_key, use_post = True, post_data = post_data)



def call_rqc_api(url: str, api_key: str, use_post = False, post_data = None) -> dict:
    result = {
        "success": False,
        "http_status_code": None,
        "message": None,
    }

    try:
        #database access somewhere else is better
        current_version = Version.objects.all().order_by('-Number').first()
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

#TBD Error handling
def encode_file_as_b64(file_uuid: str, article_id: str) -> str:
    """
    Encodes the file as a base64 binary string.
    """
    file_path = os.path.join(settings.BASE_DIR,'files','articles', article_id, file_uuid)
    with open(file_path, "rb") as f:
        encoded_file = base64.b64encode(f.read()).decode('utf-8')
    return encoded_file
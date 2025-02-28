from typing import Union
from datetime import datetime, timezone

import requests
from requests import RequestException

from core.models import SettingValue
from plugins.rqc_adapter.config import API_VERSION, API_BASE_URL
from plugins.rqc_adapter.plugin_settings import VERSION
from utils.models import Version

def call_mhs_apikeycheck(journal_id: str, api_key: str) -> Union[int, dict]:
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
    """
    try:
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

        response = requests.get(
            f'{API_BASE_URL}/mhs_apikeycheck/{journal_id}',
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        try:
            return response.json()
        except ValueError:
            return response.status_code

    except RequestException as e:
        print(f"API request failed: {str(e)}")
        raise

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
        return {"status": "success", "message": "Journal ID updated successfully"}
    except SettingValue.DoesNotExist:
        return {"status": "error", "message": "Journal ID setting not found"}
    except Exception as e:
        return {"status": "error", "message": f"Error updating journal ID: {str(e)}"}

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


def call_mhs_submission(journal_id: str, journal_api_key: str):
    """
    TBD
    """
    return
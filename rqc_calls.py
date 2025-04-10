import base64
import hashlib
import os
import random
import string
from datetime import datetime, timezone

import requests
from requests import RequestException

from django.conf import settings

from core.models import SettingValue, Setting
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


#TODO Error handling
def encode_file_as_b64(file_uuid: str, article_id: str) -> str:
    """
    Encodes the file as a base64 binary string.
    """
    file_path = os.path.join(settings.BASE_DIR, 'files', 'articles', article_id, file_uuid)
    with open(file_path, "rb") as f:
        encoded_file = base64.b64encode(f.read()).decode('utf-8')
    return encoded_file


def convert_review_decision_to_rqc_format(decision_string: str) -> str:
    """
    Maps the string representation of the reviewers decision to the string representation in RQC.
    """
    match decision_string:
        case 'Accept Without Revisions':
            return 'ACCEPT'
        case 'Minor Revisions Required':
            return 'MINORREVISION'
        case 'Major Revisions Required':
            return 'MAJORREVISION'
        case 'Reject':
            return 'REJECT'
        case _:
            return ''


# TODO datetime correct?
def get_editorial_decision(article):
    """
    Gets the (most recent) editorial decision for the article. The default is empty "".
    TODO: to get the recent editorial decision i have to iterate over the stage history of the article
    :param article: Article object
    :return string of the editorial decision
    """
    stages = article.stage_log_set.all().order_by('-date_time')
    for stage in stages:
        if stage.stage_to == 'Accepted':
            return 'ACCEPTED'
        elif stage.stage_to == 'Rejected':
            return 'REJECTED'
        elif stage.strage_from == 'Under Revisions' and stage.stage_to == 'Under Review':
            return 'MAJORREVISION'
        elif stage.stage_to == 'Under Revisions':  #TODO default assumption minor revision reasonable?
            return 'MINORREVISION'
        else:
            return ''


def create_pseudo_address(email, salt):
    """
    Create a pseudo email address.
    """
    combined = email + salt
    hash_obj = hashlib.sha1(combined.encode())
    hash_hex = hash_obj.hexdigest()
    pseudo_address = hash_hex + "@example.edu"
    return pseudo_address


def generate_random_salt(length=12):
    """
    Generate a random salt string of specified length.
    Uses a mix of lowercase letters, uppercase letters, and digits.
    TODO: generate a salt for every journal at install?
    """
    characters = string.ascii_letters + string.digits
    salt = ''.join(random.choice(characters) for _ in range(length))
    return salt





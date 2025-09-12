"""
© Julius Harms, Freie Universität Berlin 2025
"""

import json
import requests
from requests import RequestException

from utils.logger import get_logger
from utils.models import Version

from plugins.rqc_adapter.models import RQCCall
from plugins.rqc_adapter.utils import convert_date_to_rqc_format
from plugins.rqc_adapter.config import API_VERSION, API_BASE_URL, REQUEST_TIMEOUT
from plugins.rqc_adapter.config import VERSION

logger = get_logger(__name__)

def call_mhs_apikeycheck(journal_id: int, api_key: str) -> dict:
    """
    Verify API key with the RQC service.
    :param journal_id: str: The ID of the journal to check
    :param api_key: str: The API key to validate
    :return:int: dict: Response data if available and valid or raises RequestException: If the request fails
    """
    url = f'{API_BASE_URL}/mhs_apikeycheck/{journal_id}'
    return call_rqc_api(url, api_key)

def call_mhs_submission(journal_id: int, api_key: str, submission_id, post_data: str, article=None) -> dict:
    """
    TODO
    """
    url = f'{API_BASE_URL}/mhs_submission/{journal_id}/{submission_id}'
    return call_rqc_api(url , api_key, use_post=True, post_data=post_data, article=article)

def call_rqc_api(url: str, api_key: str, use_post=False, post_data=None, article=None) -> dict:
    result = {
        'success': False,
        'http_status_code': None,
        'message': None,
        'redirect_target': None,
    }
    try:
        #TODO database access somewhere else is better
        try:
            current_version = Version.objects.all().order_by('-number').first()
            if not current_version:
                raise ValueError('No version information available')
        except Exception as db_error:
            raise ValueError(f"Error retrieving version information: {db_error}")

        headers = {
            'X-Rqc-Api-Version': API_VERSION,
            'X-Rqc-Mhs-Version': f'Janeway {current_version.number}',
            'X-Rqc-Mhs-Adapter': f'RQC plugin {VERSION} https://github.com/JuliusHarms/janeway-rqcplugin',
            'X-Rqc-Time': convert_date_to_rqc_format(),
            'Authorization': f'Bearer {api_key}',
        }
        if use_post:
            #headers['Content-Type'] = 'application/json'
            # todo make redirects work?
            print(headers, post_data) #todo remove?
            response = requests.post(
                url,
                json = post_data,
                headers = headers,
                timeout = REQUEST_TIMEOUT,
                allow_redirects = False,
            )
        else:
            response = requests.get(
                url,
                headers = headers,
                timeout = REQUEST_TIMEOUT
            )
        result['http_status_code'] = response.status_code
        result['success'] = response.ok

        if response.ok:
            logger.info(f'Request to RQC succeeded with status code: {response.status_code}')
        else:
            logger.debug(f'Request to RQC failed with status code: {response.status_code}')

        if response.ok and use_post:
            RQCCall.objects.get_or_create(article=article, defaults = {'editor_assignments': post_data['edassgmnt_set']})

        if response.status_code == 200 and use_post:
            return result
        # Otherwise try to parse the body
        else:
            try:
                response_data = response.json()
                try:
                    if 'user_message' in response_data:
                        result['message'] = response_data['user_message']
                    elif "error" in response_data:
                        result['message'] = response_data['error']
                    # Return info if json exists but no message - is this needed?
                    elif not response.ok:
                        result['message'] = f'Request failed: {response.reason}'
                    if result['http_status_code'] == 303:
                        result['redirect_target'] = response_data.get('redirect_target')
                        result['success'] = True
                        # TODO additional excepts
                except ValueError:
                    result[
                        "message"] = f'Request failed and no error message was provided. Request status: {response.reason}'
            except json.decoder.JSONDecodeError:
                result["message"] = f'Request succeeded but response body was malformed. Request status: {response.reason}'
            return result
    #TODO look further at different types of request errors + appropriate response msg.
    except (requests.ConnectionError, requests.Timeout):
        result['message'] = 'Unable to connect to API service. Please try again later.'
    except RequestException as e:
        result['message'] = f'API service returned an invalid response: {str(e)}'
    return result
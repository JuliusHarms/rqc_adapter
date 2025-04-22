from datetime import datetime, timezone

import requests
from requests import RequestException

from plugins.rqc_adapter.config import API_VERSION, API_BASE_URL, REQUEST_TIMEOUT
from plugins.rqc_adapter.config import VERSION
from plugins.rqc_adapter.models import RQCReviewerOptingDecision
from plugins.rqc_adapter.plugin_settings import get_journal_api_key, get_journal_id, get_salt, set_journal_salt, \
    has_salt
from plugins.rqc_adapter.utils import convert_review_decision_to_rqc_format, get_editorial_decision, \
    create_pseudo_address
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
    return call_rqc_api(url , api_key, use_post=True, post_data=post_data)

def implicit_call_mhs_submission(**kwargs) -> dict:
    """
    TODO
    TODO unnecessary database calls... maybe put all the data collection in a separate function
    """
    article = kwargs['article']
    article_id = article.pk
    request = kwargs['request']
    return fetch_post_data(request=request, article=article, article_id = article_id, journal= request.journal)

def call_rqc_api(url: str, api_key: str, use_post=False, post_data=None) -> dict:
    result = {
        "success": False,
        "http_status_code": None,
        "message": None,
    }

    try:
        #database access somewhere else is better
        try:
            current_version = Version.objects.all().order_by('-number').first()
            if not current_version:
                raise ValueError("No version information available")
        except Exception as db_error:
            raise ValueError(f"Error retrieving version information: {db_error}")

        headers = {
            'X-Rqc-Api-Version': API_VERSION,
            'X-Rqc-Mhs-Version': f'Janeway {current_version.number}',
            'X-Rqc-Mhs-Adapter': f'RQC-Adapter {VERSION}',
            'X-Rqc-Time': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
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


def fetch_post_data(request, article, article_id, journal):
    submission_data = {}

    # interactive user get from request
    # how to check if there is a user
    if hasattr(request.user, 'id') and request.user.id is not None:
        submission_data['interactive_user'] = request.user.email
    else:
        submission_data['interactive_user'] = ""

    # submission page - redirect to the page from where the post request came from
    # if interactive user is empty this should be emtpy as well
    if submission_data.get('interactive_user') is not None:
        submission_data['mhs_submissionpage'] = request.META.get('HTTP_REFERER')  # open redirect vulnerabilities?
    else:
        submission_data['mhs_submissionpage'] = ""

    # title - length?
    submission_data['title'] = article.title

    # external uid
    submission_data['external_uid'] = str(article_id)
    # visible uid - remove characters that cant appear in url
    submission_data['visible_uid'] = str(article_id)

    # submission date check date time - utc
    submission_data['submitted'] = article.date_submitted.strftime('%Y-%m-%dT%H:%M:%SZ')

    # authorset -> for each ----> ONLY corresponding auth
    # author email
    # author firstname
    # author lastname
    # orcid
    # ordernumber
    author = article.correspondence_author
    author_order = article.articleauthororder_set.all()
    author_set = []
    author_info = {
        'email': author.email,
        'firstname': author.first_name if author.first_name else "",
        'lastname': author.last_name, #TODO what if this is empty? then a problem
        'orcid_id': author.orcid if author.orcid else "",
        'order_number': author_order.get(author=author).order  # TODO what if article,author is not unique
    }
    author_set.append(author_info)
    submission_data['author_set'] = author_set

    # editor_assignment set -> for each
    # editor assignments for each article
    # editor email
    # editor firstname
    # last name
    # ordcid
    # level
    submission_data['editor_set'] = []
    editor_assignments = article.editorassignment_set.all()
    for editor_assignment in editor_assignments:
        editor = editor_assignment.editor
        editor_data = {
            'email': editor.email,
            'firstname': editor.first_name if editor.first_name else "",
            'lastname': editor.last_name,
            'orcid_id': editor.orcid if editor.orcid else "",
            'level': 1  # TODO what about different levels
        }
        submission_data['editor_set'].append(editor_data)

    # reviewerset
    # TODO handle opted out reviewers
    submission_data['review_set'] = []
    review_assignments = article.reviewassignment_set.all()  # TODO what if there is not reviewassignment -> no call should be possible os that guarenteed?
    num_reviews = 0
    for review_assignment in review_assignments:
        reviewer = review_assignment.reviewer
        review_file = review_assignment.review_file
        review_text = ""
        for review_answer in review_assignment.review_form_answers():  # TODO whats going on with multiple answers
            if review_answer.answer is not None:
                review_text = review_text + review_answer.answer
        review_data = {
            'visible_id': str(num_reviews + 1),  # TODO is that ok?
            'invited': review_assignment.date_requested.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'agreed': review_assignment.date_accepted.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'expected': review_assignment.date_due.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'submitted': review_assignment.date_complete.strftime('%Y-%m-%dT%H:%M:%SZ'),  # TODO correct timing utc?
            'text': review_text,
            'suggested_decision': convert_review_decision_to_rqc_format(review_assignment.decision),
            'is_html': 'true',  # review_file.mime_type in ["text/html"]  # TODO is the mime type correct?
        }
        try:
            opting_status = review_assignment.reviewer.rqcrevieweroptingdecision.opting_status
        except (AttributeError, RQCReviewerOptingDecision.DoesNotExist):
            opting_status = None
        if opting_status == RQCReviewerOptingDecision.OptingChoices.OPT_IN:  # TODO treat no opting decision as opt out
            reviewer = {
                'email': reviewer.email,
                'firstname': reviewer.first_name if reviewer.first_name else "",
                'lastname': reviewer.last_name,
                'orcid_id': reviewer.orcid if reviewer.orcid else "",
            }
        else:
            if not has_salt(journal):
                salt = set_journal_salt(journal)
            else:
                salt = get_salt(journal)
            reviewer = {
                'email': create_pseudo_address(reviewer.email, salt),
                'firstname': '',
                'lastname': '',
                'orcid_id': ''
            }
        review_data['reviewer'] = reviewer
        # handle attachments - there can only be one review file
        # need to be handled in their own function i think..
        # check for file being remote
        attachment_set = []
        # TODO attachments do not work yet on the side of RQC
        """
        if review_file is not None and not review_file.is_remote: #TODO handle remote files
            attachment_set.append({
                'filename': review_file.original_filename,
                'data': encode_file_as_b64(review_file.uuid_filename,article_id),
            })
        """
        review_data['attachment_set'] = attachment_set
        submission_data['review_set'].append(review_data)

    # decision
    submission_data['decision'] = get_editorial_decision(
        article)  # TODO redo revision request by querying for revisionrequest objects
    print(submission_data)  # TODO remove
    return submission_data
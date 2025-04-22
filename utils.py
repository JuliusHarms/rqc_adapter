import base64
import hashlib
import os
import secrets
import string

from django.conf import settings

from core.models import SettingValue
from review.models import RevisionRequest


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
    if article.is_accepted:
        return 'ACCEPTED'
    elif article.date_declined is not None: #TODO correct?
        return 'REJECTED'
    else:
        try:
            revision_request = RevisionRequest.objects.filter(article=article).order_by('-date_requested').first() #TODO get the most recent one?
            if revision_request.type == 'minor_revisions':
                return 'MINORREVISION'
            else:
                return 'MAJORREVISION'
        except RevisionRequest.DoesNotExist:
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
    salt = ''.join(secrets.choice(characters) for _ in range(length))
    while SettingValue.objects.filter(value=salt).exists():
        salt = ''.join(secrets.choice(characters) for _ in range(length))
    return salt




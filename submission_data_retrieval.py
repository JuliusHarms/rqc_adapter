"""
© Julius Harms, Freie Universität Berlin 2025
"""

from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCReviewerOptingDecisionForReviewAssignment
from plugins.rqc_adapter.plugin_settings import has_salt, set_journal_salt, get_salt
from plugins.rqc_adapter.utils import convert_review_decision_to_rqc_format, create_pseudo_address, encode_file_as_b64, \
    get_editorial_decision

MAX_SINGLE_LINE_STRING_LENGTH = 2000
MAX_MULTI_LINE_STRING_LENGTH = 200000
MAX_LIST_LENGTH = 20

# TODO just article ? article already has id and journal...
def fetch_post_data(article, journal, mhs_submissionpage = '', is_interactive = False, user = None ) :
    """ Generates and collects all information for a RQC submission
    :param user: User object
    :param article: Article object
    :param journal: Journal object
    :param mhs_submissionpage: str Redirect URL from RQC back to Janeway
    :param is_interactive: Boolean flag to enable interactive call mode which redirects to RQC
    :return: Dictionary of submission data
    """
    submission_data = {}

    # If the interactive flag is set user information is transmitted to RQC.
    interactive_user_email = ''
    if is_interactive and user and hasattr(user, 'email') and user.email:
        interactive_user_email = user.email

    submission_data['interactive_user'] = interactive_user_email

    # If interactive user is set the call will open RQC to grade the submission.
    # mhs_submissionpage is used by RQC to redirect the user to Janeway after grading.
    # So if interactive user is empty this should be empty as well.
    if submission_data['interactive_user']:
        submission_data['mhs_submissionpage'] = mhs_submissionpage #TODO redirect vulnerabilities?
    else:
        submission_data['mhs_submissionpage'] = ''

    # RQC requires that single line strings don't exceed 2000 characters
    # and that multi lines string don't exceed 200 000 characters.
    # Field constraints in the models already enforce this, but we double-check for safety.
    submission_data['title'] = article.title[:MAX_SINGLE_LINE_STRING_LENGTH]

    submission_data['external_uid'] = str(article.pk)
    # The primary key is just a number because Django's auto-increment pk is used
    submission_data['visible_uid'] = str(article.pk)

    # RQC requires all datetime values to be in UTC
    # Janeway uses aware timezones and the default timezone is UTC per the general settings
    submission_data['submitted'] = article.date_submitted.strftime('%Y-%m-%dT%H:%M:%SZ')

    submission_data['author_set'] = get_authors_info(article)

    submission_data['edassgmt_set'] = get_editors_info(article)

    submission_data['review_set'] = get_reviews_info(article, journal)

    submission_data['decision'] = get_editorial_decision(article)  # TODO redo revision request by querying for revisionrequest objects -> prob fine but add test for it
    return submission_data


def get_authors_info(article):
    """ Returns the authors info for an article
    :param article: Article object
    :return: List of author information
    """
    # The RQC API specifies that only information from correspondence authors
    # should be transmitted. In janeway there can only be one correspondence author
    # so the author_set will only contain one member.
    author = article.correspondence_author
    author_order = article.articleauthororder_set.filter(author=author).first()
    author_set = []
    author_info = {
        'email': author.email[:MAX_SINGLE_LINE_STRING_LENGTH],
        'firstname': author.first_name[:MAX_SINGLE_LINE_STRING_LENGTH] if author.first_name else '',
        'lastname': author.last_name[:MAX_SINGLE_LINE_STRING_LENGTH] if author.last_name else '',
        'orcid_id': author.orcid[:MAX_SINGLE_LINE_STRING_LENGTH] if author.orcid else '',
        'order_number': author_order.order+1 # Add 1 because RQC author numbering starts at 1 while in Janeway counting starts at  0
    }
    author_set.append(author_info)
    return author_set

def get_editors_info(article):
    """ Returns the information about the editors of the article
    :param article: Article Object
    :return: List of editor info
    """
    edassgmt_set = []

    # RQC requires that the list of editor assignments is no longer than 20 entries.
    # RQC distinguishes between three levels of editors.
    # 1 - handling editor, 2 - section editor, 3 - chief editor
    # One editor may appear multiple times in each role.
    editor_assignments = article.editorassignment_set.order_by('-assigned')

    # Editors assigned to the article will be treated as handling editors by RQC.
    # Editors that aren't assigned to the article but to the section of the article
    # will be added to the assignment set so that they can grade the article reviews as well.
    for editor_assignment in editor_assignments:
        edassgmt_set.append(get_editor_info(editor_assignment.editor, 1))

    section = article.section
    if section is not None:
        for section_editor in section.section_editors.all():
            edassgmt_set.append(get_editor_info(section_editor, 2))

        for editor in section.editors.all():
            edassgmt_set.append(get_editor_info(editor, 3))

    return edassgmt_set[:MAX_LIST_LENGTH]

def get_editor_info(editor, level):
    """
    :param editor: Editor Object
    :param level: Level of editor
    :return: Dictionary of editor data
    """
    editor_data = {
            'email': editor.email[:MAX_SINGLE_LINE_STRING_LENGTH],
            'firstname': editor.first_name[:MAX_SINGLE_LINE_STRING_LENGTH] if editor.first_name else '',
            'lastname': editor.last_name[:MAX_SINGLE_LINE_STRING_LENGTH] if editor.last_name else '',
            'orcid_id': editor.orcid[:MAX_SINGLE_LINE_STRING_LENGTH] if editor.orcid else '',
            'level': level
        }
    return editor_data

def get_reviews_info(article, journal):
    """ Returns the info for all reviews for the given article in a list
    :param article: Article object
    :param journal: Journal object
    :return: List of review info
    """
    review_set = []
    # If a review assignment was not accepted this date field will be null.
    # Reviewers that have not accepted a review assignment are not considered for grading by RQC
    # TODO what if the review was unaccepted!!!?
    review_assignments = article.reviewassignment_set.filter(date_accepted__isnull = False).order_by('date_accepted') # TODO what if there is not review assignment -> no call should be possible os that guarenteed?
    review_num = 1
    for review_assignment in review_assignments:
        reviewer = review_assignment.reviewer
        # TODO what if reviews are not yet completed?
        # TODO are review assignment created if reviewers haven't accepted yet? -> then a review assignment is made anyway...
        review_assignment_answers = [ra.answer for ra in review_assignment.review_form_answers()]
        review_text = " ".join(review_assignment_answers)
        reviewer_has_opted_in = has_opted_in(reviewer, review_assignment)

        review_data = {
            # Visible id is just supposed to identify the review as a sort of name.
            # An integer ordering by the acceptance date is used starting at 1 for the oldest review assignment.
            'visible_id': str(review_num), #TODO what if the review isn't published yet??ß
            'invited': review_assignment.date_requested.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'agreed': review_assignment.date_accepted.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'expected': review_assignment.date_due.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'submitted': review_assignment.date_complete.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'text': review_text[:MAX_SINGLE_LINE_STRING_LENGTH] if reviewer_has_opted_in else '',
            # Review text is always HTML.
            # This is due to the text input being collected in the TinyMCE widget.
            'is_html': True,
            'suggested_decision': convert_review_decision_to_rqc_format(review_assignment.decision),
            'reviewer': get_reviewer_info(reviewer, reviewer_has_opted_in, journal),
            # Because RQC does not yet support attachments the attachment set is left empty.
            # review_data['attachment_set'] = get_attachment(article, review_file=article.review_file)
            'attachment_set': []
        }

        review_set.append(review_data)
        review_num = review_num + 1
    # TODO does this go against the reviews are holy principle?
    return review_set[:MAX_LIST_LENGTH]

#TODO does this work?
def has_opted_in(reviewer, review_assignment):
    """ Determines if reviewer has opted into RQC
    :param reviewer: Reviewer object
    :param review_assignment: Review Assignment object
    :return: True if reviewer has opted in and False otherwise
    """
    try:
        opting_status = reviewer.rqcrevieweroptingdecisionforreviewassignment_set.filter(review_assignment = review_assignment).first().opting_status
    except (AttributeError, RQCReviewerOptingDecisionForReviewAssignment.DoesNotExist):
        opting_status = None
    if opting_status == RQCReviewerOptingDecision.OptingChoices.OPT_IN:
        return True
    else:
        return False

def get_reviewer_info(reviewer, reviewer_has_opted_in, journal):
    """ Gets the reviewer's information. If the reviewer has not opted in return pseudo address and empty values instead
    :param reviewer: Reviewer object
    :param reviewer_has_opted_in: True if reviewer has opted in
    :param journal: Journal object
    :return reviewer_info: dictionary {'email': str, 'firstname': str, 'lastname': str, 'orcid_id': str}
    """
    if reviewer_has_opted_in:
        reviewer_data = {
            'email': reviewer.email[:MAX_SINGLE_LINE_STRING_LENGTH],
            'firstname': reviewer.first_name[:MAX_SINGLE_LINE_STRING_LENGTH] if reviewer.first_name else '',
            'lastname': reviewer.last_name[:MAX_SINGLE_LINE_STRING_LENGTH] if reviewer.last_name else '',
            'orcid_id': reviewer.orcid[:MAX_SINGLE_LINE_STRING_LENGTH] if reviewer.orcid else '',
        }
    # If a reviewer has opted out RQC requires that the email address is anonymised and no additional data is transmitted
    else:
        if not has_salt(journal):
            salt = set_journal_salt(journal)
        else:
            salt = get_salt(journal)
        reviewer_data = {
            'email': create_pseudo_address(reviewer.email, salt),
            'firstname': '',
            'lastname': '',
            'orcid_id': ''
        }
    return reviewer_data

# As of API version 2023-09-06, RQC does not support file attachments
# TODO: Remote files might not work with this code
def get_attachment(article, review_file):
    """ Gets the filename of the attachment and encodes its data. Attachments don't work yet on the side of RQC so in practice this should only be called with review_file=None
    :param review_file: File object
    :param article: Article object
    :return: list of dicts {filename: str, data: str}
    """
    attachment_set = []
    # File size should me no larger than 64mb
    if review_file is not None and not review_file.is_remote and review_file.get_file_size(article) <= 67108864:
        attachment_set.append({
            'filename': review_file.original_filename,
            'data': encode_file_as_b64(review_file.uuid_filename,article),
        })
    return attachment_set



from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCReviewerOptingDecisionForReviewAssignment
from plugins.rqc_adapter.plugin_settings import has_salt, set_journal_salt, get_salt
from plugins.rqc_adapter.utils import convert_review_decision_to_rqc_format, create_pseudo_address, encode_file_as_b64, \
    get_editorial_decision


# TODO just article ? article already has id and journal...
def fetch_post_data(article, article_id, journal, mhs_submissionpage = '', interactive = False, user=None ) :
    """ Generates and collects all information for a RQC submission
    :param user: User object
    :param article: Article object
    :param article_id: Article ID
    :param journal: Journal object
    :param mhs_submissionpage: str Redirect URL from RQC back to Janeway
    :param interactive: Boolean flag to enable interactive call mode which redirects to RQC
    :return: Dictionary of submission data
    """
    submission_data = {}

    # If the interactive flag is set user information is transmitted to RQC.
    if interactive and hasattr(user, 'id') and user.id is not None:
        submission_data['interactive_user'] = user.email
    else:
        submission_data['interactive_user'] = ''

    # If interactive user is set the call will open RQC to grade the submission.
    # mhs_submissionpage is used by RQC to redirect the user to Janeway after grading.
    # So if interactive user is empty this should be empty as well.
    if submission_data.get('interactive_user') != '':
        submission_data['mhs_submissionpage'] = mhs_submissionpage  #todo open redirect vulnerabilities?
    else:
        submission_data['mhs_submissionpage'] = ''

    # RQC requires that single line strings don't exceed 2000 characters
    # and that multi lines string don't exceed 200 000 characters.
    # Field constraints in the models already enforce this, but we double-check for safety.
    submission_data['title'] = article.title[:2000]

    submission_data['external_uid'] = str(article_id)
    # visible uid - remove characters that cant appear in url
    submission_data['visible_uid'] = str(article_id) #TODO only printable characters - no blanks?

    # RQC requires all datetime values to be in UTC
    # Janeway uses aware timezones and the default timezone is UTC per the general settings
    submission_data['submitted'] = article.date_submitted.strftime('%Y-%m-%dT%H:%M:%SZ')

    submission_data['author_set'] = get_authors_info(article)

    submission_data['edassgmt_set'] = get_editors_info(article)

    # TODO handle opted out reviewers
    #TODO change order
    submission_data['review_set'] = get_reviews_info(article, article_id, journal)

    submission_data['decision'] = get_editorial_decision(
        article)  # TODO redo revision request by querying for revisionrequest objects
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
        'email': author.email[:2000],
        'firstname': author.first_name[:2000] if author.first_name else '',
        'lastname': author.last_name[:2000] if author.last_name else '',
        'orcid_id': author.orcid[:2000] if author.orcid else '',
        'order_number': author_order.order+1 # We add 1 because RQC author numbering starts at 1 while in Janeway counting starts at  0
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

    editor_assignments = article.editorassignment_set.order_by('-assigned')[:20]

    # Editors assigned to the article will be treated as handling editors by RQC.
    # Editors that aren't assigned to the article but to the section of the article
    # will be added to the assignment set so that they can grade the article reviews as well.

    for editor_assignment in editor_assignments:
        editor = editor_assignment.editor
        editor_data = get_editor_data(editor, 1)
        edassgmt_set.append(editor_data)

    section = article.section
    if section is not None:
        for section_editor in section.section_editors.all():
            editor_data = get_editor_data(section_editor, 2)
            edassgmt_set.append(editor_data)

        for editor in section.editors.all():
            editor_data = get_editor_data(editor, 3)
            edassgmt_set.append(editor_data)

    return edassgmt_set[:20]

def get_editor_data(editor, level):
    """
    :param editor: Editor Object
    :param level: Level of editor
    :return: Dictionary of editor data
    """
    editor_data = {
            'email': editor.email[:2000],
            'firstname': editor.first_name[:2000] if editor.first_name else '',
            'lastname': editor.last_name[:2000] if editor.last_name else '',
            'orcid_id': editor.orcid[:2000] if editor.orcid else '',
            'level': level
        }
    return editor_data

def get_reviews_info(article, article_id, journal):
    """ Returns the info for all reviews for the given article in a list
    :param article: Article object
    :param article_id: Article id
    :param journal: Journal object
    :return: List of review info
    """
    review_set = []
    # If a review assignment was not accepted this date field will be null.
    # Reviewers that have not accepted a review assignment are not considered for grading by RQC
    review_assignments = article.reviewassignment_set.filter(date_accepted__isnull = False) # TODO what if there is not reviewassignment -> no call should be possible os that guarenteed?
    num_reviews = 0
    for review_assignment in review_assignments:
        reviewer = review_assignment.reviewer
        # The review file is needed to transmit attachments but attachments are not yet supported by RQC
        # TODO what if reviews are not yet completed?
        # TODO are reviewassignment created if reviewers havent accepted yet? -> then a reviewassignment is made anyway...
        review_text = ''
        for review_answer in review_assignment.review_form_answers():  # TODO whats going on with multiple answers
            if review_answer.answer is not None:
                review_text = review_text + review_answer.answer

        review_data = {
            'visible_id': str(num_reviews + 1),  # TODO is that ok?
            'invited': review_assignment.date_requested.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'agreed': review_assignment.date_accepted.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'expected': review_assignment.date_due.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'submitted': review_assignment.date_complete.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'is_html': True,  # review_file.mime_type in ["text/html"]  #TODO check can a review not be html
            'suggested_decision': convert_review_decision_to_rqc_format(review_assignment.decision),
        }

        reviewer_has_opted_in = has_opted_in(reviewer, review_assignment)

        # Review text should not exceed 200000 characters
        if reviewer_has_opted_in:
            review_data['text'] = review_text[:200000]
        else:
            review_data['text'] = ''

        review_data['reviewer'] = get_reviewer_info(reviewer, reviewer_has_opted_in, journal)

        # Because RQC does not yet support attachments the attachment set is left empty
        # review_data['attachment_set'] = get_attachment(article, review_file=article.review_file)
        review_data['attachment_set'] = []

        review_set.append(review_data)
        # TODO does this go against the reviews are holy principle?
    return review_set[:20]

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
            'email': reviewer.email[:2000],
            'firstname': reviewer.first_name[:2000] if reviewer.first_name else '',
            'lastname': reviewer.last_name[:2000] if reviewer.last_name else '',
            'orcid_id': reviewer.orcid[:2000] if reviewer.orcid else '',
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



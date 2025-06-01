from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCReviewerOptingDecisionForReviewAssignment
from plugins.rqc_adapter.plugin_settings import has_salt, set_journal_salt, get_salt
from plugins.rqc_adapter.utils import convert_review_decision_to_rqc_format, create_pseudo_address, encode_file_as_b64, \
    get_editorial_decision


# TODO just article ? article already has id and journal...
def fetch_post_data(user, article, article_id, journal, mhs_submissionpage = '', interactive = False):
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

    # If interactive flag is set user information is transmitted to RQC

    if interactive and hasattr(user, 'id') and user.id is not None:
        submission_data['interactive_user'] = user.email
    else:
        submission_data['interactive_user'] = ''

    # If interactive user is set the call will open RQC to grade the submission
    # mhs_submissionpage is used by RQC to redirect the user to Janeway afterwards
    # So if interactive user is empty this should be empty as well

    if submission_data.get('interactive_user') != '':
        submission_data['mhs_submissionpage'] = mhs_submissionpage  #todo open redirect vulnerabilities?
    else:
        submission_data['mhs_submissionpage'] = ''

    # title - length?
    submission_data['title'] = article.title

    # external uid
    submission_data['external_uid'] = str(article_id)
    # visible uid - remove characters that cant appear in url
    submission_data['visible_uid'] = str(article_id) #TODO only printable characters - no blanks?

    # submission date check date time - utc
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
    :return: Dictionary of author information
    """
    author = article.correspondence_author
    author_order = article.articleauthororder_set.all()
    author_set = []
    author_info = {
        'email': author.email,
        'firstname': author.first_name if author.first_name else "",
        'lastname': author.last_name, #TODO what if this is empty? then a problem
        'orcid_id': author.orcid if author.orcid else "",
        'order_number': author_order.get(author=author).order+1  # TODO what if article,author is not unique
    }
    author_set.append(author_info)
    return author_set

def get_editors_info(article):
    """ Returns the information about the editors of the article
    :param article: Article Object
    :return: Dictionary of editor info
    """
    edassgmt_set = [] #TODO editor_set? editorassignment_set? edassgmt_set?
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
        edassgmt_set.append(editor_data)
    return edassgmt_set

def get_reviews_info(article, article_id, journal):
    """ Returns the info for all reviews for the given article in a list
    :param article: Article object
    :param article_id: article id
    :param journal: Journal object
    :return: list of review info
    """
    review_set = []
    # If a review assignment was not accepted this date field will be null.
    # Reviewer that have not accepted a review assignment are not considered for grading by RQC
    review_assignments = article.reviewassignment_set.filter(date_accepted__isnull = False) # TODO what if there is not reviewassignment -> no call should be possible os that guarenteed?
    num_reviews = 0
    for review_assignment in review_assignments:
        reviewer = review_assignment.reviewer
        # The review file is needed to transmit attachments but attachments are not yet supported by RQC
        #review_file = review_assignment.review_file
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
            'submitted': review_assignment.date_complete.strftime('%Y-%m-%dT%H:%M:%SZ'),  # TODO correct timing utc?
            'is_html': True,  # review_file.mime_type in ["text/html"]  #TODO check can a review not be html
            'suggested_decision': convert_review_decision_to_rqc_format(review_assignment.decision),
        }

        reviewer_has_opted_in = has_opted_in(reviewer, review_assignment)

        if reviewer_has_opted_in:
            review_data['text'] = review_text
        else:
            review_data['text'] = ''

        review_data['reviewer'] = get_reviewer_info(reviewer, reviewer_has_opted_in, journal)

        review_data['attachment_set'] = get_attachments_info(article_id, review_file=None)
        review_set.append(review_data)
    return review_set

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
            'email': reviewer.email,
            'firstname': reviewer.first_name if reviewer.first_name else '',
            'lastname': reviewer.last_name,
            'orcid_id': reviewer.orcid if reviewer.orcid else '',
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

def get_attachments_info(article_id, review_file):
    """ Gets the filename of the attachment and encodes its data. Attachments don't work yet on the side of RQC so in practice this should only be called with review_file=None
    :param review_file
    :param article_id
    :return: list of dicts {filename: str, data: str}
    """
    attachment_set = []
    # TODO attachments do not work yet on the side of RQC
    if review_file is not None and not review_file.is_remote: #TODO handle remote files
        attachment_set.append({
            'filename': review_file.original_filename,
            'data': encode_file_as_b64(review_file.uuid_filename,article_id),
        })
    return attachment_set



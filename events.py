"""
© Julius Harms, Freie Universität Berlin 2025

This file contains the functions that are registered for events in plugin_settings.
"""
from utils.logger import get_logger

from plugins.rqc_adapter.utils import utc_now
from plugins.rqc_adapter.models import RQCJournalAPICredentials, RQCReviewerOptingDecision
from plugins.rqc_adapter.rqc_calls import call_mhs_submission
from plugins.rqc_adapter.submission_data_retrieval import fetch_post_data

logger = get_logger(__name__)

# Called when an article editorial decision changes
def implicit_call_mhs_submission(**kwargs) -> dict | None:
    """
    TODO what if values don't exist yet....
    TODO unnecessary database calls... maybe put all the data collection in a separate function
    """
    article = kwargs['article']
    request = kwargs['request']

    if article is None:
        logger.warning("No article provided. Could not make implicit call to the RQC API.")
        return None

    journal = article.journal

    # If there are no RQC credentials no calls should be made.
    try:
        credentials = RQCJournalAPICredentials.objects.get(journal=journal)
    except RQCJournalAPICredentials.DoesNotExist:
        return None

    # If there are no reviews for an article, for instance if an article is declined
    # without going into the 'Review' stage, no call is made.
    if not article.reviewassignment_set.exists():
        return None

    journal_id = credentials.journal_id
    api_key = credentials.api_key
    submission_id = article.pk #TODO change sub id to something else?
    post_data = fetch_post_data(user=request.user, article=article, journal= request.journal)
    return call_mhs_submission(journal_id=journal_id,
                               api_key=api_key,
                               submission_id=submission_id,
                               post_data=post_data,
                               article=article)

# Executed when ON_REVIEWER_ACCEPTED event happens (when a reviewer accepts a review assignment).
def create_review_assignment_opting_decision(**kwargs):
    """
    Creates review_assignment_opting_decision.
    :param kwargs: Contains ReviewAssignment object
    """
    review_assignment = kwargs.get("review_assignment")
    journal = review_assignment.journal
    # Don't create Review Assignment Opting Decisions if no API credentials are present
    try:
        RQCJournalAPICredentials.objects.get(journal=journal)
    except RQCJournalAPICredentials.DoesNotExist:
        return None

    if not review_assignment:
        logger.error('Could not create RQC opting decision: review_assignment is required')
        return None
    try:
        decision = RQCReviewerOptingDecision.objects.filter(reviewer=review_assignment.reviewer,
                                                             journal=journal,
                                                             opting_date__year=utc_now().year).first()
        if decision is not None:
            opting_status = decision.opting_status
            RQCReviewerOptingDecision.objects.get_or_create(review_assignment=review_assignment,
                                                            opting_status=opting_status)
        else:
            # Create with default status of undefined
            RQCReviewerOptingDecision.objects.get_or_create(review_assignment=review_assignment)
    except Exception as e:
        logger.error(f'Could not create RQC opting decision for review assignment: {e}')
        return None
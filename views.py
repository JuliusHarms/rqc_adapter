"""
© Julius Harms, Freie Universität Berlin 2025
"""
from datetime import datetime, timezone

from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from plugins.rqc_adapter.utils import utc_now
from review import logic
from review.models import ReviewAssignment
from utils.logger import get_logger
from security import decorators
from security.decorators import production_manager_roles
from submission import models as submission_models

from plugins.rqc_adapter import forms
from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCDelayedCall, RQCJournalAPICredentials, \
    RQCReviewerOptingDecisionForReviewAssignment, RQCCall
from plugins.rqc_adapter.rqc_calls import call_mhs_submission
from plugins.rqc_adapter.submission_data_retrieval import fetch_post_data

logger = get_logger(__name__)

@decorators.has_journal
@production_manager_roles
def manager(request):
    template = 'rqc_adapter/manager.html'
    journal = request.journal
    api_key_set = False
    try:
        credentials = RQCJournalAPICredentials.objects.get(journal=journal)
        if credentials.rqc_journal_id is not None:
            journal_id = credentials.rqc_journal_id
            form = forms.RqcSettingsForm(initial={'journal_id_field': journal_id})
        else:
            form = forms.RqcSettingsForm()

        if credentials.api_key is not None and credentials.api_key != "":
            api_key_set = True
    except RQCJournalAPICredentials.DoesNotExist:
        form = forms.RqcSettingsForm()
    return render(request, template, {'form': form, 'api_key_set': api_key_set})

def handle_journal_settings_update(request):
    if request.method == 'POST':
        template = 'rqc_adapter/manager.html'
        journal = request.journal
        form = forms.RqcSettingsForm(request.POST)
        user_id = request.user.id if hasattr(request, 'user') else None
        if form.is_valid():
            try:
                journal_id = form.cleaned_data['journal_id_field']
                journal_api_key = form.cleaned_data['journal_api_key_field']
                # journal_id and api_key are saved together as a pair.
                # Because journal_id and api_key only serve as valid credentials as a pair and API calls with false credentials should be avoided
                with transaction.atomic():
                    RQCJournalAPICredentials.objects.update_or_create(journal = journal, defaults={'rqc_journal_id': journal_id, 'api_key': journal_api_key})
                messages.success(request, 'RQC settings updated successfully.')
                logger.info(f'RQC settings updated successfully for journal: {journal.name} by user: {user_id}.')
            except Exception as e:
                messages.error(request, 'Settings update failed due to a system error.')
                log_settings_error(journal.name, user_id, e)
        else:
            non_field_errors = form.non_field_errors()
            for non_field_error in non_field_errors:
                messages.error(request, 'Settings update failed. ' + non_field_error)
                log_settings_error(journal.name, user_id, non_field_error)
            for field_name, field_errors in form.errors.items():
                if field_name != '__all__':
                    field_label = form.fields[field_name].label
                    for error in field_errors:
                        messages.error(request, f'{field_label}: {error}')
                        log_settings_error(journal.name, user_id, error)
            # In the case of validation errors users aren't redirect to preserve and display field and non-field errors
            return render(request, template, {'form': form})
        # Users are redirected after post to prevent double submits
        return redirect('rqc_adapter_manager')
    # Ignore non-post requests
    else:
        return redirect('rqc_adapter_manager')

def log_settings_error(journal_name, user_id, error_msg):
    logger.error(f'Failed to save RQC settings for journal {journal_name} by user: {user_id}. Details: {error_msg}')


#All one-line strings must be no longer than 2000 characters.
#All multi-line strings (the review texts) must be no longer than 200000 characters.
#Author lists must be no longer than 200 entries.
#Other lists (reviews, editor assignments) must be no longer than 20 entries.
#Attachments cannot be larger than 64 MB each.
@decorators.has_journal
@decorators.editor_user_required_and_can_see_pii
def submit_article_for_grading(request, article_id):
    referer = request.META.get('HTTP_REFERER')
    article = get_object_or_404(
        submission_models.Article,
        pk=article_id,
        journal=request.journal,
    )
    journal = article.journal
    try:
        api_credentials = RQCJournalAPICredentials.objects.get(journal=journal)
    except RQCJournalAPICredentials.DoesNotExist:
        messages.error(request, 'Review Quality Collector API credentials not found.')
        return redirect(referer)
    user = request.user
    mhs_submissionpage = request.META.get('HTTP_REFERER')
    is_interactive = True
    post_data = fetch_post_data(article, journal, mhs_submissionpage, is_interactive, user)
    response = call_mhs_submission(journal_id = api_credentials.rqc_journal_id,
                                   api_key = api_credentials.api_key,
                                   submission_id=article_id, post_data=post_data, article=article)
    print(response) #TODO remove
    # TODO handle errors and status response:
    #TODO add messages in templates
    # TODO what if no message?
    if not response['success']:
        match response['http_status_code']:
            case 400:
                messages.error(request, f'Sending the data to RQC failed. The message sent to RQC was malformed. Details: {response["message"]}')
            case 403:
                messages.error(request, f'Sending the data to RQC failed. The API key was wrong. Details: {response["message"]}' ) #TODO alert editors? see api description
            case 404:
                messages.error(request, f'Sending the data to RQC failed. The whole URL was malformed or no journal with the given journal id exists at RQC. Details: {response["message"]}')
            case  _: #TODO what other cases can occur? - change message based on response code
                messages.error(request, f'Sending the data to RQC failed. There might be a server error on the side of RQC the data will be automatically resent shortly. Details: {response["message"]}')
                RQCDelayedCall.objects.create(remaining_tries= 10,
                                                article = article,
                                                article_id = article.pk,
                                                journal = journal,
                                                failure_reason = response['http_status_code'],
                                                last_attempt_at = now())
        return redirect(referer)
    else:
        if response['http_status_code'] == 303:
            return redirect(response['redirect_target']) #TODO correct format?
        else:
            return redirect(referer)

# TODO should a user be able to manually enter the url and change opting status?
# TODO check user login?
# TODO user should be able to get here manually
# The request must provide a journal object because the opting decision in specific to the journal
# The user must be a reviewer since only reviewers should be able to opt in or out
@decorators.has_journal
@decorators.reviewer_user_required
def set_reviewer_opting_status(request):
    if request.method == 'POST':
        form = forms.ReviewerOptingForm(request.POST)
        if form.is_valid():
            opting_status = form.cleaned_data['status_selection_field']
            user = request.user
            RQCReviewerOptingDecision.objects.update_or_create(reviewer = user, journal= request.journal, defaults={'opting_status': opting_status, 'opting_date': utc_now()})
            if opting_status == RQCReviewerOptingDecision.OptingChoices.OPT_IN:
                messages.info(request, 'Thank you for choosing to participate in RQC!')
            else:
                messages.info(request, 'Thank you for your response. Your preference has been recorded.')

            # Check if the Review Assignment is frozen (see also the is_frozen property
            # of RQCReviewerOptingDecisionForReviewAssignment)
            # Not Frozen means data was not yet received by RQC
            # and the assignment is ongoing meaning accepted but not complete and not declined.
            # If the Review Assignment is not frozen we update the opting status to reflect
            # the selected value.
            RQCReviewerOptingDecisionForReviewAssignment.objects.exclude(
                Q(review_assignment__article__in = RQCCall.objects.values_list('article', flat=True))
                | Q(review_assignment__is_complete = True)
                | Q(review_assignment__date_declined__isnull = False)
                | Q(review_assignment__date_accepted__isnull = False)
            ).update(opting_status=opting_status)

            assignment_id = request.POST.get('assignment_id')

            # Logic checks request.GET for the access code.
            # If the access code is not available that way we can access the code
            # via a hidden input field in the form.
            access_code = logic.get_access_code(request)
            if access_code is None:
                access_code = request.POST.get('access_code')

            try:
                if access_code:
                    assignment = ReviewAssignment.objects.get(
                        Q(pk=assignment_id)
                        & Q(is_complete=False)
                        & Q(access_code=access_code)
                        & Q(article__stage=submission_models.STAGE_UNDER_REVIEW)
                    )
                else:
                    assignment = ReviewAssignment.objects.get(
                        Q(pk=assignment_id)
                        & Q(is_complete=False)
                        & Q(reviewer=request.user)
                        & Q(article__stage=submission_models.STAGE_UNDER_REVIEW)
                        )

                return redirect(
                    logic.generate_access_code_url("do_review", assignment, access_code)
                )
            except ReviewAssignment.DoesNotExist:
                    return redirect('core_dashboard')
    else:
        return redirect('core_dashboard')
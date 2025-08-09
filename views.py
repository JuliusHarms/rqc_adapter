"""
© Julius Harms, Freie Universität Berlin 2025
"""

from django.utils.timezone import now

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from utils.logger import get_logger

from plugins.rqc_adapter.rqc_calls import call_mhs_submission, fetch_post_data
from security import decorators
from security.decorators import production_manager_roles
from submission import models as submission_models

from plugins.rqc_adapter import forms, plugin_settings
from plugins.rqc_adapter.plugin_settings import set_journal_id, set_journal_api_key, has_salt, set_journal_salt, \
    get_journal_id, get_journal_api_key, has_journal_id, has_journal_api_key, get_salt
from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCDelayedCall

logger = get_logger(__name__)

@decorators.has_journal
@production_manager_roles
def manager(request):
    template = 'rqc_adapter/manager.html'
    journal = request.journal
    api_key_set = False

    if has_journal_id(journal) :
        journal_id = get_journal_id(journal)
        form = forms.RqcSettingsForm(initial={'journal_id_field': journal_id})
    else:
        form = forms.RqcSettingsForm()

    if has_journal_api_key(journal):
        api_key_set = True

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
                set_journal_id(journal_id, journal)
                journal_api_key = form.cleaned_data['journal_api_key_field']
                set_journal_api_key(journal_api_key, journal)

                messages.success(request, 'RQC settings updated successfully.')
                logger.info(f'RQC settings updated successfully for journal: {journal.name} by user: {user_id}.')
                return redirect('rqc_adapter_manager')
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
            # In the case of validation errors users aren't redirect to preserve and display
            # field and non-field errors
            return render(request, template, {'form': form})
        # Users are redirected after post to prevent double submits
        return redirect('rqc_adapter_manager')
    # Ignore non-post requests
    else:
        return redirect('rqc_adapter_manager')

def log_settings_error(journal_name, user_id, error_msg):
    logger.error(f'Failed to save RQC settings for journal {journal_name} by user: {user_id}. Details: {error_msg}')


#TODO maybe save the data so for implicit calls it is not regenerated (except decision + additonal reviews)
#TODO check if RQC size limits are respected
#All one-line strings must be no longer than 2000 characters.
#All multi-line strings (the review texts) must be no longer than 200000 characters.
#Author lists must be no longer than 200 entries.
#Other lists (reviews, editor assignments) must be no longer than 20 entries.
#Attachments cannot be larger than 64 MB each.
# TODO what is a production user + add decorators to the other functions if needed
# TODO remove request as an argument
# TODO logic to move the article to the next stage?
# TODO check if user is editor or section editor
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
    user = request.user
    mhs_submissionpage = request.META.get('HTTP_REFERER')
    is_interactive = True
    post_data = fetch_post_data(article, journal, mhs_submissionpage, is_interactive, user)
    response = call_mhs_submission(journal_id=get_journal_id(journal), api_key=get_journal_api_key(journal),
                                submission_id=article_id, post_data=post_data) #Mode journal_id, journal_api_key?
    print(response)
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

# TODO check if user is editor or section editor
# TODO dont reveal personal information to section editors
@decorators.has_journal
@decorators.editor_user_required_and_can_see_pii
def rqc_grading_articles(request):
    """
    Displays a list of articles in the RQC Grading stage.
    :param request: HttpRequest
    :return: HttpResponse
    """
    article_filter = request.GET.get('filter', None)
    articles_in_rqc_grading = submission_models.Article.objects.filter(
        journal = request.journal,
        stage = plugin_settings.STAGE,
    )

    # Articles with at least one submitted review should also be listed.
    # In case an RQCGuardian wants to grade some of the reviews before making an editorial decision

    reviewed_articles = submission_models.Article.objects.filter(
        journal = request.journal,
        stage = submission_models.STAGE_UNDER_REVIEW,
        reviewassignment__is_complete = True
    )

    template = 'rqc_adapter/rqc_grading_articles.html'
    context = {
        'articles_in_rqc_grading': articles_in_rqc_grading,
        'reviewed_articles': reviewed_articles,
        'filter': article_filter,
    }
    return render(request, template, context)


# Does an rqc request contain personally identifiable information?
# TODO Check for conflict of interest?

@decorators.has_journal
@decorators.editor_user_required_and_can_see_pii # Checks if the user is an editor or section editor assigned to the article #TODO dos this work?
def rqc_grade_article_reviews(request, article_id):
    article = get_object_or_404(
        submission_models.Article,
        pk=article_id,
        journal=request.journal,
    )
    template = 'rqc_adapter/rqc_grade_article_reviews.html'
    context = {
        'article': article,
    }
    return render(request, template, context)

# TODO add reviewer opting
# TODO should a user be able to manually enter the url and change opting status?
# TODO check user login?
# TODO user should be able to get here manually

# The request must provide a journal object because the opting decision in specific to the journal
# Only reviewers should be able to opt in or out of participating in RQC
@decorators.has_journal
@decorators.reviewer_user_required
def reviewer_opting_form(request):
    template = 'rqc_adapter/reviewer_opting_form.html'
    try:
        opting_status = RQCReviewerOptingDecision.objects.get(reviewer=request.user, journal=request.journal)
        if opting_status.is_valid:
            messages.info(request,
                          'You have already decided whether to participate or not participate in RQC for this journal and journal year.')
            return redirect('core_dashboard')
    except RQCReviewerOptingDecision.DoesNotExist:
        pass
    form = forms.ReviewerOptingForm(initial={'status_selection_field': RQCReviewerOptingDecision.OptingChoices.OPT_IN})
    return render(request, template, {'form': form})
#
# TODO get user and opting submission info
# TODO ? @login_required
# TODO what if there is no logged in user?
# TODO add info messages for other settings udapted
# TODO check if user is a reviewer!!!

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
            RQCReviewerOptingDecision.objects.update_or_create(reviewer = user, journal= request.journal ,opting_status=opting_status)
            if opting_status == RQCReviewerOptingDecision.OptingChoices.OPT_IN:
                messages.info(request, 'Thank you for choosing to participate in RQC!')
            else:
                messages.info(request, 'Thank you for your response. Your preference has been recorded.')
            return redirect('core_dashboard')
    else:
        return redirect('core_dashboard')
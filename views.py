from datetime import timedelta, timezone
from http.client import HTTPResponse
from django.utils.timezone import now

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from journal.models import Journal
from plugins.rqc_adapter.rqc_calls import call_mhs_submission, fetch_post_data
from security import decorators
from submission import models as submission_models

from core.models import SettingValue
from plugins.rqc_adapter import forms, plugin_settings
from plugins.rqc_adapter.plugin_settings import set_journal_id, set_journal_api_key, has_salt, set_journal_salt, \
    get_journal_id, get_journal_api_key, has_journal_id, has_journal_api_key, get_salt
from plugins.rqc_adapter.utils import encode_file_as_b64, convert_review_decision_to_rqc_format, get_editorial_decision, create_pseudo_address
from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCDelayedCall


def manager(request):
    template = 'rqc_adapter/manager.html'
    journal = request.journal

    if has_journal_id(journal) and has_journal_api_key(journal):
        journal_id = get_journal_id(journal)
        journal_api_key = get_journal_api_key(journal)
        form = forms.RqcSettingsForm(initial={'journal_id_field': journal_id, 'journal_api_key_field': journal_api_key})
    else:
        form = forms.RqcSettingsForm()
    return render(request, template, {'form': form})

#TODO create new settingvalue if object doesnt exist yet
def handle_journal_settings_update(request):
    journal = request.journal
    if request.method == 'POST':
        form = forms.RqcSettingsForm(request.POST)
        if form.is_valid():
            journal_id = form.cleaned_data['journal_id_field']
            set_journal_id(journal_id, journal)
            journal_api_key = form.cleaned_data['journal_api_key_field']
            set_journal_api_key(journal_api_key, journal)
        return redirect('rqc_adapter_manager')

    else:
        journal_id = SettingValue.objects.get(setting__name='rqc_journal_id')
        journal_api_key = SettingValue.objects.get(setting__name='rqc_journal_api_key')
        form = forms.RqcSettingsForm(initial={'journal_id_field': journal_id.value, 'journal_api_key_field': journal_api_key.value})
        return render(request,'rqc_adapter/manager.html',{'form':form})


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
@decorators.has_journal
@decorators.production_user_or_editor_required
def submit_article_for_grading(request, article_id):
    referer = request.META.get('HTTP_REFERER')
    article = get_object_or_404(
        submission_models.Article,
        pk=article_id,
        journal=request.journal,  #TODO?
    )
    journal = article.journal #TODO ?
    user = request.user
    mhs_submissionpage = request.META.get('HTTP_REFERER')
    post_data = fetch_post_data(user, article, article_id, journal, mhs_submissionpage, interactive = True)
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
def reviewer_opting_form(request):
    template = 'rqc_adapter/reviewer_opting_form.html'
    try:
        initial_value = RQCReviewerOptingDecision.objects.get(reviewer=request.user).opting_status
    except RQCReviewerOptingDecision.DoesNotExist:
        initial_value = RQCReviewerOptingDecision.OptingChoices.OPT_IN
    form = forms.ReviewerOptingForm(initial={'status_selection_field': initial_value})
    return render(request, template, {'form': form})
#
# TODO get user and opting submission info
# TODO ? @login_required
# TODO what if there is no logged in user?
# TODO add info messages for other settings udapted
# TODO check if user is a reviewer!!!
def set_reviewer_opting_status(request):
    if request.method == 'POST':
        form = forms.ReviewerOptingForm(request.POST)
        if form.is_valid():
            opting_status = form.cleaned_data['status_selection_field']
            user = request.user
            current_status, created = RQCReviewerOptingDecision.objects.update_or_create(reviewer = user, opting_status=opting_status)
            return redirect('rqc_adapter_reviewer_opting_form')
    else:
        return redirect('rqc_adapter_reviewer_opting_form')
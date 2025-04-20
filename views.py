from django.core.checks import messages
from django.shortcuts import render, redirect, get_object_or_404

from journal.models import Journal
from plugins.rqc_adapter.rqc_calls import call_mhs_submission
from security import decorators
from submission import models as submission_models

from core.models import SettingValue
from plugins.rqc_adapter import forms, plugin_settings
from plugins.rqc_adapter.plugin_settings import set_journal_id, set_journal_api_key, has_salt, set_journal_salt, \
    get_journal_id, get_journal_api_key, has_journal_id, has_journal_api_key, get_salt
from plugins.rqc_adapter.utils import encode_file_as_b64, convert_review_decision_to_rqc_format, get_editorial_decision, create_pseudo_address
from plugins.rqc_adapter.models import RQCReviewerOptingDecision


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
@decorators.has_journal
@decorators.production_user_or_editor_required
def submit_article_for_grading(request, article_id):
    article = get_object_or_404(
        submission_models.Article,
        pk=article_id,
        journal=request.journal,  #TODO?
    )
    journal = article.journal #TODO ?
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
        submission_data['mhs_submissionpage'] = request.META.get('HTTP_REFERER') # open redirect vulnerabilities?
    else:
        submission_data['mhs_submissionpage'] = ""

    #title - length?
    submission_data['title'] = article.title

    # external uid
    submission_data['external_uid'] = article_id
    #visible uid - remove characters that cant appear in url
    submission_data['visible_uid'] = article_id

    # submission date check date time - utc?
    submission_data['submitted'] = article.date_submitted

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
            'firstname': author.first_name,
            'lastname': author.last_name,
            'orcid_id': author.orcid,
            'order_number': author_order.get(author=author).order #TODO what if article,author is not unique
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
            'firstname': editor.first_name,
            'lastname': editor.last_name,
            'orcid_id': editor.orcid,
            'level': 1  # TODO what about different levels
        }
        submission_data['editor_set'].append(editor_data)

    # reviewerset
    # TODO handle opted out reviewers
    submission_data['review_set'] = []
    review_assignments = article.reviewassignment_set.all() #TODO what if there is not reviewassignment -> no call should be possible os that guarenteed?
    num_reviews = 0
    for review_assignment in review_assignments:
        reviewer = review_assignment.reviewer
        review_file = review_assignment.review_file
        review_text = ""
        for review_answer in review_assignment.review_form_answers(): #TODO whats going on with multiple answers
             if review_answer.answer is not None:
                review_text = review_text + review_answer.answer
        review_data = {
            'visible_id': num_reviews+1, #TODO is that ok?
            'invited': review_assignment.date_requested,
            'agreed':  review_assignment.date_accepted,
            'expected': review_assignment.date_due,
            'submitted': review_assignment.date_complete, #TODO correct timing utc?
            'text': review_text,
            'suggested_decision': convert_review_decision_to_rqc_format(review_assignment.decision),
            'is_html': 'true',  # review_file.mime_type in ["text/html"]  # TODO is the mime type correct?
        }
        try:
            opting_status = review_assignment.reviewer.rqcrevieweroptingdecision.opting_status
        except (AttributeError, RQCReviewerOptingDecision.DoesNotExist):
            opting_status = None
        if opting_status == RQCReviewerOptingDecision.OptingChoices.OPT_IN:   #TODO treat no opting decision as opt out
            reviewer = {
                'email': reviewer.email,
                'firstname': reviewer.first_name,
                'lastname': reviewer.last_name,
                'orcid_id': reviewer.orcid
            }
        else:
            if not has_salt(journal):
                salt = set_journal_salt(journal)
            else:
                salt = get_salt(journal)
            reviewer = {
                'email': create_pseudo_address(reviewer.email,salt),
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
    submission_data['decision'] = get_editorial_decision(article) #TODO redo revision request by querying for revisionrequest objects
    print(submission_data) #TODO remove
    value = call_mhs_submission(journal_id = get_journal_id(journal), api_key= get_journal_api_key(journal), submission_id= article_id, post_data= submission_data)
    return value


def rqc_grading_articles(request):
    """
    Displays a list of articles in the RQC Grading stage.
    :param request: HttpRequest
    :return: HttpResponse
    """
    article_filter = request.GET.get('filter', None)
    articles_in_rqc_grading = submission_models.Article.objects.filter(
        journal=request.journal,
        stage=plugin_settings.STAGE,
    )
    template = 'rqc_adapter/rqc_grading_articles.html'
    context = {
        'articles_in_rqc_grading': articles_in_rqc_grading,
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
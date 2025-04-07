from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from security import decorators
from security.decorators import author_user_required
from submission import models as submission_models

from core.models import SettingValue
from plugins.rqc_adapter import forms
from plugins.rqc_adapter.utils import set_journal_id, set_journal_api_key, encode_file_as_b64, \
    convert_review_decision_to_rqc_format, get_editorial_decision, create_pseudo_address, has_salt, set_journal_salt
from plugins.rqc_adapter.models import RQCReviewerOptingDecision


def manager(request):
    template = 'rqc_adapter/manager.html'
    journal_id = SettingValue.objects.get(setting__name='rqc_journal_id')
    journal_api_key = SettingValue.objects.get(setting__name='rqc_journal_api_key')
    if journal_id.value and journal_api_key.value:
        form = forms.RqcSettingsForm(initial={'journal_id_field': journal_id.value, 'journal_api_key_field': journal_api_key.value})
    else:
        form = forms.RqcSettingsForm()
    return render(request, template, {'form': form})

#TODO create new settingvalue if object doesnt exist yet
def handle_journal_id_settings_update(request):
    if request.method == 'POST':
        form = forms.RqcSettingsForm(request.POST)
        if form.is_valid():
            journal_id = request.data.get('journal_id')
            set_journal_id(journal_id)
            journal_api_key = request.data.get('api_key')
            set_journal_api_key(journal_api_key)
        return redirect('rqc_adapter_manager')
    else:
        journal_id = SettingValue.objects.get(setting__name='rqc_journal_id')
        journal_api_key = SettingValue.objects.get(setting__name='rqc_journal_api_key')
        form = forms.RqcSettingsForm(initial={'journal_id_field': journal_id, 'journal_api_key_field': journal_api_key})
        return render(request,'rqc_adapter/manager.html',{'form':form})

def grading_articles(request):
    print("Test")
    template = 'rqc_adapter/manager.html'
    return render(request, template)

@decorators.has_journal
@decorators.production_user_or_editor_required
def submit_article_for_grading(request, article_id):
    article = get_object_or_404(
        submission_models.Article,
        pk=article_id,
        journal=request.journal,
    )

    submission_data = {}

    # interactive user get from request
    # how to check if there is a user
    if hasattr(request.user, 'id') and request.user.id is not None:
        submission_data['interactive_user'] = request.user.email
    else:
        submission_data['interactive_user'] = ""

    # submission page - redirect to the page from where the post request came from
    # if interactive user is empty this should be emtpy aswell
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
            'order_number': author_order.filter(author=author).order
    }
    author_set.append(author_info)
    submission_data['author_set'] = author_set

    # editor_assginemnt set -> for each
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
    review_assignments = article.reviewassignment_set.all()
    num_reviews = 0
    for review_assignment in review_assignments:
        reviewer = review_assignment.reviewer
        review_file = review_assignment.review_file
        review_text = ""
        for review_answer in review_assignment.review_form_answers(): #TODO whats going on with multiple answers
            review_text = review_text + review_answer.edited_answer
        review_data = {
            'visible_id': num_reviews+1,
            'invited': review_assignment.date_requested,
            'agreed':  review_assignment.date_accepted,
            'expected': review_assignment.date_due,
            'submitted': review_assignment.date_complete, #TODO correct timing utc?
            'text': review_text,
            'suggested_decision': convert_review_decision_to_rqc_format(review_assignment.decision),
        }
        if review_assignment.reviewer.rqcrevieweroptingdecision.opting_status == RQCReviewerOptingDecision.OptingChoices.OPT_IN:
            reviewer = {
                'email': reviewer.email,
                'firstname': reviewer.first_name,
                'lastname': reviewer.last_name,
                'orcid_id': reviewer.orcid
            }
        else:
            if not has_salt(request.journal):
                salt = set_journal_salt(request.journal)
            else:
                salt = SettingValue.objects.get(setting__name='rqc_journal_salt').value
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
        if review_file is not None:
            attachments = {
                'filename': review_file.original_filename,
                'data': encode_file_as_b64(review_file.uuid_filename,article_id),
                'is_html': review_file.mime_type in ["text/html"] #TODO is the mime type correct?
            }
            review_data['attachments'] = attachments
        submission_data['review_set'].append(review_data)

    # decision
    submission_data['decision'] = get_editorial_decision(article)
    return
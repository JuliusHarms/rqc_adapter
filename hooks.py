"""
© Julius Harms, Freie Universität Berlin 2025

This file contains the functions that register for hooks and determine the rendered content
if that hook is triggered.
"""

from django.template.loader import render_to_string

from review.models import ReviewAssignment

from plugins.rqc_adapter import forms
from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCJournalAPICredentials
from plugins.rqc_adapter.utils import has_opted_in_or_out

def render_rqc_grading_action(context):
    """
    Returns the string for rendering the 'Grade in RQC' action in the Editors
    action menu when the 'in_review_editor_actions' hook is triggered.
    """
    request = context['request']
    article = context['article']
    journal = request.journal
    # Only render the element if the journal has valid credentials.
    has_api_credentials = RQCJournalAPICredentials.objects.filter(journal=journal).exists()
    if not has_api_credentials:
        return ''
    # If there are review assignments for the article that have been accepted
    # but not yet completed the reviewer needs to be informed before sending the
    # data to RQC.
    if ReviewAssignment.objects.filter(article=article, date_accepted__isnull=False, is_complete=True).exists():
        has_outstanding_reviews = True
    else:
        has_outstanding_reviews = False
    string = render_to_string('rqc_adapter/grading_action.html', context={'request': request,'article': context['article'], 'has_outstanding_reviews': has_outstanding_reviews })
    return string

def render_reviewer_opting_form(context):
    """
    Returns the string for rendering the reviewer opting form
    when the 'review_form_guidelines' hook is triggered as is defined in plugin_settings.
    """
    request = context['request']
    journal = request.journal
    user = request.user
    # Only render the opting form if the journal has valid credentials and user has not made
    # the decision to opt in or out.
    # Validity of the credentials is checked upon entering the settings (not here).
    # Additional validation via another API call is too costly.
    has_api_credentials = RQCJournalAPICredentials.objects.filter(journal=journal).exists()
    if has_api_credentials and not has_opted_in_or_out(user, journal):
        form = forms.ReviewerOptingForm(initial={'status_selection_field': RQCReviewerOptingDecision.OptingChoices.OPT_IN})
        return render_to_string('rqc_adapter/reviewer_opting_form.html', context={'request': request, 'form': form})
    else:
        return ''
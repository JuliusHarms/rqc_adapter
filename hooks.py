"""
© Julius Harms, Freie Universität Berlin 2025
"""

from django.template.loader import render_to_string
from plugins.rqc_adapter import forms
from plugins.rqc_adapter.models import RQCReviewerOptingDecision
from plugins.rqc_adapter.plugin_settings import has_journal_api_key, has_journal_id
from plugins.rqc_adapter.utils import has_opted_in_or_out

# TODO work over
def render_rqc_grading_action(context):
    request = context['request']
    string = render_to_string('rqc_adapter/grading_action.html', context={'request': request,'article': context['article']})
    return string

def render_reviewer_opting_form(context):
    request = context['request']
    journal = request.journal
    user = request.user
    # Only render the opting form if the journal has valid credentials and user has not made the decision to opt in or out.
    # Validity of the credentials is checked upon entering the settings (not here).
    # Additional validation via another API call is too costly.
    if has_journal_api_key(journal) and has_journal_id(journal) and not has_opted_in_or_out(user, journal):
        form = forms.ReviewerOptingForm(initial={'status_selection_field': RQCReviewerOptingDecision.OptingChoices.OPT_IN})
        return render_to_string('rqc_adapter/reviewer_opting_form.html', context={'request': request, 'form': form})
    else:
        return ''
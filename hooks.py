from django.template.loader import render_to_string
from plugins.rqc_adapter import forms
from plugins.rqc_adapter.models import RQCReviewerOptingDecision


def render_reviewer_opting_link(context):
    request = context['request']
    return  render_to_string('rqc_adapter/reviewer_dashboard_opting_link.html', context={})

def render_rqc_grading_action(context):
    request = context['request']
    string = render_to_string('rqc_adapter/grading_action.html', context={'article': context['article']})
    return string

def render_reviewer_opting_form(context):
    request = context['request']
    form = forms.ReviewerOptingForm(initial={'status_selection_field': RQCReviewerOptingDecision.OptingChoices.OPT_IN})
    return render_to_string('rqc_adapter/reviewer_opting_form.html', context={'request': request, 'form': form})
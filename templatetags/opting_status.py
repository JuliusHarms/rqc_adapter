from django import template

from plugins.rqc_adapter.models import RQCReviewerOptingDecision

register = template.Library()

@register.simple_tag(takes_context=True)
def has_submitted_opting_status(context):
    request = context['request']
    try:
        status = RQCReviewerOptingDecision.objects.get(reviewer=request.user)
    except RQCReviewerOptingDecision.DoesNotExist:
        return False
    if status.is_valid:
        return True
    else:
        return False

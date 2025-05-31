from django import template

from plugins.rqc_adapter import plugin_settings
from submission import models as submission_models

register = template.Library()

@register.simple_tag(takes_context=True)
def articles_in_rqc_stage_count(context):
    request = context['request']
    return submission_models.Article.objects.filter(
        journal = request.journal,
        stage = plugin_settings.STAGE,
    ).count()

@register.simple_tag(takes_context=True)
def reviewed_articles_count(context):
    request = context['request']
    return submission_models.Article.objects.filter(
        journal = request.journal,
        stage = submission_models.STAGE_UNDER_REVIEW,
        reviewassignment__is_complete = True
    ).count()


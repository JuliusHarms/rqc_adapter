"""
© Julius Harms, Freie Universität Berlin 2025
"""

from django.contrib import admin

from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCDelayedCall, \
    RQCReviewerOptingDecisionForReviewAssignment


class RQCReviewerOptingDecisionAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'journal', 'opting_status', 'opting_date')


class RQCReviewerOptingDecisionForReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'review_assignment', 'opting_status')

class RQCDelayedCallAdmin(admin.ModelAdmin):
    list_display = ('article', 'remaining_tries', 'last_attempt_at', 'failure_reason')

#TODO should i even do this?
class RQCJournalAPICredentialsAdmin(admin.ModelAdmin):
    list_display = ('journal', 'journal_id', 'api_key')

admin.site.register(RQCReviewerOptingDecision, RQCReviewerOptingDecisionAdmin)
admin.site.register(RQCReviewerOptingDecisionForReviewAssignment, RQCReviewerOptingDecisionForReviewAssignmentAdmin)
admin.site.register(RQCDelayedCall, RQCDelayedCallAdmin)

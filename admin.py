"""
© Julius Harms, Freie Universität Berlin 2025

This file defines the fields shown in the Django admin interface.
"""

from django.contrib import admin

from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCDelayedCall, \
    RQCReviewerOptingDecisionForReviewAssignment


class RQCReviewerOptingDecisionAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'journal', 'opting_status')
    readonly_fields = ('opting_date',)

class RQCReviewerOptingDecisionForReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ('review_assignment', 'opting_status')

class RQCDelayedCallAdmin(admin.ModelAdmin):
    list_display = ('article', 'remaining_tries', 'last_attempt_at', 'failure_reason')

admin.site.register(RQCReviewerOptingDecision, RQCReviewerOptingDecisionAdmin)
admin.site.register(RQCReviewerOptingDecisionForReviewAssignment, RQCReviewerOptingDecisionForReviewAssignmentAdmin)
admin.site.register(RQCDelayedCall, RQCDelayedCallAdmin)

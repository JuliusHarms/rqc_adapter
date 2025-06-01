from django.contrib import admin
from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCDelayedCall, \
    RQCReviewerOptingDecisionForReviewAssignment
from utils import admin_utils as utils_admin_utils


class RQCReviewerOptingDecisionAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'journal', 'opting_status', 'opting_date')


class RQCReviewerOptingDecisionForReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ('reviewer', 'review_assignment', 'opting_status')


class RQCDelayedCallAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'remaining_tries', 'last_attempt_at', 'failure_reason')


admin.site.register(RQCReviewerOptingDecision, RQCReviewerOptingDecisionAdmin)
admin.site.register(RQCDelayedCall, RQCDelayedCallAdmin)

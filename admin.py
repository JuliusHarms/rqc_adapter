from django.contrib import admin
from plugins.rqc_adapter.models import RQCReviewerOptingDecision
from utils import admin_utils as utils_admin_utils

class RQCReviewerOptingDecisionAdmin(admin.ModelAdmin):
    list_display = ('reviewer','opting_status','opting_date')

admin.site.register(RQCReviewerOptingDecision, RQCReviewerOptingDecisionAdmin)
from datetime import timezone, datetime

from django.db import models
from django.contrib.auth.models import User

from core.janeway_global_settings import AUTH_USER_MODEL


class ReviewerOptingDecisionStatus(models.Model):
    # add preliminary opting statuses - what do they do? -> used if a draft of the form is saved?
    # opting status needs to be year specific
    class RqcOptingChoices(models.IntegerChoices):
        UNDEFINED = 30, "RQC_OPTING_STATUS_UNDEFINED"
        OPT_IN = 31, "RQC_OPTING_STATUS_OPT_IN"
        OPT_OUT = 32, "RQC_OPTING_STATUS_OPT_OUT"
        #OPT_IN_PRELIM = 35, "RQC_OPTING_STATUS_OPT_IN_PRELIM"
        #OPT_OUT_PRELIM = 36, "RQC_OPTING_STATUS_OPT_OUT_PRELIM"

    rqc_opting_status = models.IntegerField(choices=RqcOptingChoices.choices, default=RqcOptingChoices.UNDEFINED)
    rqc_opting_date = models.DateTimeField(auto_now_add=True)
    user = models.OneToOneField(AUTH_USER_MODEL, on_delete=models.CASCADE)

    def is_valid(self):
        """
        Return True if the opting decision is valid for the current UTC year.
        """
        return self.rqc_opting_date.year == datetime.now(timezone.utc).year #utc?

    class Meta:
        verbose_name = "RQC Opting Decision"
        verbose_name_plural = "RQC Opting Decisions"

from datetime import timezone, datetime

from django.db import models

from core.janeway_global_settings import AUTH_USER_MODEL


class RQCReviewerOptingDecision(models.Model):
    class OptingChoices(models.IntegerChoices):
        UNDEFINED = 30, "RQC_OPTING_STATUS_UNDEFINED"
        OPT_IN = 31, "RQC_OPTING_STATUS_OPT_IN"
        OPT_OUT = 32, "RQC_OPTING_STATUS_OPT_OUT"

    opting_status = models.IntegerField(choices=OptingChoices.choices, default=OptingChoices.UNDEFINED)
    opting_date = models.DateTimeField(auto_now_add=True)
    reviewer = models.OneToOneField(AUTH_USER_MODEL, on_delete=models.CASCADE)

    @property
    def is_valid(self):
        """
        Return True if the opting decision is valid for the current UTC year.
        """
        return self.opting_date.year == datetime.now(timezone.utc).year #utc?

    class Meta:
        verbose_name = "RQC Opting Decision"
        verbose_name_plural = "RQC Opting Decisions"

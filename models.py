from datetime import timezone, datetime

from django.db import models

from core.janeway_global_settings import AUTH_USER_MODEL
from journal.models import Journal
from submission.models import Article


class RQCReviewerOptingDecision(models.Model):
    class OptingChoices(models.IntegerChoices):
        UNDEFINED = 30, ""
        OPT_IN = 31, "Yes, take part in RQC"
        OPT_OUT = 32, "No, opt out from RQC"

    opting_status = models.IntegerField(choices=OptingChoices.choices, default=OptingChoices.UNDEFINED)
    opting_date = models.DateTimeField(auto_now_add=True)
    reviewer = models.OneToOneField(AUTH_USER_MODEL, on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE)

    @property
    def is_valid(self):
        """
        Return true if the opting decision is valid for the current UTC year.
        """
        return self.opting_date.year == datetime.now(timezone.utc).year

    class Meta:
        verbose_name = "RQC Opting Decision"
        verbose_name_plural = "RQC Opting Decisions"


class RQCDelayedCall(models.Model):
    remaining_tries = models.IntegerField(default=10)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)  # TODO cascade? probably yes but if reviews are holy maybe i should save the call data and then submit to rqc anyway
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)
    last_attempt_at = models.DateTimeField()
    failure_reason = models.TextField()
    @property
    def is_valid(self):
        if self.remaining_tries <= 0:
            return False
        return True

    def delete_self(self):
        self.delete()


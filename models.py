"""
© Julius Harms, Freie Universität Berlin 2025
"""

from datetime import timezone, datetime

from django.db import models

from core.models import Account
from journal.models import Journal
from submission.models import Article
from review.models import ReviewAssignment


class RQCReviewerOptingDecision(models.Model):
    class OptingChoices(models.IntegerChoices):
        UNDEFINED = 0, ""
        OPT_IN = 1, "Yes, take part in RQC"
        OPT_OUT = 2, "No, opt out from RQC"

    opting_status = models.IntegerField(choices=OptingChoices.choices, null=False, blank=False, default=OptingChoices.UNDEFINED)
    opting_date = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    reviewer = models.OneToOneField(Account, null=False, blank=False, on_delete=models.CASCADE)
    journal = models.ForeignKey(Journal, null=False, blank=False, on_delete=models.CASCADE)

    @property
    def is_valid(self):
        """
        Return true if the opting decision is valid for the current UTC year.
        """
        return self.opting_date.year == datetime.now(timezone.utc).year

    class Meta:
        verbose_name = "RQC Opting Decision"
        verbose_name_plural = "RQC Opting Decisions"

# The opting decision of a reviewer is attached to a review assignment if that reviewer has given a participation preference
# for that journal year and accepted to review an article or completed his or her review of an article.
# This helps ensure consistent behaviour on the side of RQC incase the reviewing process for an article spans multiple years
# and delimits which articles are included in a reviewers yearly receipt.
# TODO check this text
class RQCReviewerOptingDecisionForReviewAssignment(models.Model):
    opting_status = models.IntegerField(choices=RQCReviewerOptingDecision.OptingChoices.choices, null=False, blank=False, default=RQCReviewerOptingDecision.OptingChoices.UNDEFINED)
    reviewer = models.OneToOneField(Account, null=False, blank=False, on_delete=models.CASCADE)
    review_assignment = models.ForeignKey(ReviewAssignment, null=False, blank=False, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "RQC Reviewer Opting Decision for ReviewAssignment"
        verbose_name_plural = "RQC Reviewer Opting Decisions for ReviewAssignments"

class RQCDelayedCall(models.Model):
    remaining_tries = models.IntegerField(default=10, null=False, blank=False)
    article = models.ForeignKey(Article, null=False, blank=False, on_delete=models.CASCADE)
    last_attempt_at = models.DateTimeField(null=True, blank=True) #TODO review!
    failure_reason = models.TextField(null=True, blank=True)
    @property
    def is_valid(self):
        if self.remaining_tries <= 0:
            return False
        return True

    def delete_self(self):
        self.delete()

    class Meta:
        verbose_name = "RQC Delayed Call"
        verbose_name_plural = "RQC Delayed Calls"

class RQCJournalAPICredentials(models.Model):
    journal = models.ForeignKey(Journal, null=False, blank=False, on_delete=models.CASCADE)
    journal_id = models.IntegerField(null=False, blank=False)
    api_key = models.TextField(null=False, blank=False)

    class Meta:
        verbose_name = "RQC Journal Credentials"
        verbose_name_plural = "RQC Journal Credentials"


class RQCJournalSalt(models.Model):
    journal = models.ForeignKey(Journal, null=False, blank=False, on_delete=models.CASCADE)
    salt = models.TextField(null=False, blank=False)
    class Meta:
        verbose_name = "RQC Journal Salt"
        verbose_name_plural = "RQC Journal Salt"

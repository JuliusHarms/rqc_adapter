from django.db import models
from django.contrib.auth.models import User

class ReviewerOptingDecisionStatus(models.Model):
    # add preliminary opting statuses - what do they do?
    # opting status needs to be year specific
    status_in = "RQC_OPTING_STATUS_IN"
    status_out = "RQC_OPTING_STATUS_OUT"
    status_in_prelim = "RQC_OPTING_STATUS_IN_PRELIM"
    status_out_prelim = "RQC_OPTING_STATUS_OUT_PRELIM"
    status_undefined = "RQC_OPTING_STATUS_UNDEFINED"
    RQC_OPTING_CHOICES = {
        status_in: 36,
        status_out: 35,
        status_in_prelim: 32,
        status_out_prelim: 31,
        status_undefined: 30
    }
    rqc_opting_status = models.IntegerField(choices=RQC_OPTING_CHOICES, default=30)
    rqc_opting_date = models.DateTimeField(auto_now_add=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
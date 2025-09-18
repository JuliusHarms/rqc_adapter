"""
© Julius Harms, Freie Universität Berlin 2025

This file contains tests for calls to the mhs_submission endpoint.
"""
import os
from unittest import skipUnless

from django.forms.models import model_to_dict

from plugins.rqc_adapter.models import RQCJournalAPICredentials
from plugins.rqc_adapter.tests.base_test import RQCAdapterBaseTestCase
from django.urls import reverse

has_api_credentials_env = os.getenv("RQC_API_KEY") and os.getenv("RQC_JOURNAL_ID")
class TestCallsToMHSSubmissionEndpoint(RQCAdapterBaseTestCase):

    explicit_call_button_template = 'rqc_adapter/grading_action.html'

    post_to_rqc_view = 'rqc_adapter_submit_article_for_grading'

    def post_to_rqc(self, article_id):
        return self.client.post(reverse(self.post_to_rqc_view, args=[article_id]))

    def setUp(self):
        super().setUp()
        self.create_session_with_editor()



# data is correctly fetched

# RQC-Service Contacted


# Salt Creation if not yet existent

# Opt-In Opt-Out - correctly handled


# Integration with RQC API

@skipUnless(has_api_credentials_env, "No API key found. Cannot make API call integration tests.")
class TestSubmissionCallsAPIIntegration(TestCallsToMHSSubmissionEndpoint):
    # Happy path -
    def setUp(self):
        super().setUp()
        if has_api_credentials_env:
            RQCJournalAPICredentials.objects.create(journal=self.journal_one, rqc_journal_id=self.rqc_journal_id, api_key=self.rqc_api_key)

    def test_make_successful_call(self):
        print(model_to_dict(self.active_article))
        response = self.post_to_rqc(self.active_article.id)
        print(response.json())
        self.assertEqual(response.status_code, 302)
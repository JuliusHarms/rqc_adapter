"""
© Julius Harms, Freie Universität Berlin 2025

This file contains tests for calls to the mhs_submission endpoint.
"""
import os
from lib2to3.pytree import convert
from unittest import skipUnless

from django.contrib.messages import get_messages
from django.forms.models import model_to_dict
from django.utils import timezone

from plugins.rqc_adapter.models import RQCJournalAPICredentials, RQCReviewerOptingDecision, \
    RQCReviewerOptingDecisionForReviewAssignment
from plugins.rqc_adapter.tests.base_test import RQCAdapterBaseTestCase
from django.urls import reverse

from plugins.rqc_adapter.utils import convert_date_to_rqc_format

has_api_credentials_env = os.getenv("RQC_API_KEY") and os.getenv("RQC_JOURNAL_ID")

class TestCallsToMHSSubmissionEndpoint(RQCAdapterBaseTestCase):

    explicit_call_button_template = 'rqc_adapter/grading_action.html'
    review_management_template = 'review/in_review.html'

    post_to_rqc_view = 'rqc_adapter_submit_article_for_grading'
    review_management_view = 'review_in_review'

    def post_to_rqc(self, article_id, domain=None):
        if domain is None:
            return self.client.post(reverse(self.post_to_rqc_view, args=[article_id]))
        else:
            return self.client.post(reverse(self.post_to_rqc_view, args=[article_id]), HTTP_HOST=domain)

    def get_review_management(self, article_id):
        return self.client.get(reverse(self.review_management_view, args=[article_id]))

    def opt_in_reviewer_one(self):
        RQCReviewerOptingDecision.objects.create(reviewer=self.reviewer_one, journal=self.journal_one, opting_status=self.OPT_IN)
        RQCReviewerOptingDecisionForReviewAssignment.objects.create(review_assignment=self.review_assignment, opting_status=self.OPT_IN)

    def setUp(self):
        super().setUp()
        self.create_session_with_editor()

class TestCallsToMHSSubmissionEndpointMocked(TestCallsToMHSSubmissionEndpoint):
    pass

class TestExplicitCalls(TestCallsToMHSSubmissionEndpointMocked):
    pass

# Data is correctly fetched

# RQC-Service Contacted

# Salt Creation if not yet existent

# Opt-In Opt-Out - correctly handled

# Implicit Calls
class TestImplicitCalls(TestCallsToMHSSubmissionEndpointMocked):

    make_editorial_decision_view = 'review_decision'
    request_revisions_view = 'review_request_revisions'

    def make_editorial_decision(self, decision):
        form_data = {
            "to_address": "author@example.com",
            "subject": "Test",
            "body": "Test",
        }
        self.client.post(reverse(self.make_editorial_decision_view, args=[self.active_article.id, decision]), form_data)

    def make_revision_request(self, revision_type):
        form_data = {
            "date_due": (timezone.now() + timedelta(days=7)).date(),
            "type": revision_type,
            "editor_note": "Please fix these issues",
        }
        self.client.post(reverse(self.request_revisions_view, args=[self.active_article.id]), form_data)

    def test_implicit_calls_with_article_argument(self):
        kwargs = {
            'article': self.active_article,
            'request': None
        }
        implicit_call_mhs_submission(**kwargs)
        self.mock_call.assert_called()

    def test_implicit_calls_with_revisions_argument(self):
        revision_request = RevisionRequest.objects.create(
            article=self.active_article,
            editor=self.editor,
            date_due=timezone.now()+timedelta(days=7),
            type='minor_revisions',
            editor_note="Please fix these issues",
        )
        kwargs = {
            'revision': revision_request,
            'request': None
        }
        implicit_call_mhs_submission(**kwargs)
        self.mock_call.assert_called()

    def test_implicit_call_made_upon_editorial_decision(self):
        editorial_decisions = ['accept', 'decline', 'undecline']
        for decision in editorial_decisions:
            self.make_editorial_decision(decision)
            self.mock_call.assert_called()

    # TODO currently should not work due to the ON_REVISIONS_REQUEST event not firing
    def test_implicit_call_made_upon_revisions_requested(self):
        revision_types = ["minor_revisions", "major_revisions"]
        for revision_type in revision_types:
            self.make_revision_request(revision_type)
            self.assertTrue(
                RevisionRequest.objects.filter(
                    article=self.active_article, editor=self.editor
                ).exists()
            )
            self.mock_call.assert_called()

# Delayed Calls
class TestDelayedCalls(TestCallsToMHSSubmissionEndpointMocked):
    pass

# Integration with RQC API
@skipUnless(has_api_credentials_env, "No API key found. Cannot make API call integration tests.")
class TestSubmissionCallsAPIIntegration(TestCallsToMHSSubmissionEndpoint):
    def setUp(self):
        super().setUp()
        if has_api_credentials_env:
            self.create_journal_credentials(self.journal_one, self.rqc_journal_id, self.rqc_api_key)

        # Without a valid Url-Domain RQC rejects the request
        self.journal_one.domain = 'example.com'
        self.journal_one.save()

    def test_make_successful_call(self):
        self.opt_in_reviewer_one()
        self.get_review_management(self.active_article.id)
        response = self.post_to_rqc(self.active_article.id, self.journal_one.domain)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Successfully submitted article.', [m.message for m in messages])
        self.assertEqual(response.status_code, 302)
"""
© Julius Harms, Freie Universität Berlin 2025

This file contains tests for calls to the mhs_submission endpoint.
"""
import os
from datetime import timedelta
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.utils import timezone

from plugins.rqc_adapter.events import implicit_call_mhs_submission
from plugins.rqc_adapter.models import RQCReviewerOptingDecision, \
    RQCReviewerOptingDecisionForReviewAssignment, RQCDelayedCall
from plugins.rqc_adapter.rqc_calls import RQCErrorCodes
from plugins.rqc_adapter.tests.base_test import RQCAdapterBaseTestCase
from django.urls import reverse

from review.models import RevisionRequest
from review.views import review_decision

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
        """Makes a call to the review_decision view with form data."""
        form_data = {
            "to_address": "author@example.com",
            "subject": "Test",
            "body": "Test",
        }
        self.client.post(reverse(self.make_editorial_decision_view, args=[self.active_article.id, decision]), form_data)

    def make_revision_request(self, revision_type):
        """Makes a call to the request_revisions view with form data"""
        form_data = {
            "date_due": (timezone.now() + timedelta(days=7)).date(),
            "type": revision_type,
            "editor_note": "Please fix these issues",
        }
        self.client.post(reverse(self.request_revisions_view, args=[self.active_article.id]), form_data)

    def test_implicit_calls_with_article_argument(self):
        """Just Tests if implicit_call_mhs_submission function call results in a call to RQC"""
        kwargs = {
            'article': self.active_article,
            'request': None
        }
        implicit_call_mhs_submission(**kwargs)
        self.mock_call.assert_called()

    def test_implicit_calls_with_revisions_argument(self):
        """Tests if the implicit calls function works with a revision request object in kwargs"""
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
        """Tests if implicit calls are made upon editorial decision"""
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
    # Delayed Call created
    def test_delayed_call_created(self):
        """Test that a delayed call is created with the given status codes"""
        response_codes = list(range(500, 505)) + [RQCErrorCodes.CONNECTION_ERROR,
                                                  RQCErrorCodes.TIMEOUT, RQCErrorCodes.REQUEST_ERROR]
        for response_code in response_codes:
            self.mock_call.return_value = self.create_mock_call_return_value(success=False, http_status_code=response_code)
            self.post_to_rqc(self.active_article.id)
            self.mock_call.assert_called()
            self.assertTrue(RQCDelayedCall.objects.filter(article=self.active_article, failure_reason=str(response_code), remaining_tries=10).exists())

    def test_delayed_call_not_created(self):
        """Test that a delayed call is not created with the given status codes"""
        response_codes = [400,403,404, RQCErrorCodes.UNKNOWN_ERROR]
        for response_code in response_codes:
            self.mock_call.return_value = self.create_mock_call_return_value(success=False, http_status_code=response_code)
            self.post_to_rqc(self.active_article.id)
            self.mock_call.assert_called()
            self.assertFalse(RQCDelayedCall.objects.filter(article=self.active_article, failure_reason=str(response_code), remaining_tries=10).exists())

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
        """Tests a successful call to RQC with the credentials from the environment."""
        self.opt_in_reviewer_one()
        self.get_review_management(self.active_article.id)
        response = self.post_to_rqc(self.active_article.id, self.journal_one.domain)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Successfully submitted article.', [m.message for m in messages])
        self.assertEqual(response.status_code, 302)
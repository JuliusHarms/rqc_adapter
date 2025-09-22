"""
© Julius Harms, Freie Universität Berlin 2025

This file contains tests for calls to the mhs_submission endpoint.
"""
import os
from datetime import timedelta
from unittest import skipUnless
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.contrib.messages import get_messages
from django.core.management import call_command
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

    @staticmethod
    def create_mock_call_return_value(success=True,
                                      http_status_code=200,
                                      message=None, redirect_target=None):
       return	{
            'success': success,
            'http_status_code': http_status_code,
            'message': message,
            'redirect_target': redirect_target,
        }

    def call_and_get_args_back(self):
        self.post_to_rqc(self.active_article.id)
        self.mock_call.assert_called()
        args, kwargs = self.mock_call.call_args
        return args, kwargs

    def setUp(self):
        super().setUp()
        self.create_journal_credentials(self.journal_one, 9, 'Test key')
        patcher = patch('plugins.rqc_adapter.rqc_calls.call_rqc_api')
        self.mock_call = patcher.start()
        self.addCleanup(patcher.stop)

class TestExplicitCalls(TestCallsToMHSSubmissionEndpointMocked):

    def test_reviewer_anonymized_without_opt_in(self):
        """Tests if reviewers that are not opted in are anonymized."""
        args, kwargs = self.call_and_get_args_back()
        post_data = kwargs.get('post_data')
        review_set = post_data.get('review_set')
        review_one = review_set[0]
        self.assertEqual(review_one['text'], '')
        reviewer_email = review_one['reviewer']['email']
        self.assertNotEqual(reviewer_email, self.reviewer_one.email)
        self.assertTrue("@example.edu" in reviewer_email)

    def test_reviewer_not_anonymized_when_opted_in(self):
        """Tests that opted in reviewers are not anonymized."""
        self.opt_in_reviewer_one()
        args, kwargs = self.call_and_get_args_back()
        post_data = kwargs.get('post_data')
        review_set = post_data.get('review_set')
        review_one = review_set[0]
        # Review answer gets added to post data
        self.assertTrue("<p>Test Answer<p>" in review_one['text'])
        # Reviewer Email gets transmitted
        reviewer_email = review_one['reviewer']['email']
        self.assertEqual(reviewer_email, self.reviewer_one.email)

    def test_interactive_user_and_mhs_submissionpage_set(self):
        """Tests that interactive user and mhs_submissionpage are set when making an explicit call."""
        args, kwargs =self.call_and_get_args_back()
        post_data = kwargs.get('post_data')
        self.assertEqual(post_data['interactive_user'], self.editor.email)
        self.assertNotEqual(post_data['mhs_submissionpage'],reverse(self.review_management_view, args=[self.active_article.id]))

class TestImplicitCalls(TestCallsToMHSSubmissionEndpointMocked):

    make_editorial_decision_view = 'review_decision'
    request_revisions_view = 'review_request_revisions'

    # TODO interactive user is not set

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
        """Just tests if implicit_call_mhs_submission function call results in a call to RQC"""
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
    # Tests for the creation of delayed calls
    def test_delayed_call_created(self):
        """Test that a delayed call is created with the given status codes"""
        response_codes = [500, 502, 503, 504] + [RQCErrorCodes.CONNECTION_ERROR,
                                                  RQCErrorCodes.TIMEOUT, RQCErrorCodes.REQUEST_ERROR]
        for response_code in response_codes:
            self.mock_call.return_value = self.create_mock_call_return_value(success=False, http_status_code=response_code)
            reponse = self.post_to_rqc(self.active_article.id)
            self.mock_call.assert_called()
            self.assertTrue(RQCDelayedCall.objects.filter(article=self.active_article, failure_reason=str(response_code), remaining_tries=10).exists())

    def test_delayed_call_not_created(self):
        """Test that a delayed call is not created with the given status codes"""
        response_codes = [400,403,404, RQCErrorCodes.UNKNOWN_ERROR]
        for response_code in response_codes:
            self.mock_call.return_value = self.create_mock_call_return_value(success=False, http_status_code=response_code)
            self.post_to_rqc(self.active_article.id)
            self.mock_call.assert_called()
            self.assertFalse(RQCDelayedCall.objects.filter(article=self.active_article,
                                                           failure_reason=str(response_code),
                                                           remaining_tries=10).exists())

    @patch('rqc_adapter.management.commands.rqc_install_cronjob.crontab.CronTab')
    def test_cron_tab_created(self, mock_crontab):
        """Tests creation of crontab."""
        mock_tab = MagicMock()
        mock_job =MagicMock()
        mock_crontab.return_value = mock_tab
        mock_tab.new.return_value = mock_job

        with patch.dict(os.environ, {'VIRTUAL_ENV': 'mock/virtualenv'}):
            call_command('rqc_install_cronjob', action='install')
        mock_crontab.assert_called_once_with(user=True)
        expected_command = f"/mock/virtualenv/bin/python3 {settings.BASE_DIR}/manage.py rqc_make_delayed_calls"
        mock_tab.new.assert_called_once_with(expected_command)
        mock_job.setall.assert_called_once_with("0 8 * * *")
        mock_tab.write.assert_called_once()

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
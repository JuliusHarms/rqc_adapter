"""
© Julius Harms, Freie Universität Berlin 2025
"""

import os
from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

from core.context_processors import journal
from plugins.rqc_adapter.models import RQCReviewerOptingDecision, RQCJournalAPICredentials, \
    RQCReviewerOptingDecisionForReviewAssignment
from plugins.rqc_adapter.tests.base_test import RQCAdapterBaseTestCase
from utils.testing import helpers


class TestReviewerOpting(RQCAdapterBaseTestCase):

    OPT_IN = RQCReviewerOptingDecision.OptingChoices.OPT_IN
    OPT_OUT = RQCReviewerOptingDecision.OptingChoices.OPT_OUT
    UNDEFINED = RQCReviewerOptingDecision.OptingChoices.UNDEFINED

    review_form_view = 'do_review'
    review_form_template = 'review/review_form.html'
    opting_form_template = 'rqc_adapter/reviewer_opting_form.html'
    opting_from_post_view = 'rqc_adapter_set_reviewer_opting_status'

    post_opting_form_url = reverse(opting_from_post_view)

    def create_opt_in_form_data(self, assignment_id=None):
        data = {'status_selection_field': self.OPT_IN}
        if assignment_id:
            data['assignment_id'] = assignment_id
        return data

    def create_opt_out_form_data(self, assignment_id=None):
        data = {'status_selection_field': self.OPT_OUT}
        if assignment_id:
            data['assignment_id'] = assignment_id
        return data

    def post_opting_status(self, form_data, follow=False):
        return self.client.post(
            self.post_opting_form_url,
            data=form_data,
            follow=follow
        )

    def get_review_form(self, assignment_id=None):
        return self.client.get(
            reverse(self.review_form_view,
            args=[assignment_id]))

    def assert_opting_decision_exists(self):
        self.assertTrue(
            RQCReviewerOptingDecision.objects.filter(
                reviewer=self.reviewer_one,
                opting_status=self.OPT_IN
            ).exists()
        )
    def create_opting_status(self, journal_field, decision, opting_date=None):
        if opting_date:
            RQCReviewerOptingDecision.objects.create(reviewer=self.reviewer_one, journal=journal_field,
                                                     opting_status=decision,
                                                     opting_date=opting_date)
        else:
            # Created with current time as default
            RQCReviewerOptingDecision.objects.create(reviewer= self.reviewer_one,
                                                     journal=journal_field,
                                                     opting_status=decision)

    def assert_opting_form_template_used(self, response):
        self.assertTemplateUsed(response, self.opting_form_template)

    def setUp(self):
        super().setUp()
        RQCJournalAPICredentials.objects.create(journal= self.journal_one,
                                                rqc_journal_id = 1,
                                                api_key= 'test')

        self.create_session_with_reviewer()

        # Create second Review Assignment
        # Set-Up author
        self.author_two = self.create_author(self.journal_one, 'author_two')

        # Create Article
        self.article_two = self.create_article(self.journal_two, 'Article 2', self.author_two)

        self.review_assignment_two = helpers.create_review_assignment(
            journal=self.journal_two,
            article=self.article_two,
            reviewer=self.reviewer_one,
            editor= self.editor,
            due_date= timezone.now() + timedelta(weeks=2))

        # Create third Review Assignment in journal_one
        self.article_three = self.create_article(self.journal_one, 'Article 3', self.author)
        self.review_assignment_three = helpers.create_review_assignment(
            journal=self.journal_one,
            article=self.article_three,
            reviewer=self.reviewer_one,
            editor= self.editor,
            due_date= timezone.now() + timedelta(weeks=2)
        )

    def create_session(self):
        session = self.client.session
        session['journal'] = self.journal_one.id
        session['user'] = self.reviewer_one.id
        session.save()

    def create_session_with_reviewer(self):
        self.login_reviewer()
        self.create_session()

    def test_opting_status_set(self):
        """Test creation of opting status when form is submitted and redirection."""
        response = self.post_opting_status(form_data=self.create_opt_in_form_data())
        # Redirect after POST
        self.assertEqual(response.status_code, 302)
        # Created Opting status
        self.assert_opting_decision_exists()

    def test_opting_form_shown_if_no_opting_status_present(self):
        """Form is shown on the review form if no opting status is present."""
        # Open the review form
        response = self.get_review_form(assignment_id=self.review_assignment.id)
        self.assertTemplateUsed(response, self.review_form_template)
        self.assert_opting_form_template_used(response)

    def test_redirect_to_review_form(self, response=None):
        """Test redirection to review form."""
        response = self.get_review_form(assignment_id=self.review_assignment.id)
        self.assert_opting_decision_exists()
        form_data = self.create_opt_in_form_data(assignment_id=self.review_assignment.id)
        self.post_opting_status(form_data=form_data)

        # Created Opting status
        self.assert_opting_decision_exists()
        # Redirected to review_form with correct url
        self.assertTemplateUsed(response, self.review_form_template)
        final_url = response.request['PATH_INFO']
        expected_url = reverse(self.review_form_view, args=[self.review_assignment.id])
        self.assertEqual(final_url, expected_url)

    def test_opting_form_not_shown(self):
        """Form is not shown on the review form if the reviewer already has a valid opting status."""
        self.create_opting_status(self.journal_one, self.OPT_IN)
        response = self.get_review_form(assignment_id=self.review_assignment.id)
        self.assertTemplateNotUsed(response,self.opting_form_template)

    def test_opting_form_shown_invalid_opting_status(self):
        """Form is shown if the reviewer has an invalid (old) opting status."""
        self.create_opting_status(self.journal_one, self.OPT_IN, opting_date=timezone.now() - timedelta(weeks=200))
        response = self.get_review_form(assignment_id=self.review_assignment.id)
        self.assertTemplateUsed(response, self.opting_form_template)

    def test_opting_form_shown_in_second_journal(self):
        """Form is shown in second journal even if reviewer already
        has a valid opting status in another journal."""
        # Create OPT-In status in journal one
        self.create_opting_status(self.journal_one, self.OPT_IN)
        # Go to review assignment in journal two
        response = self.get_review_form(assignment_id=self.review_assignment_two.id)
        self.assertTemplateUsed(response, self.opting_form_template)

    def test_active_review_assignments_get_status_update(self):
        """Correctly updates RQCOptingStatusForReviewAssignment for active review assignments."""
        self.create_reviewer_opting_decision_for_ReviewAssignment(review_assignment=self.review_assignment,
                                                                  opting_status=self.UNDEFINED)
        self.get_review_form(assignment_id=self.review_assignment.id)
        self.post_opting_status(form_data=self.create_opt_in_form_data(assignment_id=self.review_assignment.id))
        self.assertTrue(RQCReviewerOptingDecisionForReviewAssignment.objects.filter(
            review_assignment=self.review_assignment,
            opting_status=self.OPT_IN).exists())

    def test_inactive_review_assignments_do_not_status_update(self):
        """Does not update RQCOptingStatusForReviewAssignment for declined review assignments."""
        review_assignment_opting_status = self.create_reviewer_opting_decision_for_ReviewAssignment(self.review_assignment_three,
                                                                  self.UNDEFINED)
        review_assignment_opting_status.review_assignment.date_declined = timezone.now()
        self.post_opting_status(form_data=self.create_opt_in_form_data(assignment_id=self.review_assignment.id))
        self.assertTrue(RQCReviewerOptingDecisionForReviewAssignment.objects.filter(
            review_assignment=self.review_assignment_three,
            opting_status=self.UNDEFINED).exists())

    def test_opting_form_redirects_with_access_code(self):
        """Tests that redirection works when an access code is given."""
        pass

    def test_non_reviewers_can_not_set_opting_status(self):
        """Tests if non-reviewers can not set opting status."""
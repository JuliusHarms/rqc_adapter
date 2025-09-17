"""
© Julius Harms, Freie Universität Berlin 2025

This file defines a basic test case that sets up data and provides utility
methods for the other test classes.
"""

from datetime import datetime, timezone, timedelta
from mock import Mock
import os

from django.http import HttpRequest
from django.test import TestCase, override_settings
from django.contrib.contenttypes.models import ContentType

import submission.models
from plugins.rqc_adapter.models import RQCReviewerOptingDecisionForReviewAssignment, RQCReviewerOptingDecision
from press.models import Press
from utils.testing import helpers

# Django-Debug-Toolbar gets disabled to avoid it wrapping html responses with its own templates
@override_settings(ROOT_URLCONF="plugins.rqc_adapter.tests.test_urls")
@override_settings(
    DEBUG=False,
    DEBUG_TOOLBAR_CONFIG={
        'SHOW_TOOLBAR_CALLBACK': lambda request: False,
    }
)
class RQCAdapterBaseTestCase(TestCase):

    @classmethod
    def create_author(cls, journal, username):
        author = helpers.create_user(
            username,
            ['author'],
            journal= journal,
        )
        author.is_active = True
        author.save()
        return author

    @classmethod
    def create_article(cls, journal, title, author, stage=submission.models.STAGE_UNDER_REVIEW):
        article = helpers.create_article(
            journal=journal,
        )
        article.title = title
        article.authors.add(author)
        article.stage = stage
        article.save()
        return article

    @classmethod
    def create_reviewer_opting_decision_for_ReviewAssignment(cls, review_assignment, opting_status=RQCReviewerOptingDecision.OptingChoices.OPT_IN):
        opting_for_review_assignment = RQCReviewerOptingDecisionForReviewAssignment.objects.create(review_assignment=review_assignment, opting_status=opting_status)
        return opting_for_review_assignment

    @classmethod
    def setUpTestData(cls):
        """
        Setup the test environment.
        :return: None
        """
        roles_to_setup = [
            "reviewer",
            "editor",
        ]
        cls.press = helpers.create_press()
        cls.journal_one, cls.journal_two = helpers.create_journals()
        helpers.create_roles(roles_to_setup)

        cls.editor = helpers.create_editor(cls.journal_one)
        cls.article_owner = helpers.create_regular_user()
        cls.bad_user = helpers.create_second_user(cls.journal_one)

        # Set-Up author
        cls.author = helpers.create_user(
            'author@rqc.initiative',
            ['author'],
            journal=cls.journal_one,
        )
        cls.author.is_active = True
        cls.author.save()
        cls.active_article = helpers.create_article(
            journal=cls.journal_one,
        )

        # Create Article
        cls.active_article.title = 'Active Article'
        cls.active_article.authors.add(cls.author)
        cls.active_article.stage = submission.models.STAGE_UNDER_REVIEW
        cls.active_article.save()

        # Create Reviewer 1
        cls.reviewer_one = helpers.create_peer_reviewer(cls.journal_one)
        cls.reviewer_one.is_active = True
        cls.reviewer_one.save()

        # Create Reviewer 2
        cls.reviewer_two = helpers.create_peer_reviewer(cls.journal_one)
        cls.reviewer_two.is_active = True
        cls.reviewer_two.save()

        # Create Review Assignment
        cls.review_assignment = helpers.create_review_assignment(
            journal=cls.journal_one,
            article=cls.active_article,
            reviewer=cls.reviewer_one,
            editor= cls.editor,
            due_date=datetime.now(timezone.utc) + timedelta(weeks=2))

        # Set-Up API credentials for live calls:
        cls.rqc_api_key = os.environ.get('RQC_API_KEY', None)
        cls.rqc_journal_id = os.environ.get('RQC_JOURNAL_ID', None)

    @staticmethod
    def mock_messages_add(level, message, extra_tags):
        pass

    @staticmethod
    def get_method(field):
        return None

    @staticmethod
    def prepare_request_with_user(user, journal, press=None):
        """
        Build a basic request dummy object with the journal set to journal
        and the user having editor permissions.
        :param user: the user to use
        :param journal: the journal to use
        :param press: the press to use
        :return: an object with user and journal properties
        """
        request = Mock(HttpRequest)
        request.user = user
        request.GET = Mock()
        request.GET.get = RQCAdapterBaseTestCase.get_method
        request.journal = journal
        request._messages = Mock()
        request._messages.add = RQCAdapterBaseTestCase.mock_messages_add
        request.path = '/a/fake/path/'
        request.path_info = '/a/fake/path/'
        request.press = press
        request.content_type = ContentType.objects.get_for_model(user)
        request.model_content_type = request.content_type

        request.site_type = ContentType.objects.get_for_model(journal)
        request.site = press or journal
        # if model:
        #    request.content_type = ContentType.objects.get_for_model(model)
        return request

    def login_editor(self):
        self.client.force_login(self.editor)

    def login_reviewer(self):
        self.client.force_login(self.reviewer_one)


data = {
    "interactive_user": "test@fu-berlin.de",
    "mhs_submissionpage": "https://mymhs.example.com/journal17/user29?submission=submission31",
    "title": "Rather Altogether Modestly Long-ish Submission Title 21",
    "external_uid": "5",
    "visible_uid": "5",
    "submitted": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    "author_set": [
        {
            "email": "author31@sm.wh",
            "firstname": "A.N.",
            "lastname": "Author",
            "orcid_id": "0000-0001-5592-0005",
            "order_number": 1
        },
        {
            "email": "other_author@sm.wh",
            "firstname": "Brubobolob",
            "lastname": "Authoress",
            "orcid_id": "0000-0001-5592-0006",
            "order_number": 3
        }
    ],
    "edassgmt_set": [
        {
            "email": "editor1@sm.wh",
            "firstname": "Keen",
            "lastname": "Editorus",
            "orcid_id": "0000-0001-5592-0003",
            "level": 1
        },
        {
            "email": "editor2@sm.wh",
            "firstname": "Keener",
            "lastname": "Editora",
            "orcid_id": "0000-0001-5592-0004",
            "level": 3
        },
        {
            "email": "editor3@sm.wh",
            "firstname": "Kim",
            "lastname": "Nguyen",
            "orcid_id": "0000-0001-5592-0007",
            "level": 3
        }
    ],
    "review_set": [
        {
            "visible_id": "1",
            "invited": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "agreed": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "expected": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "submitted": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "text": "This is the text of review 1.",
            "attachment_set": [],
            "is_html": False,
            "suggested_decision": "MINORREVISION",
            "reviewer": {
                "email": "reviewer1@sm.wh",
                "firstname": "J.",
                "lastname": "Reviewer 1",
                "orcid_id": "0000-0001-5592-0001"
            }
        },
        {
            "visible_id": "2",
            "invited": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "agreed": "",
            "expected": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "submitted": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "text": "This is the text of review 2.\nIt is multiple lines long, some of which are themselves a bit longer (like this one, for instance; at least somewhat -- truly long would be longer, of course)\n\nLine 4, the last one.",
            "is_html": False,
            "suggested_decision": "ACCEPT",
            "reviewer": {
                "email": "reviewer2@sm.wh",
                "firstname": "J.",
                "lastname": "Reviewer 2",
                "orcid_id": "0000-0001-5592-0002"
            },
            "attachment_set": []
        }
    ],
    "decision": "ACCEPT"
}

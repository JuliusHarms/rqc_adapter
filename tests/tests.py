from datetime import datetime, timezone
from unittest.mock import patch

from django.conf import settings
from django.http import HttpRequest, QueryDict
from django.test import TestCase, LiveServerTestCase, TransactionTestCase, override_settings
from django.urls import reverse
from mock import Mock

import os

from plugins.rqc_adapter.models import RQCJournalAPICredentials
from plugins.rqc_adapter.views import handle_journal_settings_update
from utils.testing import helpers


@override_settings(ROOT_URLCONF="plugins.rqc_adapter.tests.test_urls")
@override_settings(
    DEBUG=False,
    DEBUG_TOOLBAR_CONFIG={
        'SHOW_TOOLBAR_CALLBACK': lambda request: False,
    }
)
class TestRQCAdapter(TestCase):

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
        request.GET.get = TestRQCAdapter.get_method
        request.journal = journal
        request._messages = Mock()
        request._messages.add = TestRQCAdapter.mock_messages_add
        request.path = '/a/fake/path/'
        request.path_info = '/a/fake/path/'
        request.press = press
        return request


# Test explicit calls


# Test implicit calls


# Test delayed calls

# Test setting and deleting settings


    # 1. Call with valid Settings
    def test_setting_validation_case_valid(self):
        func = Mock()
        # Init Request
        if self.rqc_api_key is None or self.rqc_journal_id is None:
            print("No API key found. Cannot make API call integration tests.")
            return
        else:
            request = self.prepare_request_with_user(
                self.editor,
                self.journal_one,
            )
            post_data = QueryDict(mutable=True)
            post_data.update({
                'journal_id_field': self.rqc_journal_id,
                'journal_api_key_field': self.rqc_api_key,
            })
            request.method = 'POST'
            request.POST = post_data
            # Valid example data
            form_data = {
                'journal_id_field': self.rqc_journal_id,
                'journal_api_key_field': self.rqc_api_key,
            }
            #response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data)
            response = handle_journal_settings_update(request)
            print(f"Status code: {response.status_code}")
            # Credentials were created if the given data
            #context = response.context
            #print("Content (first 200 chars):", response.content[:200])
            #print("Templates used:", [t.name for t in response.templates])
            #print(response.status_code)
            self.assertTrue(RQCJournalAPICredentials.objects.filter(journal=self.journal_one,rqc_journal_id=self.rqc_journal_id, api_key = self.rqc_api_key).exists())

    def test_setting_validation_case_valid_settings_no_follow_redirect(self):
        if self.rqc_api_key is None or self.rqc_journal_id is None:
            print("No API key found. Cannot make API call integration tests.")
            return
        else:
            post_data = QueryDict(mutable=True)
            post_data.update({
                'journal_id_field': self.rqc_journal_id,
                'journal_api_key_field': self.rqc_api_key,
            })
            # Valid example data
            form_data = {
                'journal_id_field': self.rqc_journal_id,
                'journal_api_key_field': self.rqc_api_key,
            }
            response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data)
            self.assertEqual(response.status_code, 302)

    def test_setting_validation_case_valid_settings_follow_redirect(self):
        if self.rqc_api_key is None or self.rqc_journal_id is None:
            print("No API key found. Cannot make API call integration tests.")
            return
        else:
            post_data = QueryDict(mutable=True)
            post_data.update({
                'journal_id_field': self.rqc_journal_id,
                'journal_api_key_field': self.rqc_api_key,
            })
            # Valid example data
            form_data = {
                'journal_id_field': self.rqc_journal_id,
                'journal_api_key_field': self.rqc_api_key,
            }
            response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data, follow=True)
            # Database objects were created
            self.assertTrue(RQCJournalAPICredentials.objects.filter(journal=self.journal_one,rqc_journal_id=self.rqc_journal_id, api_key = self.rqc_api_key).exists())
            # Manager template is given in response after redirect
            self.assertTemplateUsed(response, 'rqc_adapter/manager.html')






# 2. Make invalid calls
    # Formatting errors -> non alphanumeric, non number for

    # Redirect Test

    # Response Template Test

    # Error Labels + Messages Tests

    # Test Roles

# RQC Call Data:
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

        helpers.create_press()
        cls.journal_one, cls.journal_two = helpers.create_journals()
        helpers.create_roles(roles_to_setup)

        cls.editor = helpers.create_editor(cls.journal_one)
        cls.article_owner = helpers.create_regular_user()
        cls.bad_user = helpers.create_second_user(cls.journal_one)
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
        cls.active_article.title = 'Active Article'
        cls.active_article.save()
        cls.active_article.authors.add(cls.author)

        # Set-Up API credentials for live calls:
        cls.rqc_api_key = os.environ.get('RQC_API_KEY', None)
        cls.rqc_journal_id = os.environ.get('RQC_JOURNAL_ID', None)

        # Create session with editor logged in
        cls.client.force_login(cls.editor)
        session = cls.client.session
        session['journal'] = cls.journal_one.id
        session['user'] = cls.editor.id
        session.save()

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
                "attachment_set":[]
            }
        ],
        "decision": "ACCEPT"
    }
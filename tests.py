from django.http import HttpRequest
from django.test import TestCase
from mock import Mock

class TestRQCAdapter(TestCase):

    @staticmethod
    def mock_messages_add(level, message, extra_tags):
        pass

    @staticmethod
    def get_method(field):
        return None

    def prepare_request_with_user(user, journal, press=None):
        """
        Build a basic request dummy object with the journal set to journal
        and the user having editor permissions.
        :param user: the user to use
        :param journal: the journal to use
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


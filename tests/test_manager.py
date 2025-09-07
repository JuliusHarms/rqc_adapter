"""
© Julius Harms, Freie Universität Berlin 2025

This file contains tests for the manager template and the associated
form uses to set the journals api credentials.
"""
import os
from unittest import skipUnless

from django.http import QueryDict
from django.urls import reverse

from plugins.rqc_adapter.models import RQCJournalAPICredentials
from plugins.rqc_adapter.tests.base_test import RQCAdapterBaseTestCase
from plugins.rqc_adapter.views import handle_journal_settings_update

has_api_credentials_env = os.getenv("RQC_API_KEY") and os.getenv("RQC_JOURNAL_ID")

@skipUnless(has_api_credentials_env, "No API key found. Cannot make API call integration tests.")
class TestManager(RQCAdapterBaseTestCase):

    def create_session(self):
        session = self.client.session
        session['journal'] = self.journal_one.id
        session['user'] = self.editor.id
        session.save()

    def create_session_with_editor(self):
        self.login_editor()
        self.create_session()

    def create_mock_post_request(self, journal_id, api_key):
        request = self.prepare_request_with_user(self.editor, self.journal_one, self.press)
        post_data = QueryDict(mutable=True)
        post_data.update({
            'journal_id_field': journal_id,
            'journal_api_key_field': api_key,
        })
        request.method = 'POST'
        request.POST = post_data
        return request

# Unit-Tests

    def test_valid_credentials_saved_to_database(self):
        """Valid submission creates database record"""
        # Create mock request
        request = self.create_mock_post_request(self.rqc_journal_id, self.rqc_api_key)

        response = handle_journal_settings_update(request)

        # Status Code to redirect
        self.assertEqual(response.status_code, 302)
        # Check that credentials were created
        self.assertTrue(
            RQCJournalAPICredentials.objects.filter(
                journal=self.journal_one,
                rqc_journal_id=self.rqc_journal_id,
                api_key=self.rqc_api_key
            ).exists()
        )

    def test_existing_credentials_updated_not_duplicated(self):
        """Resubmitting updates existing record"""
        self.create_session_with_editor()
        RQCJournalAPICredentials.objects.create(journal=self.journal_one, rqc_journal_id=1, api_key='test')
        form_data = {
            'journal_id_field': self.rqc_journal_id,
            'journal_api_key_field': self.rqc_api_key,
        }
        response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data)
        self.assertTrue(
            RQCJournalAPICredentials.objects.filter(
                journal=self.journal_one,
                rqc_journal_id=self.rqc_journal_id,
                api_key=self.rqc_api_key
            ).exists()
        )
        self.assertEqual(RQCJournalAPICredentials.objects.filter(journal=self.journal_one).count(), 1)

    def test_empty_fields_rejected(self):
        """Test that empty required fields show errors"""
        self.create_session_with_editor()
        form_data = {
        }
        response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data)
        form = response.context['form']
        self.assertFormError(form, 'journal_id_field', 'This field is required.')
        self.assertFormError(form, 'journal_api_key_field', 'This field is required.')

    def test_invalid_api_key_format_rejected(self):
        """Malformed API keys are rejected"""
        # Create mock request with invalid journal_api_key
        self.create_session_with_editor()
        form_data = {
            'journal_id_field': self.rqc_journal_id,
            'journal_api_key_field': "@test?",
        }
        response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data)
        self.assertFormError(response.context['form'], 'journal_api_key_field', 'The API key must only contain alphanumeric characters.')

    def test_invalid_journal_id_format_rejected(self):
        """Invalid journal IDs are rejected"""
        # Create mock request with invalid journal_id
        self.create_session_with_editor()
        form_data = {
            'journal_id_field': "test",
            'journal_api_key_field': self.rqc_api_key,
        }
        response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data)
        self.assertFormError(response.context['form'], 'journal_id_field', 'Journal ID must be a number')

# Integration Tests
    def test_api_credentials_validated_against_rqc_service(self):
        """Form validates credentials with actual RQC API"""

    def test_manager_contains_form(self):
        pass

    def test_redirect_after_valid_post(self):
        """
        Tests 'happy' path where editor deposits valid data a database record is created and user is redirected.
        Note that this requires rqc_api_key and rqc_journal_id to be present as environment variables.
        See also setUpData in base_test.
        """
        self.create_session_with_editor()
        form_data = {
            'journal_id_field': self.rqc_journal_id,
            'journal_api_key_field': self.rqc_api_key,
        }
        response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data)
        # Redirect after post
        self.assertEqual(response.status_code, 302)

    def test_redirect_to_manager_after_valid_post(self):
        """
        Tests 'happy' path where editor deposits valid data a database record is created and user is redirected to manager page.
        Note that this requires rqc_api_key and rqc_journal_id to be present as environment variables.
        See also setUpData in base_test.
        """
        # Valid example data
        self.create_session_with_editor()
        form_data = {
            'journal_id_field': self.rqc_journal_id,
            'journal_api_key_field': self.rqc_api_key,
        }
        response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data, follow=True)
        # Database objects were created
        self.assertTrue(RQCJournalAPICredentials.objects.filter(journal=self.journal_one,rqc_journal_id=self.rqc_journal_id, api_key = self.rqc_api_key).exists())
        # Manager template is given in response after redirect
        self.assertTemplateUsed(response, 'rqc_adapter/manager.html')

    def test_anonymous_user_redirected_to_login(self):
        """
        Test whether anonymous user is redirected to login page.
        """
        # Valid example data
        form_data = {
            'journal_id_field': self.rqc_journal_id,
            'journal_api_key_field': self.rqc_api_key,
        }
        response = self.client.post(reverse('rqc_adapter_handle_journal_settings_update'), data=form_data, follow=True)
        # Admin login template is given in response
        self.assertTemplateUsed(response, 'rqc_adapter/manager.html')

    def test_non_editor_non_journal_manager_can_not_edit(self):
        pass

    def test_csrf_protection_enabled(self):
        pass

    def test_concurrent_submissions_handled(self):
        """Multiple editors submitting simultaneously"""
        pass

    def test_successful_submission_shows_success_message(self):
        """User gets feedback on successful submission"""
        pass

    def test_form_errors_displayed_clearly(self):
        """Validation errors are shown next to relevant fields"""
        pass

    def test_form_retains_data_after_validation_error(self):
        """User doesn't lose their input if validation fails"""
        pass

# 2. Make invalid calls
    # Formatting errors -> non alphanumeric, non number for

    # Response Template Test

    # Error Labels + Messages Tests

    # Test Roles
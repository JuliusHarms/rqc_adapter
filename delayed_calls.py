import os
from django.utils.timezone import now
from django.core.management.base import BaseCommand

from plugins.rqc_adapter.models import RQCDelayedCall
from plugins.rqc_adapter.plugin_settings import get_journal_id, get_journal_api_key
from plugins.rqc_adapter.rqc_calls import fetch_post_data, call_rqc_api, call_mhs_submission

#TODO delayed mhsapicheck calls doesnt make sense right?

try:
    import crontab
except (ImportError, ModuleNotFoundError):
    crontab = None

# todo give credit
class Command(BaseCommand):
    """
    Retries failed RQC Calls.
    """

    help = "Retries failed RQC Calls."

    def add_arguments(self, parser):
        parser.add_argument('--action', default="")
# TODO multiple calls for the same article waht if the info is old?
# add logs i guess
    def handle(self, *args, **options):
        """
        Retries failed RQC calls.
        :param args: None
        :param options: None
        :return: None
        """
        queue = RQCDelayedCall.objects.filter(retry_time__gte=now()).order_by('-retry_time')
        for call in queue:
            if call.is_valid:
                user = call.user
                article = call.article
                article_id = call.article.pk
                journal = call.article.journal
                post_data = fetch_post_data(user ,article, article_id, journal, interactive= False)
                response = call_mhs_submission(get_journal_id(journal), get_journal_api_key(journal), article_id, post_data)
                call.tries = call.tries + 1
                #TODO handle response
                if not response['success']:
                    match response['http_status_code']:
                        case '400':
                            call.delete()
                        case '403':
                            print(f"error: {response['http_status_code']} {response['message']}") #TODO temp  #TODO temp
                        case '404':
                            print(f"error: {response['http_status_code']} {response['message']}") #TODO temp
                        case _:  # TODO what other cases can occur? - change message based on response code
                            print(f"error: {response['http_status_code']} {response['message']}")
                else:
                    call.delete()
            else:
                call.delete()
            sleep(1) #TODO sleep between calls?


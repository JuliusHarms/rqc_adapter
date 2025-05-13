import os

from django.core.management.base import BaseCommand
from django.conf import settings

try:
    import crontab
except (ImportError, ModuleNotFoundError):
    crontab = None

# todo give credit
class Command(BaseCommand):
    """
    Installs the cron task for retrying failed RQC calls.
    """

    help = "Installs the cron task for retrying failed RQC calls."

    def add_arguments(self, parser):
        parser.add_argument('--action', default="")

    def handle(self, *args, **options):
        """
        Installs Cron
        :param args: None
        :param options: None
        :return: None
        """
        if not os.path.isfile('/usr/bin/crontab'):
            return

        if not crontab:
            print("WARNING: crontab module is not installed, skipping crontab config.")
            return

        tab = crontab.CronTab(user=True) #load current user as cron user
        virtualenv = os.environ.get('VIRTUAL_ENV', None)
        django_command = "{0}/manage.py {1}".format(settings.BASE_DIR, 'make_delayed_rqc_calls')
        if virtualenv:
            command = '%s/bin/python3 %s' % (virtualenv, django_command)
        else:
            command = '%s' % django_command
        cron_job = tab.new(command)
        #todo shift cron time? or let users set the cron job time?
        cron_job.day.every(1)
        tab.write()

"""
© Julius Harms, Freie Universität Berlin 2025
"""

import os

from django.core.management.base import BaseCommand
from django.conf import settings

try:
    import crontab
except (ImportError, ModuleNotFoundError):
    crontab = None

# todo give credit
# logging?
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
            self.stdout.write(
                self.style.WARNING('WARNING: /usr/bin/crontab not found. Could not install RQC cronjob.')
            )
            return

        if not crontab:
            self.stdout.write(
                self.style.WARNING('WARNING: crontab python module is not installed. Could not install RQC cronjob.')
            )
            return

        tab = crontab.CronTab(user=True) #load current user as cron user
        virtualenv = os.environ.get('VIRTUAL_ENV', None)
        django_command = "{0}/manage.py {1}".format(settings.BASE_DIR, 'rqc_make_delayed_calls')
        if virtualenv:
            command = '%s/bin/python3 %s' % (virtualenv, django_command)
        else:
            command = '%s' % django_command
        cron_job = tab.new(command)
        #todo shift cron time? or let users set the cron job time?
        cron_job.setall('0 8 * * *')
        tab.write()
        self.stdout.write(
            self.style.SUCCESS('Successfully installed RQC cronjob.')
        )
        self.stdout.flush()

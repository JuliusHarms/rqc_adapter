from utils import plugins
from utils.logger import get_logger
from utils.install import update_settings
from journal.models import Journal
from core.models import Setting, SettingValue
from events import logic as events_logic
from events.logic import Events

from plugins.rqc_adapter.config import VERSION
from plugins.rqc_adapter.utils import generate_random_salt

PLUGIN_NAME = 'RQC Adapter Plugin'
DISPLAY_NAME = 'RQC Adapter'
DESCRIPTION = 'This plugin connects Janeway to the RQC API, allowing it to report review data for grading and inclusion in reviewers receipts.'
AUTHOR = 'Julius Harms'
SHORT_NAME = 'rqc_adapter'
MANAGER_URL = 'rqc_adapter_manager'
JANEWAY_VERSION = "1.3.8"

logger = get_logger(__name__)

class Rqc_adapterPlugin(plugins.Plugin):
    plugin_name = PLUGIN_NAME
    display_name = DISPLAY_NAME
    description = DESCRIPTION
    author = AUTHOR
    short_name = SHORT_NAME
    manager_url = MANAGER_URL

    version = VERSION
    janeway_version = JANEWAY_VERSION

    # TODO workflow settings correct?
    is_workflow_plugin = False

def install():
    Rqc_adapterPlugin.install()
    update_settings(
        file_path='plugins/rqc_adapter/install/settings.json'
    )
    journals = Journal.objects.all()
    setting = Setting.objects.get(name='rqc_journal_salt')
    for journal in journals:
        set_journal_salt(journal)


def hook_registry():
    Rqc_adapterPlugin.hook_registry()
    return {
        'in_review_editor_actions': {
                    'module': 'plugins.rqc_adapter.hooks',
                    'function': 'render_rqc_grading_actions',
        },
        'review_form_guidelines': {
            'module': 'plugins.rqc_adapter.hooks',
            'function': 'render_reviewer_opting_form',
        }
    }


# TODO test out what happens if you request revisions on an article
def register_for_events():
    from plugins.rqc_adapter.rqc_calls import implicit_call_mhs_submission
    # The RQC API requires an implicit call when the editorial decision is changed
    events_logic.Events.register_for_event(
        Events.ON_ARTICLE_ACCEPTED,
        implicit_call_mhs_submission,
    )
    # todo -> set editorial decision to ""?
    events_logic.Events.register_for_event(
        Events.ON_ARTICLE_DECLINED,
        implicit_call_mhs_submission,
    )

    events_logic.Events.register_for_event(
        Events.ON_ARTICLE_UNDECLINED,
        implicit_call_mhs_submission,
    )

    events_logic.Events.register_for_event(
        Events.ON_REVISIONS_REQUESTED,
        implicit_call_mhs_submission,
    )


def set_journal_salt(journal):
    """
    Sets the journals salt to a newly random generated salt string
    TODO: user could change the value through database admin interface -> add warning not to do that
    :param journal: Journal object
    :return: Salt string
    """
    salt = generate_random_salt()
    setting = Setting.objects.filter(name='rqc_journal_salt')
    setting_value = SettingValue(setting=setting, value=salt, journal=journal)
    setting_value.save()
    logger.info('Set rqc_journal salt to: %s for journal: %s', salt,
                journal.name)  # From a security standpoint is this ok? Test later.
    return salt

def has_salt(journal):
    """
    :param journal: Journal object
    :return: Boolean
    """
    return SettingValue.objects.filter(setting__name='rqc_journal_salt', journal=journal).exists()

def get_salt(journal):
    """ Gets the salt string for the journal
    :param journal: Journal object
    :return: Salt string
    """
    return SettingValue.objects.get(setting__name='rqc_journal_salt', journal=journal).value

def set_journal_id(journal_id: int, journal: Journal) -> dict:
    """
    Set the journal id.
    :param journal_id: The journal ID to set
    :param journal: Journal object
    #TODO handle setting doesnt exists?
    :return: A dictionary with status and message
    :raises: Setting.DoesNotExist: If the setting doesn't exist
    """
    if not journal_id or not isinstance(journal_id, int):
        return {"status": "error", "message": "Invalid journal ID"}

    try:
        journal_id_setting = Setting.objects.get(name='rqc_journal_id')
        journal_id_setting_value = SettingValue(setting= journal_id_setting, value= journal_id, journal=journal)
        journal_id_setting_value.save()
        return {"status": "success", "message": "Journal Id updated successfully"}
    except Setting.DoesNotExist:
        return {"status": "error", "message": "Journal Id setting not found"}
    except Exception as e:
        return {"status": "error", "message": f"Error updating journal Id: {str(e)}"}

def has_journal_id(journal: Journal) -> bool:
    """ Checks if the journal has a journal ID
    :param journal: Journal object
    :return: Boolean
    """
    journal_id_setting = Setting.objects.get(name='rqc_journal_id')
    return SettingValue.objects.filter(setting=journal_id_setting, journal=journal).exists()

def get_journal_id(journal: Journal) -> str:
    """ Returns the journal ID
    :param journal: Journal object
    :return: journal ID
    TODO - errors
    """
    journal_id_setting = Setting.objects.get(name='rqc_journal_id')
    return SettingValue.objects.get(setting=journal_id_setting, journal=journal).value

def set_journal_api_key(journal_api_key: str, journal: Journal) -> dict:
    """
    Set the journal API key.
    :param journal_api_key: The API key to set
    :param journal: Journal object
    :return: A dictionary with status and message
    :raises: Setting.DoesNotExist: If the setting doesn't exist'
    """
    if not journal_api_key or not isinstance(journal_api_key, str):
        return {"status": "error", "message": "Invalid journal API key"}
    try:
        journal_api_key_setting = Setting.objects.get(name='rqc_journal_api_key')
        journal_api_key_setting_value = SettingValue(setting=journal_api_key_setting, value= journal_api_key, journal=journal)
        journal_api_key_setting_value.save()
        return {"status": "success", "message": "Journal API key updated successfully"}
    except Setting.DoesNotExist:
        return {"status": "error", "message": "Journal API key setting not found"}
    except Exception as e:
        return {"status": "error", "message": f"Error updating journal API key: {str(e)}"}


def get_journal_api_key(journal: Journal) -> str:
    """ Returns the journals API key
    :param journal: Journal object
    :return:  API key string
    TODO errors
    """
    journal_api_key_setting = Setting.objects.get(name='rqc_journal_api_key')
    return SettingValue.objects.get(setting=journal_api_key_setting, journal=journal).value

def has_journal_api_key(journal: Journal) -> bool:
    """ Checks if the journal API key exists
    :param journal: Journal object
    :return: Boolean
    """
    journal_api_key_setting = Setting.objects.get(name='rqc_journal_api_key')
    return SettingValue.objects.filter(setting=journal_api_key_setting, journal=journal).exists()
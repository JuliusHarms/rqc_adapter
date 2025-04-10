from plugins.rqc_adapter.utils import generate_random_salt
from utils import plugins
from utils.install import update_settings
from journal.models import Journal
from core.models import Setting, SettingValue


PLUGIN_NAME = 'RQC Adapter Plugin'
DISPLAY_NAME = 'RQC Adapter'
DESCRIPTION = 'This plugin connects Janeway to the RQC API, allowing it to report review data for grading and inclusion in reviewers receipts.'
AUTHOR = 'Julius Harms'
VERSION = '0.1'
SHORT_NAME = 'rqc_adapter'
MANAGER_URL = 'rqc_adapter_manager'
JANEWAY_VERSION = "1.3.8"

# Workflow Settings
IS_WORKFLOW_PLUGIN = True
JUMP_URL = 'rqc_grade_article_reviews'
HANDSHAKE_URL = 'rqc_adapter_rqc_grading_articles'
ARTICLE_PK_IN_HANDSHAKE_URL = True
STAGE = 'rqc_adapter_plugin'
KANBAN_CARD = ''
DASHBOARD_TEMPLATE = 'rqc_adapter/dashboard.html'



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
    is_workflow_plugin = True
    handshake_url = HANDSHAKE_URL
    article_pk_in_handshake_url = ARTICLE_PK_IN_HANDSHAKE_URL
    


def install():
    Rqc_adapterPlugin.install()
    update_settings(
        file_path='plugins/rqc_adapter/install/settings.json'
    )
    # Generate a salt value for each journal
    # TODO what if a new journal is created -> create a salt later when needed
    journals = Journal.objects.all()
    setting = Setting.objects.get(name='rqc_journal_salt')
    for journal in journals:
        salt = generate_random_salt()
        setting_value = SettingValue(setting=setting, value=salt, journal=journal)
        setting_value.save()



def hook_registry():
    Rqc_adapterPlugin.hook_registry()
    return {
        'core_article_tasks': {'module: plugins.rqc_adapter.hooks', 'function: render_reviewer_opting_form'},
    }


# TODO register for review_complete, article_declined, article accepted, revisions requested
# TODO test out what happens if you request revisions on an article
def register_for_events():
    pass


def set_journal_salt(journal):
    """
    Sets the journals salt to a newly random generated salt string
    TODO: user could change the value through database admin interface -> add warning not to do that
    param: journal: Journal object
    return: salt string
    """
    salt = generate_random_salt()
    setting = Setting.objects.filter(name='rqc_journal_salt')
    setting_value = SettingValue(setting=setting, value=salt, journal=journal)
    setting_value.save()
    return salt

def has_salt(journal):
    """
    param: journal: Journal object
    return: boolean
    """
    return SettingValue.objects.filter(setting='rqc_journal_salt', journal=journal).exists()


def set_journal_id(journal_id: str, journal: Journal) -> dict:
    """
    Set the journal id.

    :param
        journal_id: The journal ID to set
        journal: Journal object
    :returns
        A dictionary with status and message
    :raises
        Setting.DoesNotExist: If the setting doesn't exist
    """
    if not journal_id or not isinstance(journal_id, str):
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

def get_journal_id(journal: Journal) -> str:
    """
    TODO - errors
    """
    return SettingValue.objects.get(setting='rqc_journal_id', journal=journal).value

def set_journal_api_key(journal_api_key: str, journal: Journal) -> dict:
    """
    Set the journal API key.
    :param
        journal_api_key: The API key to set
        journal: Journal object
    :return
        A dictionary with status and message
    :raises
        Setting.DoesNotExist: If the setting doesn't exist'
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
    """
    TODO errors
    """
    return SettingValue.objects.get(name='rqc_journal_api_key', journal=journal).value
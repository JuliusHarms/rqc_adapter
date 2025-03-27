from utils import plugins
from utils.install import update_settings

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
JUMP_URL = 'rqc_article'
HANDSHAKE_URL = 'rqc_adapter_grading_articles'
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

    # TBD workflow settings correct?
    is_workflow_plugin = True
    handshake_url = HANDSHAKE_URL
    article_pk_in_handshake_url = ARTICLE_PK_IN_HANDSHAKE_URL
    


def install():
    Rqc_adapterPlugin.install()
    update_settings(
        file_path='plugins/rqc_adapter/install/settings.json'
    )


def hook_registry():
    # Rqc_adapterPlugin.hook_registry()
    return {
    #     'nav_block': {'module: plugins.rqc_adapter.hooks', 'function: render_reviewer_opting_form'},
    }



def register_for_events():
    pass

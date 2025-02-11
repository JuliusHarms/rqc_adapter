from utils import plugins

PLUGIN_NAME = 'RQC Adapter Plugin'
DISPLAY_NAME = 'RQC Adapter'
DESCRIPTION = 'This plugin connects Janeway to the RQC API, allowing it to report review data for grading and inclusion in reviewers receipts.'
AUTHOR = 'Julius Harms'
VERSION = '0.1'
SHORT_NAME = 'rqc_adapter'
MANAGER_URL = 'rqc_adapter_manager'
JANEWAY_VERSION = "1.3.8"



class Rqc_adapterPlugin(plugins.Plugin):
    plugin_name = PLUGIN_NAME
    display_name = DISPLAY_NAME
    description = DESCRIPTION
    author = AUTHOR
    short_name = SHORT_NAME
    manager_url = MANAGER_URL

    version = VERSION
    janeway_version = JANEWAY_VERSION
    


def install():
    Rqc_adapterPlugin.install()


def hook_registry():
    Rqc_adapterPlugin.hook_registry()


def register_for_events():
    pass

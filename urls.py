#from django.conf.urls import url
from plugins.rqc_adapter import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^manager/$', views.manager, name='rqc_adapter_manager'),
    re_path(r'^manager/handle_journal_settings_update$', views.handle_journal_id_settings_update, name='rqc_adapter_handle_journal_settings_update'),
]

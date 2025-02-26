#from django.conf.urls import url
from plugins.rqc_adapter import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^manager/$', views.manager, name='rqc_adapter_manager'),
    re_path(r'^manager/set_journal_id$', views.set_journal_id, name='set_journal_id'),
    re_path(r'^manager/$', views.set_journal_api_key, name='rqc_adapter_set_journal_api_key'),
    #re_path(r'^manager/test_request/$', views.test_request, name='test_request'),
    #re_path(r'^manager/test_post/$', views.test_post, name='test_post')
]

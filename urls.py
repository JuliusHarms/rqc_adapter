#from django.conf.urls import url
from plugins.rqc_adapter import views
from django.urls import re_path

urlpatterns = [
    re_path(r'^manager/$', views.manager, name='rqc_adapter_manager'),
    re_path(r'^manager/handle_journal_settings_update$', views.handle_journal_id_settings_update, name='rqc_adapter_handle_journal_settings_update'),
    re_path(r'^$', views.rqc_grading_articles, name='rqc_adapter_rqc_grading_articles'),
    re_path(r'^article/(?P<article_id>\d+)/$', views.rqc_grade_article_reviews, name='rqc_adapter_rqc_grade_article_reviews'),
    re_path(r'^articles/(?P<article_id>\d+)/submit$', views.submit_article_for_grading, name='rqc_adapter_submit_article_for_grading'),
]

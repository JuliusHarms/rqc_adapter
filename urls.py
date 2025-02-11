from django.conf.urls import url

from plugins.rqc_adapter import views


urlpatterns = [
    url(r'^manager/$', views.manager, name='rqc_adapter_manager'),
]

from django.http import JsonResponse
from django.shortcuts import render

import utils.setting_handler
from core.models import SettingValue
from plugins.rqc_adapter import forms
from django.contrib import messages
from django.shortcuts import render, redirect #!TEST
import requests
from datetime import datetime, timezone
import logging
from utils import migration_utils
from core.models import Setting, SettingValue


def manager(request):
    form = forms.DummyManagerForm()
    template = 'rqc_adapter/manager.html'
    context = {
        'form': form,
    }
    return render(request, template, context)

def set_journal_id(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    else:
        journal_id_setting = SettingValue.objects.get(setting__name='rqc_journal_id')
        journal_id_setting.value = request.data.get('journal_id')
        journal_id_setting.save()
    return redirect('rqc_adapter_manager')

def set_journal_api_key(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    else:
        journal_api_key_setting = SettingValue.objects.get(setting__name='rqc_journal_api_key')
        journal_api_key_setting.value = request.data.get('api_key')
        journal_api_key_setting.save()
    return redirect('rqc_adapter_manager')
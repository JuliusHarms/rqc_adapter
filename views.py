from django.http import JsonResponse
from django.shortcuts import render, redirect

from core.models import SettingValue
from plugins.rqc_adapter import forms
from plugins.rqc_adapter.utils import set_journal_id, set_journal_api_key


def manager(request):
    template = 'rqc_adapter/manager.html'
    context = {
        'form': form,
    }
    return render(request, template, context)

def handle_journal_id_settings_update(request):
    if request.method == 'POST':
        form = forms.RqcSettingsForm(request.POST)
        if form.is_valid():
            journal_id = request.data.get('journal_id')
            set_journal_id(journal_id)
            journal_api_key = request.data.get('api_key')
            set_journal_api_key(journal_api_key)
        return redirect('rqc_adapter_manager')
    else:
        journal_id = SettingValue.objects.get(setting__name='rqc_journal_id')
        journal_api_key = SettingValue.objects.get(setting__name='rqc_journal_api_key')
        form = forms.RqcSettingsForm(initial={'journal_id_field': journal_id, 'journal_api_key_field': journal_api_key})
        return render(request,"rqc_adapter/manager.html",{'form':form})
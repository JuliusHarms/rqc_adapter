from django.http import JsonResponse
from django.shortcuts import render, redirect

from plugins.rqc_adapter import forms
from plugins.rqc_adapter.utils import set_journal_id, set_journal_api_key


def manager(request):
    form = forms.DummyManagerForm()
    template = 'rqc_adapter/manager.html'
    context = {
        'form': form,
    }
    return render(request, template, context)

def handle_journal_id_settings_update(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    else:
        # validate keys beforehand
        journal_id = request.data.get('journal_id')
        set_journal_id(journal_id)
        journal_api_key = request.data.get('api_key')
        set_journal_api_key(journal_api_key)
    return redirect('rqc_adapter_manager')
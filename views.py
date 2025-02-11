from django.shortcuts import render

from plugins.rqc_adapter import forms


def manager(request):
    form = forms.DummyManagerForm()

    template = 'rqc_adapter/manager.html'
    context = {
        'form': form,
    }

    return render(request, template, context)

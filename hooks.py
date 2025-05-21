from django.template.loader import render_to_string


def render_reviewer_opting_form(context):
    request = context['request']
    article = context['article']
    return  render_to_string('rqc_adapter/reviewer_opting_form.html', context={'article': article})

def render_rqc_grading_task(context):
    request = context['request']
    string = render_to_string('rqc_adapter/grading_task.html', context={})
    print(string)
    return string
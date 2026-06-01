from django import template
from django.utils.http import urlencode

register = template.Library()

STATUS_ICONS = {
    'open': 'fa-regular fa-circle',
    'in_progress': 'fa-regular fa-clock',
    'completed': 'fa-regular fa-circle-check',
    'failed': 'fa-regular fa-circle-xmark',
}

PRIORITY_ICONS = {
    'High': 'fa-arrow-up',
    'Medium': 'fa-arrow-right',
    'Low': 'fa-arrow-down',
    'Высокий': 'fa-arrow-up',
    'Средний': 'fa-arrow-right',
    'Низкий': 'fa-arrow-down',
}

TYPE_ICONS = {
    'Front': 'fa-code',
    'Back': 'fa-server',
    'Design': 'fa-pen-ruler',
    'DB': 'fa-database',
    'BD': 'fa-briefcase',
    'Backlog': 'fa-list',
    'Canceled': 'fa-ban',
}


@register.filter
def status_icon(status):
    return STATUS_ICONS.get(status, 'fa-regular fa-circle')


@register.filter
def priority_icon(priority):
    return PRIORITY_ICONS.get(priority, 'fa-arrow-right')


@register.filter
def task_type_icon(task_type):
    return TYPE_ICONS.get(task_type, 'fa-tag')


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return urlencode(query, doseq=True)

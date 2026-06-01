from collections import Counter

from django.db import connection
from django.db.models import Q

from .models import Task

VALID_TASK_TYPE_CODES = {code for code, _ in Task.TYPE_CHOICES}
TYPE_LABELS = dict(Task.TYPE_CHOICES)


def normalize_type_codes(codes):
    return [code for code in codes if code in VALID_TASK_TYPE_CODES]


def _type_match_q(type_code):
    if connection.vendor == 'sqlite':
        return Q(types__icontains=f'"{type_code}"')
    return Q(types__contains=[type_code])


def parse_type_filters(request):
    return normalize_type_codes(request.GET.getlist('type'))


def filter_tasks_by_types(queryset, type_codes):
    selected = normalize_type_codes(type_codes)
    if not selected:
        return queryset
    q = Q()
    for code in selected:
        q |= _type_match_q(code)
    return queryset.filter(q)


def tasks_with_type(queryset, type_code):
    if type_code not in VALID_TASK_TYPE_CODES:
        return queryset.none()
    return queryset.filter(_type_match_q(type_code))


def aggregate_task_types(queryset):
    counter = Counter()
    for types_list in queryset.values_list('types', flat=True):
        for code in types_list or []:
            if code in VALID_TASK_TYPE_CODES:
                counter[code] += 1
    return counter


def type_labels(types_list):
    return [TYPE_LABELS.get(code, code) for code in (types_list or [])]

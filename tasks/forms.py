from datetime import timedelta

from django import forms
from django.utils import timezone

from accounts.models import User
from .models import Task, Team

DEADLINE_INPUT_FORMATS = [
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d %H:%i',
    '%d.%m.%Y %H:%M',
    '%Y-%m-%dT%H:%M',
    '%Y-%m-%dT%H:%M:%S',
]


class TaskForm(forms.ModelForm):
    types = forms.MultipleChoiceField(
        choices=Task.TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'mg-type-checkboxes'}),
        required=True,
        label='Типы',
    )

    class Meta:
        model = Task
        fields = [
            'title', 'description', 'link', 'types', 'rank',
            'due_date', 'assigned_to', 'team',
        ]
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'rank': 'Ранг',
            'due_date': 'Срок',
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'mg-input',
                'placeholder': 'Название задачи',
            }),
            'description': forms.Textarea(attrs={
                'class': 'mg-input',
                'rows': 3,
                'placeholder': 'Что нужно сделать…',
            }),
            'link': forms.URLInput(attrs={
                'class': 'mg-input',
                'placeholder': 'https://github.com/org/repo',
                'inputmode': 'url',
            }),
            'rank': forms.NumberInput(attrs={'class': 'mg-input'}),
            'due_date': forms.TextInput(attrs={
                'class': 'mg-input mg-deadline-input',
                'placeholder': 'Выберите дату и время',
                'autocomplete': 'off',
                'readonly': 'readonly',
            }),
            'assigned_to': forms.Select(attrs={'class': 'mg-input'}),
            'team': forms.Select(attrs={'class': 'mg-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].input_formats = DEADLINE_INPUT_FORMATS
        self.fields['link'].required = False
        self.fields['link'].label = 'Ссылка'
        self.fields['assigned_to'].queryset = User.objects.filter(role='worker')
        self.fields['team'].queryset = Team.objects.all()
        self.fields['assigned_to'].required = False
        self.fields['team'].required = False
        self.fields['assigned_to'].label = 'Назначить работнику'
        self.fields['assigned_to'].empty_label = '— Выберите работника —'
        self.fields['team'].label = 'Назначить команде'
        self.fields['team'].empty_label = '— Выберите команду —'

        if self.instance.pk and self.instance.types:
            self.initial.setdefault('types', self.instance.types)

        if not self.is_bound:
            due = self.initial.get('due_date') or self.instance.due_date if self.instance.pk else None
            if due:
                if hasattr(due, 'strftime'):
                    self.initial['due_date'] = timezone.localtime(due).strftime('%Y-%m-%d %H:%M')
            else:
                default_due = timezone.localtime(timezone.now() + timedelta(days=1))
                self.initial['due_date'] = default_due.strftime('%Y-%m-%d %H:%M')

    def clean_types(self):
        types = self.cleaned_data.get('types') or []
        if not types:
            raise forms.ValidationError('Выберите хотя бы один тип задачи.')
        return types

    def clean(self):
        cleaned_data = super().clean()
        assigned = cleaned_data.get('assigned_to')
        team = cleaned_data.get('team')
        if assigned and team:
            raise forms.ValidationError('Назначьте либо работника, либо команду, но не обоих.')
        if not assigned and not team:
            raise forms.ValidationError('Назначьте работника или команду.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.types = self.cleaned_data.get('types', [])
        if commit:
            instance.save()
        return instance


class TeamForm(forms.ModelForm):
    target_types = forms.MultipleChoiceField(
        choices=Task.TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'mg-type-option__input'}),
        required=False,
        label='Типы задач команды',
    )
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(role='worker'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Участники команды',
    )

    class Meta:
        model = Team
        fields = ['name', 'description', 'target_types', 'members']
        labels = {
            'name': 'Название',
            'description': 'Описание',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'mg-input',
                'placeholder': 'Название команды',
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'mg-input',
                'placeholder': 'Над чем работает эта команда?',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            if self.instance.target_types:
                self.initial.setdefault('target_types', self.instance.target_types)
            self.initial.setdefault('members', self.instance.members.all())

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.target_types = self.cleaned_data.get('target_types') or []
        if commit:
            instance.save()
            self.save_m2m()
        return instance

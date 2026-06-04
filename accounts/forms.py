from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm

from .models import Skill, User, UserSkill


class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = (
        ('worker', 'Работник'),
        ('manager', 'Менеджер'),
    )

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='worker',
        label='Роль',
        widget=forms.RadioSelect(attrs={'class': 'auth-role-options'}),
    )
    manager_invite_code = forms.CharField(
        required=False,
        label='Код приглашения менеджера',
        widget=forms.TextInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Код из .env',
            'autocomplete': 'off',
        }),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Имя пользователя',
            'email': 'Email',
        }

    def __init__(self, *args, manager_signup_enabled=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.manager_signup_enabled = manager_signup_enabled
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'
        for field in self.fields.values():
            field.help_text = ''
        if not manager_signup_enabled:
            del self.fields['role']
            del self.fields['manager_invite_code']

    def clean(self):
        cleaned = super().clean()
        if not self.manager_signup_enabled:
            return cleaned

        role = cleaned.get('role', 'worker')
        if role == 'manager':
            expected = getattr(settings, 'MANAGER_REGISTRATION_CODE', '')
            if not expected:
                raise forms.ValidationError(
                    'Регистрация менеджера отключена. Обратитесь к администратору.'
                )
            code = (cleaned.get('manager_invite_code') or '').strip()
            if code != expected:
                self.add_error(
                    'manager_invite_code',
                    'Неверный код приглашения.',
                )
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.manager_signup_enabled:
            user.role = self.cleaned_data.get('role', 'worker')
        else:
            user.role = 'worker'
        if commit:
            user.save()
        return user


# Форма редактирования личных данных и соцсетей
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['full_name', 'email', 'phone', 'address', 'website', 'github', 'twitter', 'telegram']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'mg-input', 'placeholder': 'Полное имя'}),
            'email': forms.EmailInput(attrs={'class': 'mg-input', 'placeholder': 'email@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'mg-input', 'placeholder': '+7 (123) 456-78-90'}),
            'address': forms.TextInput(attrs={'class': 'mg-input', 'placeholder': 'Город, улица'}),
            'website': forms.URLInput(attrs={'class': 'mg-input', 'placeholder': 'https://example.com'}),
            'github': forms.TextInput(attrs={'class': 'mg-input', 'placeholder': 'username'}),
            'twitter': forms.TextInput(attrs={'class': 'mg-input', 'placeholder': '@username'}),
            'telegram': forms.TextInput(attrs={'class': 'mg-input', 'placeholder': '@username'}),
        }


# Динамическая форма для оценки навыков (используется менеджером)
class UserSkillsForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for skill in Skill.objects.all():
            try:
                user_skill = UserSkill.objects.get(user=user, skill=skill)
                initial_value = user_skill.value
            except UserSkill.DoesNotExist:
                initial_value = 5
            self.fields[f'skill_{skill.id}'] = forms.IntegerField(
                label=skill.name,
                min_value=1,
                max_value=10,
                initial=initial_value,
                widget=forms.NumberInput(attrs={'class': 'form-control bg-dark text-white', 'step': 1})
            )

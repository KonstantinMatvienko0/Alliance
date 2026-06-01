from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserSkill, Skill

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        labels = {
            'username': 'Имя пользователя',
            'email': 'Email',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'
        for field in self.fields.values():
            field.help_text = ''

    def save(self, commit=True):
        user = super().save(commit=False)
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
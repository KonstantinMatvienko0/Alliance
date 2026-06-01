from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Skill, User, UserSkill, WorkSession


@admin.register(User)
class AllianceUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'rating', 'teams_display')
    list_filter = ('role', 'teams')
    search_fields = ('username', 'email', 'full_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Alliance', {'fields': ('role', 'rating', 'full_name', 'phone', 'address', 'website', 'github', 'twitter', 'telegram')}),
    )

    @admin.display(description='Команды')
    def teams_display(self, obj):
        return obj.team_names_display() or '—'
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Alliance', {'fields': ('role', 'email')}),
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'skill_type', 'icon')
    list_filter = ('skill_type',)
    search_fields = ('name',)


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill', 'value')
    list_filter = ('skill__skill_type',)
    search_fields = ('user__username', 'skill__name')


@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'started_at', 'ended_at', 'duration_display', 'is_active')
    list_filter = ('ended_at',)
    search_fields = ('user__username',)
    raw_id_fields = ('user',)
    date_hierarchy = 'started_at'

    @admin.display(boolean=True, description='Активна')
    def is_active(self, obj):
        return obj.is_active

    @admin.display(description='Длительность')
    def duration_display(self, obj):
        from .services.work_timer import format_duration
        return format_duration(obj.duration_seconds())

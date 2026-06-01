from django.contrib import admin

from .models import Task, Team


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'types_display', 'status', 'rank', 'link', 'assigned_to', 'team', 'due_date', 'completed_by', 'created_by')
    list_filter = ('status', 'team')
    search_fields = ('title', 'description')
    raw_id_fields = ('assigned_to', 'team', 'created_by', 'completed_by')
    date_hierarchy = 'due_date'

    @admin.display(description='Types')
    def types_display(self, obj):
        return ', '.join(obj.types or [])


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    search_fields = ('name', 'description')
    raw_id_fields = ('created_by',)

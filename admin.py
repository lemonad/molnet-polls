# -*- coding: utf-8 -*-
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from models import (Choice, Poll, Vote)


class ChoiceAdmin(admin.ModelAdmin):
    fields = ['poll', 'choice', 'added_by']
    list_display = ['poll', 'choice', 'added_by', 'date_created']
    search_fields = ['choice']

admin.site.register(Choice, ChoiceAdmin)


class PollAdmin(admin.ModelAdmin):
    fields = ['title', 'description', 'created_by', 'allow_new_choices',
              'status', 'published_at']
    list_display = ['title', 'created_by', 'allow_new_choices',
                    'status', 'published_at', 'date_created',
                    'date_modified']
    list_filter = ['status', 'allow_new_choices']
    search_fields = ['title', 'description']

admin.site.register(Poll, PollAdmin)


class VoteAdmin(admin.ModelAdmin):
    fields = ['user', 'choice']
    list_display = ['user', 'choice', 'date_created']

admin.site.register(Vote, VoteAdmin)

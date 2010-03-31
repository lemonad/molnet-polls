# -*- coding: utf-8 -*-
import re

from django.contrib.auth.models import User
from django.db import connection
from django.db.models import (BooleanField, CharField, DateField,
                              DateTimeField, ForeignKey, Manager, Model,
                              TextField, TimeField)
from django.utils.translation import ugettext_lazy as _


class PollManager(Manager):
    pass


class Poll(Model):
    """ A poll is basically a question with multiple pre-defined
    choices that users can pick amongst. Users vote by selecting
    one choice, or optionally, create a new choice _and_ vote on it).

    By answering a poll, a user increases the poll's popularity.

    Polls are created by a specific user, which becomes the poll's
    administrator. Polls are either in draft mode or published.

    Polls have a title and an optional description (markdown).

    """
    created_by = ForeignKey(User,
                            verbose_name=_('created by'),
                            null=False,
                            db_index=True)
    title = CharField(_('title'),
                      max_length=140,
                      null=False,
                      blank=False)
    description = TextField(_('description'),
                            blank=True)
    allow_new_choices = BooleanField(_('allow users to add choices?'),
                                     null=False,
                                     default=False)
    is_published = BooleanField(_('is published?'),
                                null=False,
                                db_index=True,
                                default=False)
    published_at = DateTimeField(_('date and time published'),
                                 blank=True,
                                 db_index=True)
    date_created = DateTimeField(_('created (date)'),
                                 null=False,
                                 db_index=True,
                                 auto_now_add=True)
    date_modified = DateTimeField(_('modified (date)'),
                                  null=False,
                                  db_index=True,
                                  auto_now=True)

    objects = PollManager()

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ['-is_published', '-published_at']
        verbose_name = _('poll')
        verbose_name_plural = _('polls')


class Choice(Model):
    """ A poll consists of multiple choices which users can "vote" on. """

    poll = ForeignKey(Poll,
                      verbose_name=_('poll'),
                      null=False,
                      db_index=True)
    choice = CharField(_('choice'),
                      max_length=255,
                      null=False,
                      blank=False)
    added_by = ForeignKey(User,
                          verbose_name=_('added by'),
                          null=False,
                          db_index=True)
    date_created = DateTimeField(_('created (date)'),
                                 null=False,
                                 db_index=True,
                                 auto_now_add=True)

    def __unicode__(self):
        return self.choice

    class Meta:
        ordering = ['-date_created']
        verbose_name = _('choice')
        verbose_name_plural = _('choices')


class Vote(Model):
    """ A vote on a poll choice by a user. """

    user = ForeignKey(User,
                      verbose_name=_('user'),
                      null=False,
                      db_index=True)
    choice = ForeignKey(Choice,
                      verbose_name=_('choice'),
                      null=False,
                      db_index=True)
    date_created = DateTimeField(_('created (date)'),
                                 null=False,
                                 db_index=True,
                                 auto_now_add=True)

    class Meta:
        ordering = ['-date_created']
        verbose_name = _('vote')
        verbose_name_plural = _('votes')

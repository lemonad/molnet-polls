# -*- coding: utf-8 -*-
import re

from django.contrib.auth.models import User
from django.db import connection
from django.db.models import (BooleanField, CharField, Count, DateField,
                              DateTimeField, ForeignKey, Manager, Model,
                              Q, TextField, TimeField)
from django.utils.translation import ugettext_lazy as _


class PollManager(Manager):
    def recent(self):
        return self.exclude(status='DRAFT') \
                   .order_by('-published_at')
    def created_by_user(self, userid):
        return self.filter(created_by=userid) \
                   .order_by('-published_at')
    def answered_by_user(self, userid):
        return self.filter(choice__vote__user=userid) \
                   .exclude(status='DRAFT') \
                   .order_by('-choice__vote__date_modified')


class Poll(Model):
    """ A poll is basically a question with multiple pre-defined
    choices that users can pick amongst. Users vote by selecting
    one choice, or optionally, create a new choice _and_ vote on it).

    By answering a poll, a user increases the poll's popularity.

    Polls are created by a specific user, which becomes the poll's
    administrator. Polls are either in draft mode or published.

    Polls have a title and an optional description (markdown).

    """

    STATUS_CHOICES = (('DRAFT', _("Draft")),
                      ('PUBLISHED', _("Published")),
                      ('CLOSED', _("Closed")))

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
    status = CharField(_("Status"),
                       db_index=True,
                       max_length=32,
                       choices=STATUS_CHOICES,
                       default='DRAFT')
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
        ordering = ['-published_at']
        verbose_name = _('poll')
        verbose_name_plural = _('polls')


class ChoiceManager(Manager):
    def get_choices_and_votes_for_poll(self, pollid):
        return self.filter(poll=pollid) \
                   .annotate(num_votes=Count('vote'))

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
    objects = ChoiceManager()

    def __unicode__(self):
        return self.choice

    class Meta:
        ordering = ['-date_created']
        verbose_name = _('choice')
        verbose_name_plural = _('choices')


class VoteManager(Manager):
    def votes_for_poll(self, pollid):
        return self.filter(choice__poll=pollid)


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
    date_modified = DateTimeField(_('modified (date)'),
                                  null=False,
                                  db_index=True,
                                  auto_now=True)
    objects = VoteManager()

    class Meta:
        ordering = ['-date_created']
        verbose_name = _('vote')
        verbose_name_plural = _('votes')

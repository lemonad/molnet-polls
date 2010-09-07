# -*- coding: utf-8 -*-
import re

from autoslug import AutoSlugField
from django.contrib.auth.models import User
from django.db import connection
from django.db.models import (BooleanField, CharField, Count, DateField,
                              DateTimeField, ForeignKey, Manager, Model,
                              permalink, Q, TextField, TimeField)
from django.utils.translation import ugettext_lazy as _


class PollManager(Manager):
    def recent(self):
        return self.exclude(status='DRAFT') \
                   .order_by('-published_at')
    def created_by_user(self, userid):
        return self.filter(user=userid) \
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

    slug = AutoSlugField(_("Slug"),
                         populate_from='title',
                         editable=False,
                         unique=True,
                         blank=True,
                         max_length=80)
    user = ForeignKey(User,
                      verbose_name=_('created by'),
                      db_index=True)
    title = CharField(_('title'),
                      max_length=140,
                      unique=True)
    description = TextField(_('description'),
                            blank=True)
    allow_new_choices = BooleanField(_('allow users to add choices?'),
                                     default=False)
    status = CharField(_("Status"),
                       db_index=True,
                       max_length=32,
                       choices=STATUS_CHOICES,
                       default='DRAFT')
    published_at = DateTimeField(_('date and time published'),
                                 null=True,
                                 blank=True,
                                 db_index=True)
    date_created = DateTimeField(_('created (date)'),
                                 db_index=True,
                                 auto_now_add=True)
    date_modified = DateTimeField(_('modified (date)'),
                                  db_index=True,
                                  auto_now=True)
    objects = PollManager()

    def __unicode__(self):
        return self.title

    def number_of_votes(self):
        q = self.choice_set.aggregate(num_votes=Count('vote'))
        return q['num_votes']

    def is_draft(self):
        return (self.status == 'DRAFT')

    def is_published(self):
        return (self.status != 'DRAFT')

    def is_closed(self):
        return (self.status == 'CLOSED')

    @permalink
    def get_absolute_url(self):
        return ('molnet-polls-show-poll', (),
                {'year': self.published_at.year,
                 'month': self.published_at.month,
                 'day': self.published_at.day,
                 'slug': self.slug})

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
                      db_index=True)
    choice = CharField(_('choice'),
                      max_length=255)
    user = ForeignKey(User,
                      verbose_name=_('added by'),
                      db_index=True)
    date_created = DateTimeField(_('created (date)'),
                                 db_index=True,
                                 auto_now_add=True)
    objects = ChoiceManager()

    def __unicode__(self):
        return self.choice

    class Meta:
        unique_together = (('poll', 'choice'),)
        ordering = ['date_created']
        verbose_name = _('choice')
        verbose_name_plural = _('choices')


class VoteManager(Manager):
    def votes_for_poll(self, pollid):
        return self.filter(choice__poll=pollid)


class Vote(Model):
    """ A vote on a poll choice by a user. """

    user = ForeignKey(User,
                      verbose_name=_('user'),
                      db_index=True)
    choice = ForeignKey(Choice,
                      verbose_name=_('choice'),
                      db_index=True)
    date_created = DateTimeField(_('created (date)'),
                                 db_index=True,
                                 auto_now_add=True)
    date_modified = DateTimeField(_('modified (date)'),
                                  db_index=True,
                                  auto_now=True)
    objects = VoteManager()

    class Meta:
        ordering = ['-date_created']
        verbose_name = _('vote')
        verbose_name_plural = _('votes')

# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.contrib.syndication.feeds import Feed
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db.models import Count, Q
from django.utils.translation import ugettext_lazy as _

from models import Choice, Poll, Vote


class LatestPolls(Feed):
    title = _("Latest polls")
    description = _("The latest polls submitted by your co-workers")

    def items(self):
        return Poll.objects.recent()

    def link(self):
        """ Defined as a method as reverse will otherwise throw an
        improperlyConfigured exception because the url patterns have
        not yet been compiled when importing this class.

        """
        return reverse("molnet-polls-startpage")

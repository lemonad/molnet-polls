# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.utils import translation

# Switch language temporarily for "static" I18n of URLs
language_for_urls = settings.LANGUAGE_CODE[:2]
language_saved = translation.get_language()
translation.activate(language_for_urls)

urlpatterns = patterns('molnet.polls.views',
    url(r'^$', 'startpage', name='molnet-polls-startpage'),
    url(r'^(?P<pollid>[0-9]+)/$', 'show_poll', name='molnet-polls-show-poll'),
)

# Switch back to the language of choice
translation.activate(language_saved)

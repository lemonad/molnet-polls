# -*- coding: utf-8 -*-
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.utils import translation

from feeds import LatestPolls

feeds = {'latest': LatestPolls}

# Switch language temporarily for "static" I18n of URLs
language_for_urls = settings.LANGUAGE_CODE[:2]
language_saved = translation.get_language()
translation.activate(language_for_urls)

urlpatterns = patterns('molnet.polls.views',
    url(r'^$', 'startpage', name='molnet-polls-startpage'),
    # url(r'^(?P<pollid>[0-9]+)/$', 'show_poll', name='molnet-polls-show-poll'),
    url(r'^new$', 'create_poll', name='molnet-polls-create-poll'),
    url(r'^edit/(?P<slug>[^\/]+)$', 'edit_poll', name='molnet-polls-edit-poll'),
    url(r'^(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})/(?P<day>[0-9]{1,2})/(?P<slug>[^\/]+)/$',
        'show_poll',
        name='molnet-polls-show-poll'),
)

# Feeds
urlpatterns += patterns('',
    url(r'^feeds/(?P<url>.*)/$',
        'django.contrib.syndication.views.feed',
        name='molnet-polls-feed-latest-polls',
        kwargs={'feed_dict': feeds}),
)

# Switch back to the language of choice
translation.activate(language_saved)


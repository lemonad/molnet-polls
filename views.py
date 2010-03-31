# -*- coding: utf-8 -*-
import time
import datetime

from django import forms
from django.conf import settings
from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import LogEntry
from django.contrib.admin.models import DELETION
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import connection
from django.db.models import Q
from django.forms import ModelForm
from django.http import (HttpResponse, HttpResponseNotFound, Http404,
                         HttpResponseRedirect)
from django.shortcuts import (get_object_or_404, get_list_or_404,
                              render_to_response)
from django.template import Context, RequestContext, loader
from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from models import Choice, Poll, Vote

#
# Forms
#

class ChoiceWithOtherRenderer(forms.RadioSelect.renderer):
    """RadioFieldRenderer that renders its last choice with a placeholder."""
    def __init__(self, *args, **kwargs):
        super(ChoiceWithOtherRenderer, self).__init__(*args, **kwargs)
        self.choices, self.other = self.choices[:-1], self.choices[-1]

    def __iter__(self):
        for input in super(ChoiceWithOtherRenderer, self).__iter__():
            yield input
        id = '%s_%s' % (self.attrs['id'], self.other[0]) if 'id' in self.attrs else ''
        label_for = ' for="%s"' % id if id else ''
        checked = '' if not force_unicode(self.other[0]) == self.value else 'checked="true" '
        yield '<label%s><input type="radio" id="%s" value="%s" name="%s" %s/> %s</label> %%s' % (
            label_for, id, self.other[0], self.name, checked, self.other[1])

class ChoiceWithOtherWidget(forms.MultiWidget):
    """MultiWidget for use with ChoiceWithOtherField."""
    def __init__(self, choices):
        widgets = [
            forms.RadioSelect(choices=choices, renderer=ChoiceWithOtherRenderer),
            forms.TextInput
        ]
        super(ChoiceWithOtherWidget, self).__init__(widgets)

    def decompress(self, value):
        if not value:
            return [None, None]
        return value

    def format_output(self, rendered_widgets):
        """Format the output by substituting the "other" choice into the first widget."""
        return rendered_widgets[0] % rendered_widgets[1]

class ChoiceWithOtherField(forms.MultiValueField):
    """
    ChoiceField with an option for a user-submitted "other" value.

    The last item in the choices array passed to __init__ is expected to be a choice for "other". This field's
    cleaned data is a tuple consisting of the choice the user made, and the "other" field typed in if the choice
    made was the last one.

    >>> class AgeForm(forms.Form):
    ...     age = ChoiceWithOtherField(choices=[
    ...         (0, '15-29'),
    ...         (1, '30-44'),
    ...         (2, '45-60'),
    ...         (3, 'Other, please specify:')
    ...     ])
    ...
    >>> # rendered as a RadioSelect choice field whose last choice has a text input
    ... print AgeForm()['age']
    <ul>
    <li><label for="id_age_0_0"><input type="radio" id="id_age_0_0" value="0" name="age_0" /> 15-29</label></li>
    <li><label for="id_age_0_1"><input type="radio" id="id_age_0_1" value="1" name="age_0" /> 30-44</label></li>
    <li><label for="id_age_0_2"><input type="radio" id="id_age_0_2" value="2" name="age_0" /> 45-60</label></li>
    <li><label for="id_age_0_3"><input type="radio" id="id_age_0_3" value="3" name="age_0" /> Other, please \
specify:</label> <input type="text" name="age_1" id="id_age_1" /></li>
    </ul>
    >>> form = AgeForm({'age_0': 2})
    >>> form.is_valid()
    True
    >>> form.cleaned_data
    {'age': (u'2', u'')}
    >>> form = AgeForm({'age_0': 3, 'age_1': 'I am 10 years old'})
    >>> form.is_valid()
    True
    >>> form.cleaned_data
    {'age': (u'3', u'I am 10 years old')}
    >>> form = AgeForm({'age_0': 1, 'age_1': 'This is bogus text which is ignored since I didn\\'t pick "other"'})
    >>> form.is_valid()
    True
    >>> form.cleaned_data
    {'age': (u'1', u'')}
    """
    def __init__(self, *args, **kwargs):
        fields = [
            forms.ChoiceField(widget=forms.RadioSelect(renderer=ChoiceWithOtherRenderer), *args, **kwargs),
            forms.CharField(required=False)
        ]
        widget = ChoiceWithOtherWidget(choices=kwargs['choices'])
        kwargs.pop('choices')
        self._was_required = kwargs.pop('required', True)
        kwargs['required'] = False
        super(ChoiceWithOtherField, self).__init__(widget=widget, fields=fields, *args, **kwargs)

    def compress(self, value):
        if self._was_required and not value or value[0] in (None, ''):
            raise forms.ValidationError(self.error_messages['required'])
        if not value:
            return [None, u'']
        return (value[0], value[1] if force_unicode(value[0]) == force_unicode(self.fields[0].choices[-1][0]) else u'')


class PollForm(forms.Form):
    """Form for adding and editing polls."""

    def __init__(self, *args, **kwargs):
            choices = kwargs.pop('choices')
            allow_new_choices = kwargs.pop('allow_new_choices')
            vote_id = kwargs.pop('vote_id')
            vote_id = 1
            super(PollForm, self).__init__(*args, **kwargs)

            if allow_new_choices:
                choices.append(('NEW_ISSUE', 'Other'))
                self.fields['choices'] = \
                        ChoiceWithOtherField(choices=choices,
                                             required=True)
            else:
                self.fields['choices'] = \
                        forms.ChoiceField(choices=choices,
                                          widget=forms.RadioSelect,
                                          required=True)

def startpage(request):
    """
    Start page.

    """

    # form_trip = None
    # 
    # if request.user.is_authenticated():
    #     if request.method == 'POST':
    #         # The form has been submitted
    #           form_trip = TripForm(request.POST, Trip)
    #           if form_trip.is_valid():
    #               save_trip(form_trip, request.user)
    #               # Redirect after POST
    #               return HttpResponseRedirect(reverse('molnet-trips-startpage'))
    #     else:
    #         # Initialize form
    #         form_trip_defaults = \
    #                         {'travel_from': '',
    #                          'travel_to': '',
    #                          'can_take_passengers': True,
    #                          'can_take_cargo': True,
    #                          'departure_date': datetime.datetime.now(). \
    #                                                     strftime("%Y-%m-%d"),
    #                          'departure_time': '8:00'}
    #         form_trip = TripForm(form_trip_defaults)
    #         # TODO: Find proper way to reset validation errors (cont.)
    #         #       so that to and from fields can be kept empty
    #         form_trip._errors = {}

    polls = Poll.objects.all()
    if request.user.is_authenticated():
        polls_created_by_user = Poll.objects.filter(created_by=request.user)
        polls_answered_by_user = Poll.objects.filter(choice__vote__user=
                                                               request.user)

    t = loader.get_template('polls-index.html')
    c = RequestContext(request,
                       {'polls': polls,
                        'polls_created_by_user': polls_created_by_user,
                        'polls_answered_by_user': polls_answered_by_user})
    return HttpResponse(t.render(c))

def show_poll(request, pollid):
    poll = get_object_or_404(Poll, id=pollid)
    choices = Choice.objects.filter(poll=pollid)

    number_of_votes = Vote.objects.filter(choice__poll=pollid).count()

    vote_id = None
    if request.user.is_authenticated():
        vote = Vote.objects.get(Q(user=request.user.id)&
                                Q(choice__poll=pollid))
        vote_id = vote.choice.id

    form_choices = []
    for choice in choices:
        form_choices.append((str(choice.id), choice.choice))

    poll_form_defaults = {'choices': str(vote_id)}
    form = PollForm(choices=form_choices,
                    allow_new_choices=poll.allow_new_choices,
                    vote_id=vote_id,
                    initial=poll_form_defaults)
    related_polls = None
    t = loader.get_template('polls-show-poll.html')
    c = RequestContext(request,
                       {'poll': poll,
                        'form': form,
                        'vote_id': vote_id,
                        'number_of_votes': number_of_votes,
                        'related_polls': related_polls})
    return HttpResponse(t.render(c))

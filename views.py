# -*- coding: utf-8 -*-
import copy
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
from django.db.models import Count, Q
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
    def __init__(self, choices, other_widget):
        widgets = [
            forms.RadioSelect(choices=choices, renderer=ChoiceWithOtherRenderer),
            other_widget
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

    The last item in the choices array passed to __init__ is expected to be a
    choice for "other". This field's cleaned data is a tuple consisting of the
    choice the user made, and the "other" field typed in if the choice made was
    the last one.

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
        other_field = kwargs.pop('other_field', None)
        if other_field is None:
            other_field = forms.CharField(required=False)
        fields = [
            forms.ChoiceField(widget=forms.RadioSelect(renderer=ChoiceWithOtherRenderer), *args, **kwargs),
            other_field
        ]
        widget = ChoiceWithOtherWidget(choices=kwargs['choices'], other_widget=other_field.widget)
        kwargs.pop('choices')
        self._was_required = kwargs.pop('required', True)
        kwargs['required'] = False
        super(ChoiceWithOtherField, self).__init__(widget=widget, fields=fields, *args, **kwargs)

    def clean(self, value):
        # MultiValueField turns off the "required" field for all the fields.
        # It prevents us from requiring the manual entry.  This implements that.
        if self._was_required:
            if value and value[0] == self.fields[0].choices[-1][0]:
                manual_choice = value[1]
                if not manual_choice:
                    raise forms.ValidationError(self.error_messages['required'])
        return super(ChoiceWithOtherField, self).clean(value)

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
            super(PollForm, self).__init__(*args, **kwargs)

            if allow_new_choices:
                choices.append(('OTHER', 'Other'))
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

    recent_polls = Poll.objects.recent()
    polls_created_by_user = None
    polls_answered_by_user = None
    if request.user.is_authenticated():
        polls_created_by_user = Poll.objects.created_by_user(request.user.id)
        polls_answered_by_user = Poll.objects.answered_by_user(request.user.id)

    t = loader.get_template('polls-index.html')
    c = RequestContext(request,
                       {'recent_polls': recent_polls,
                        'polls_created_by_user': polls_created_by_user,
                        'polls_answered_by_user': polls_answered_by_user,
                        'has_sidebar': True})
    return HttpResponse(t.render(c))


def get_form_choices(choices):
    form_choices = []
    for choice in choices:
        form_choices.append((str(choice.id), choice.choice))
    return form_choices

def show_poll(request, pollid):
    form = None
    poll = get_object_or_404(Poll, id=pollid)
    choices = Choice.objects.get_choices_and_votes_for_poll(pollid)

    show_results = False
    if 'show-results' in request.GET:
        show_results = True

    voted_for_choice_id = None
    if request.user.is_authenticated():
        print "Hello"
        try:
            vote = Vote.objects.get(Q(user=request.user.id)&
                                    Q(choice__poll=pollid))
            voted_for_choice_id = vote.choice.id
            show_results = True
        except Vote.DoesNotExist:
            voted_for_choice_id = None

        form_choices = get_form_choices(choices)
        if request.method == 'POST':
            form = PollForm(request.POST,
                            choices=form_choices,
                            allow_new_choices=poll.allow_new_choices)
            if form.is_valid():
                choice_id, choice_text = form.cleaned_data['choices']
                if choice_id == 'OTHER':
                    # Check for duplicates
                    try:
                        choice = Choice.objects.get(Q(poll=pollid)&
                                                    Q(choice=choice_text))
                    except Choice.DoesNotExist:
                        # Add new choice
                        choice = Choice.objects.create(poll=poll,
                                                       choice=choice_text,
                                                       added_by=request.user)
                    # Voted already?
                    if voted_for_choice_id:
                        # Yes, change vote
                        vote.choice = choice
                        vote.save()
                    else:
                        # No, add vote
                        Vote.objects.create(user=request.user, choice=choice)
                else:
                    # Check that the choice is valid for this poll
                    choice = get_object_or_404(Choice,
                                               id=choice_id,
                                               poll=pollid)
                    # Voted already?
                    if voted_for_choice_id:
                        # Yes, change vote
                        vote.choice = choice
                        vote.save()
                    else:
                        # No, add vote
                        Vote.objects.create(user=request.user, choice=choice)

                voted_for_choice_id = choice.id
                choices = Choice.objects.get_choices_and_votes_for_poll(pollid)
                form_choices = get_form_choices(choices)
        else:
            # Form not submitted
            if voted_for_choice_id:
                poll_form_defaults = {'choices': (str(voted_for_choice_id), '')}
                form = PollForm(choices=form_choices,
                                allow_new_choices=poll.allow_new_choices,
                                initial=poll_form_defaults)
            else:
                form = PollForm(choices=form_choices,
                                allow_new_choices=poll.allow_new_choices)

    number_of_votes = Vote.objects.votes_for_poll(pollid).count()
    related_polls = None

    recent_polls = Poll.objects.recent()
    polls_created_by_user = None
    polls_answered_by_user = None
    if request.user.is_authenticated():
        polls_created_by_user = Poll.objects.created_by_user(request.user.id)
        polls_answered_by_user = Poll.objects.answered_by_user(request.user.id)

    t = loader.get_template('polls-show-poll.html')
    c = RequestContext(request,
                       {'poll': poll,
                        'choices': choices,
                        'form': form,
                        'vote_id': voted_for_choice_id,
                        'number_of_votes': number_of_votes,
                        'related_polls': related_polls,
                        'recent_polls': recent_polls,
                        'polls_created_by_user': polls_created_by_user,
                        'polls_answered_by_user': polls_answered_by_user,
                        'show_results': show_results,
                        'has_sidebar': True})
    return HttpResponse(t.render(c))

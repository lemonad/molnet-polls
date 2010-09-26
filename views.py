# -*- coding: utf-8 -*-
import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db.models import Count, Q
from django.http import (HttpResponse, HttpResponseNotFound, Http404,
                         HttpResponseRedirect, HttpResponseForbidden)
from django.shortcuts import (get_object_or_404, get_list_or_404,
                              render_to_response)
from django.template import Context, RequestContext, loader
from django.utils.translation import ugettext_lazy as _

from forms import ChoiceForm, PollForm, PollVotingForm
from models import Choice, Poll, Vote


def get_sidebar_polls(user):
    created_by_user = None
    answered_by_user = None

    if user.is_authenticated():
        created_by_user = Poll.objects.created_by_user(user.id)
        answered_by_user = Poll.objects.answered_by_user(user.id)

    sidebar_polls = {'created_by_user': created_by_user,
                     'answered_by_user': answered_by_user,
                     'recent': Poll.objects.recent()}
    return sidebar_polls

def get_form_choices(choices):
    form_choices = []
    for choice in choices:
        form_choices.append((str(choice.id), choice.choice))
    return form_choices

def startpage(request):
    """ Start page. """

    sidebar_polls = get_sidebar_polls(request.user)

    t = loader.get_template('polls-index.html')
    c = RequestContext(request,
                       {'sidebar_polls': sidebar_polls,
                        'navigation': 'polls',
                        'navigation2': 'polls-all',})
    return HttpResponse(t.render(c))

def show_poll(request, year, month, day, slug):
    form = None
    poll = get_object_or_404(Poll, slug=slug)
    choices = Choice.objects.get_choices_and_votes_for_poll(poll.id)

    show_results = False
    if 'show-results' in request.GET or poll.status == "CLOSED":
        show_results = True

    if not request.user.is_authenticated():
        voted_for_choice_id = None
    else:
        # Only show form if authenticated
        try:
            vote = Vote.objects.get(Q(user=request.user.id)&
                                    Q(choice__poll=poll.id))
            voted_for_choice_id = vote.choice.id
            show_results = True
        except Vote.DoesNotExist:
            voted_for_choice_id = None

        form_choices = get_form_choices(choices)
        if request.method == 'POST':
            form = PollVotingForm(request.POST,
                                  choices=form_choices,
                                  allow_new_choices=poll.allow_new_choices)
            if form.is_valid():
                if poll.allow_new_choices:
                    choice_id, choice_text = form.cleaned_data['choices']
                else:
                    choice_id = form.cleaned_data['choices']

                if choice_id == 'OTHER':
                    # Check for duplicates
                    choice, created = Choice.objects \
                        .get_or_create(poll=poll,
                                       choice=choice_text,
                                       defaults={'user': request.user})
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
                                               poll=poll.id)
                    # Voted already?
                    if voted_for_choice_id:
                        # Yes, change vote
                        vote.choice = choice
                        vote.save()
                    else:
                        # No, add vote
                        Vote.objects.create(user=request.user, choice=choice)

                voted_for_choice_id = choice.id
                choices = Choice.objects.get_choices_and_votes_for_poll(poll.id)
                form_choices = get_form_choices(choices)
                if poll.allow_new_choices:
                    poll_form_defaults = {'choices': (str(voted_for_choice_id),
                                                      '')}
                else:
                    poll_form_defaults = {'choices': str(voted_for_choice_id)}
                form = PollVotingForm(choices=form_choices,
                                      allow_new_choices=poll.allow_new_choices,
                                      initial=poll_form_defaults)
        else:
            # Form not submitted
            if voted_for_choice_id:
                if poll.allow_new_choices:
                    poll_form_defaults = {'choices': (str(voted_for_choice_id),
                                                          '')}
                else:
                    poll_form_defaults = {'choices': str(voted_for_choice_id)}
                form = PollVotingForm(choices=form_choices,
                                      allow_new_choices=poll.allow_new_choices,
                                      initial=poll_form_defaults)
            else:
                form = PollVotingForm(choices=form_choices,
                                      allow_new_choices=poll.allow_new_choices)

    number_of_votes = Vote.objects.votes_for_poll(poll.id).count()
    related_polls = None
    sidebar_polls = get_sidebar_polls(request.user)

    t = loader.get_template('polls-show-poll.html')
    c = RequestContext(request,
                       {'poll': poll,
                        'choices': choices,
                        'form': form,
                        'vote_id': voted_for_choice_id,
                        'number_of_votes': number_of_votes,
                        'related_polls': related_polls,
                        'sidebar_polls': sidebar_polls,
                        'show_results': show_results})
    return HttpResponse(t.render(c))

@login_required
def create_poll(request):
    if request.method == 'POST':
        form = PollForm(request, request.POST)
        if form.is_valid():
            p = form.save()
            return HttpResponseRedirect(reverse('molnet-polls-edit-poll',
                                                kwargs={'slug': p.slug}))
    else:
        form = PollForm(request)

    sidebar_polls = get_sidebar_polls(request.user)

    t = loader.get_template('polls-create-poll.html')
    c = RequestContext(request,
                       {'form': form,
                        'sidebar_polls': sidebar_polls,
                        'navigation': 'polls',
                        'navigation2': 'polls-create',})
    return HttpResponse(t.render(c))

@login_required
def edit_poll(request, slug):
    poll = get_object_or_404(Poll, slug=slug)

    if request.user != poll.user:
        raise PermissionDenied("You must own a poll in order to edit it.")

    choices = Choice.objects.get_choices_and_votes_for_poll(poll.id)

    poll_form = PollForm(request, instance=poll, prefix='poll')
    choice_form = ChoiceForm(request, poll, prefix='choice')

    if request.method == 'POST':
        if 'poll' in request.POST:
            poll_form = PollForm(request,
                                 request.POST,
                                 instance=poll,
                                 prefix='poll')
            if poll_form.is_valid():
                p = poll_form.save()
                return HttpResponseRedirect(reverse('molnet-polls-edit-poll',
                                                    kwargs={'slug': p.slug}))

        elif 'choice' in request.POST:
            choice_form = ChoiceForm(request,
                                     poll,
                                     request.POST,
                                     prefix='choice')
            if choice_form.is_valid():
                choice, created = Choice.objects \
                    .get_or_create(poll=poll,
                                   choice=choice_form.cleaned_data['choice'],
                                   defaults={'user': request.user})
                return HttpResponseRedirect(reverse('molnet-polls-edit-poll',
                                                    kwargs={'slug':
                                                            poll.slug}))
        elif 'delete-choice' in request.POST and 'choice-id' in request.POST:
            try:
                choice = Choice.objects.get(id=request.POST['choice-id'],
                                            poll=poll) \
                                       .delete()
                return HttpResponseRedirect(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': poll.slug}))
            except Choice.DoesNotExist:
                raise Http404
        elif 'delete' in request.POST:
            poll.delete()
            return HttpResponseRedirect(reverse('molnet-polls-startpage'))
        elif 'close' in request.POST:
            poll.status="CLOSED"
            poll.save()
            return HttpResponseRedirect(reverse('molnet-polls-edit-poll',
                                                kwargs={'slug': poll.slug}))
        elif 're-open' in request.POST:
            poll.status="PUBLISHED"
            poll.save()
            return HttpResponseRedirect(reverse('molnet-polls-edit-poll',
                                                kwargs={'slug': poll.slug}))
        elif 'unpublish' in request.POST:
            poll.status="DRAFT"
            poll.save()
            return HttpResponseRedirect(reverse('molnet-polls-edit-poll',
                                                kwargs={'slug': poll.slug}))
        elif 'publish' in request.POST:
            poll.status="PUBLISHED"
            poll.published_at = datetime.datetime.now()
            poll.save()
            return HttpResponseRedirect(reverse('molnet-polls-edit-poll',
                                                kwargs={'slug': poll.slug}))
        else:
            raise Http404

    related_polls = None
    sidebar_polls = get_sidebar_polls(request.user)

    t = loader.get_template('polls-edit-poll.html')
    c = RequestContext(request,
                       {'poll': poll,
                        'choices': choices,
                        'choice_form': choice_form,
                        'poll_form': poll_form,
                        'related_polls': related_polls,
                        'sidebar_polls': sidebar_polls})
    return HttpResponse(t.render(c))

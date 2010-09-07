# -*- coding: utf-8 -*-
"""
Tests for polls.

"""
from datetime import datetime

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.http import urlquote
from django.utils.translation import ugettext

from models import Choice, Poll, Vote


class PollModelTests(TestCase):
    fixtures = ['users.json',
                'polls.json',
                'choices.json',
                'votes.json']

    def test_poll_creation(self):
        now = datetime.now()
        u = User.objects.all()[1]
        p = Poll.objects.create(user=u,
                                title="I can has cheezburger?",
                                description="**kthxbye!**",
                                allow_new_choices=False,
                                status='PUBLISHED',
                                published_at=now)

    def test_poll_deletion(self):
        p = Poll.objects.all()[0]
        p.delete()
        self.assertRaises(ObjectDoesNotExist, Poll.objects.get, id=p.id)

    def test_choice_creation(self):
        u = User.objects.all()[1]
        p = Poll.objects.all()[0]
        c1 = Choice.objects.create(poll=p,
                                   user=u,
                                   choice="Yes")

    def test_choice_deletion(self):
        c = Choice.objects.all()[0]
        c.delete()
        self.assertRaises(ObjectDoesNotExist, Choice.objects.get, id=c.id)

    def test_vote_creation(self):
        u = User.objects.all()[2]
        c = Choice.objects.all()[1]

        v = Vote.objects.create(user=u,
                                choice=c)

    def test_vote_deletion(self):
        v = Vote.objects.all()[0]
        v.delete()
        self.assertRaises(ObjectDoesNotExist, Vote.objects.get, id=v.id)


class PollTests(TestCase):
    fixtures = ['users.json',
                'polls.json',
                'choices.json',
                'votes.json']

    def test_poll_url_generation(self):
        p = Poll.objects.get(id=1)
        self.failUnlessEqual(p.get_absolute_url(),
                             reverse('molnet-polls-show-poll',
                                     kwargs={'year': p.published_at.year,
                                             'month': p.published_at.month,
                                             'day': p.published_at.day,
                                             'slug': "kittens-or-kaboodles"}))

    def test_number_of_votes(self):
        p = Poll.objects.get(id=1)
        self.failUnlessEqual(p.number_of_votes(), 3)


class ChoiceTests(TestCase):
    fixtures = ['users.json',
                'polls.json',
                'choices.json',
                'votes.json']

    def test_choices_with_votes(self):
        p = Poll.objects.get(id=1)
        choices_with_votes = Choice.objects \
                                   .get_choices_and_votes_for_poll(pollid=p)
        self.failUnlessEqual(len(choices_with_votes), 3)
        self.failUnlessEqual(choices_with_votes[0].num_votes, 2)
        self.failUnlessEqual(choices_with_votes[1].num_votes, 0)
        self.failUnlessEqual(choices_with_votes[2].num_votes, 1)


class PollUnauthorizedTests(TestCase):
    fixtures = ['users.json',
                'polls.json',
                'choices.json',
                'votes.json']

    def test_startpage_unauth(self):
        """ Check that the poll startpage renders. """

        response = self.client.get(reverse('molnet-polls-startpage'))
        self.failUnlessEqual(response.status_code, 200)

    def test_poll_views_unauth(self):
        """ Make sure all the views render. """

        polls = Poll.objects.exclude(status='DRAFT')
        for poll in polls:
            p_at = poll.published_at
            response = self.client.get(reverse('molnet-polls-show-poll',
                                               kwargs={'year': p_at.year,
                                                       'month': p_at.month,
                                                       'day': p_at.day,
                                                       'slug': poll.slug}))
            self.failUnlessEqual(response.status_code, 200)

    def test_create_poll_view_unauth(self):
        """ Make sure the create poll view redirects if not authorized. """

        response = self.client.get(reverse('molnet-polls-create-poll'))
        self.assertRedirects(response,
                             reverse('login') + "?next=" + \
                             reverse('molnet-polls-create-poll'),
                             status_code=302,
                             target_status_code=200)

    def test_edit_poll_view_unauth(self):
        """ Make sure the edit poll view redirects if not authorized. """

        p = Poll.objects.all()[1]
        response = self.client.get(reverse('molnet-polls-edit-poll',
                                           kwargs={'slug': p.slug}))
        self.assertRedirects(response,
                             reverse('login') + "?next=" + \
                             reverse('molnet-polls-edit-poll',
                                     kwargs={'slug': p.slug}),
                             status_code=302,
                             target_status_code=200)


class PollAuthorizedTests(TestCase):
    fixtures = ['users.json',
                'polls.json',
                'choices.json',
                'votes.json']

    def setUp(self):
        login = self.client.login(username='testclient', password='password')
        self.failUnless(login, 'Could not log in')

    def tearDown(self):
        self.client.logout()

    def test_startpage(self):
        """ Check that the poll startpage renders when logged in. """

        response = self.client.get(reverse('molnet-polls-startpage'))
        self.failUnlessEqual(response.status_code, 200)
        self.failUnlessEqual(response.context['user'].username, 'testclient')

    def test_poll_views(self):
        """ Make sure all the views render when logged in. """

        polls = Poll.objects.exclude(status='DRAFT')
        for poll in polls:
            p_at = poll.published_at
            response = self.client.get(reverse('molnet-polls-show-poll',
                                               kwargs={'year': p_at.year,
                                                       'month': p_at.month,
                                                       'day': p_at.day,
                                                       'slug': poll.slug}))
            self.failUnlessEqual(response.status_code, 200)
            self.failUnlessEqual(response.context['user'].username,
                                 'testclient')

    def test_create_poll_view(self):
        """ Make sure the create poll view renders when logged in. """

        response = self.client.get(reverse('molnet-polls-create-poll'))
        self.failUnlessEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'testclient')


class EditPollLoggedInAsNonOwnerTests(TestCase):
    fixtures = ['users.json',
                'polls.json',
                'choices.json',
                'votes.json']

    def setUp(self):
        # Log in as 'user'
        login = self.client.login(username='user', password='password')
        self.failUnless(login, 'Could not log in')

    def test_edit_poll_view_when_poll_not_owned_by_logged_in_user(self):
        """ Make sure the edit poll view prevents rendering the
        edit view when logged in as non-owner of poll.

        """
        # Try to render edit poll view for poll created by 'anotheruser'
        p = Poll.objects.get(id=2)
        response = self.client.get(reverse('molnet-polls-edit-poll',
                                           kwargs={'slug': p.slug}))
        self.failUnlessEqual(response.status_code, 403)

    def test_edit_poll_owned_by_other_user(self):
        """ Make sure the edit poll form does not accept input
        from a user that didn't create the form.

        """
        # Try to post update to own poll
        p = Poll.objects.get(id=2)
        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': p.slug}),
                                    {'poll': "Update",
                                     'poll-title': "Hello",
                                     'poll-description': "Hello World",
                                     'poll-allow_new_choices': True})
        self.failUnlessEqual(response.status_code, 403)

        p = Poll.objects.get(id=2)
        self.failIfEqual(p.title, "Hello")


class EditPollTests(TestCase):
    fixtures = ['users.json',
                'polls.json',
                'choices.json',
                'votes.json']

    def setUp(self):
        # Log in as 'user'
        login = self.client.login(username='user', password='password')
        self.failUnless(login, 'Could not log in')

    def test_edit_poll_view(self):
        """ Make sure the edit poll view renders when logged in as
        the user who created the poll. """

        # Should be able to render edit view for own poll
        p = Poll.objects.get(id=1)
        response = self.client.get(reverse('molnet-polls-edit-poll',
                                           kwargs={'slug': p.slug}))
        self.failUnlessEqual(response.status_code, 200)

    def test_edit_poll_by_form(self):
        """ Make sure the edit poll form works. """

        # Try to post update to own poll
        p = Poll.objects.get(id=1)
        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': p.slug}),
                                    {'poll': "Update",
                                     'poll-title': "Hello",
                                     'poll-description': "Hello World",
                                     'poll-allow_new_choices': True})
        self.assertRedirects(response,
                             reverse('molnet-polls-edit-poll',
                                     kwargs={'slug': p.slug}),
                             status_code=302,
                             target_status_code=200)

        p = Poll.objects.get(id=1)
        self.failUnlessEqual(p.title, "Hello")

    def test_delete_poll_by_form(self):
        """ Delete own poll. """

        p = Poll.objects.get(id=1)
        choices = Choice.objects.filter(poll=p.id).values_list('id', flat=True)
        self.failUnless(choices)
        votes = Vote.objects.filter(choice__in=choices)
        self.failUnless(votes)

        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': p.slug}),
                                    {'delete': "Delete"})
        self.assertRedirects(response, reverse('molnet-polls-startpage'))
        self.assertRaises(ObjectDoesNotExist, Poll.objects.get, id=p.id)

        # Verify that choices have been cascade deleted
        choices_post = Choice.objects.filter(poll=p.id) \
                                     .values_list('id', flat=True)
        self.failIf(choices_post)

        # All votes linked to the original choices should have been
        # cascade deleted
        votes_post = Vote.objects.filter(choice__in=choices)
        self.failIf(votes_post)

    def test_unpublish_published_poll_by_form(self):
        """ Unpublished own published poll. """

        p = Poll.objects.filter(user__username='user') \
                        .filter(status='PUBLISHED')[0]

        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': p.slug}),
                                    {'unpublish': "Unpublish poll"})
        self.assertRedirects(response,
                             reverse('molnet-polls-edit-poll',
                                     kwargs={'slug': p.slug}),
                             status_code=302,
                             target_status_code=200)

        p = Poll.objects.get(id=1)
        self.failUnless(p.is_draft())

    def test_unpublish_closed_poll_by_form(self):
        """ Unpublish own closed poll. """

        p = Poll.objects.filter(user__username='user') \
                        .filter(status='CLOSED')[0]

        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': p.slug}),
                                    {'unpublish': "Unpublish poll"})
        self.assertRedirects(response,
                             reverse('molnet-polls-edit-poll',
                                     kwargs={'slug': p.slug}),
                             status_code=302,
                             target_status_code=200)

        p = Poll.objects.get(id=p.id)
        self.failUnless(p.is_draft())

    def test_publish_poll_by_form(self):
        """ Publish own poll. """

        p = Poll.objects.filter(user__username='user') \
                        .filter(status='DRAFT')[0]

        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': p.slug}),
                                    {'publish': "Publish poll"})
        self.assertRedirects(response,
                             reverse('molnet-polls-edit-poll',
                                     kwargs={'slug': p.slug}),
                             status_code=302,
                             target_status_code=200)

        p = Poll.objects.get(id=1)
        self.failUnless(p.is_published())
        self.failIf(p.is_closed())

    def test_close_poll_by_form(self):
        """ Close own poll. """

        p = Poll.objects.filter(user__username='user') \
                        .filter(status='PUBLISHED')[0]

        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': p.slug}),
                                    {'close': "Close poll"})
        self.assertRedirects(response,
                             reverse('molnet-polls-edit-poll',
                                     kwargs={'slug': p.slug}),
                             status_code=302,
                             target_status_code=200)

        p = Poll.objects.get(id=1)
        self.failUnless(p.is_closed())

    def test_reopen_poll_by_form(self):
        """ Re-open own closed poll. """

        p = Poll.objects.filter(user__username='user') \
                        .filter(status='CLOSED')[0]

        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': p.slug}),
                                    {'re-open': "Re-open poll"})
        self.assertRedirects(response,
                             reverse('molnet-polls-edit-poll',
                                     kwargs={'slug': p.slug}),
                             status_code=302,
                             target_status_code=200)

        p = Poll.objects.get(id=1)
        self.failUnless(p.is_published())
        self.failIf(p.is_closed())

    def test_add_choice_by_form(self):
        """ Add a choice to own poll. """

        p = Poll.objects.get(id=1)
        new_choice = "New choice"

        # Verify that new choice does not already exist
        c = Choice.objects.filter(poll=p.id).filter(choice=new_choice)
        self.failIf(c)

        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': p.slug}),
                                    {'choice': "Add choice",
                                     'choice-choice': new_choice})
        self.assertRedirects(response,
                             reverse('molnet-polls-edit-poll',
                                     kwargs={'slug': p.slug}))

        # Verify new choice exists
        c = Choice.objects.filter(poll=p.id).filter(choice=new_choice)
        self.failUnless(c)

    def test_delete_choice_by_form(self):
        """ Delete a choice from own poll. """

        poll = Poll.objects.get(id=1)

        # Get a choice
        choice = Choice.objects.filter(poll=poll.id)[0]

        # Get votes for choice
        votes = Vote.objects.filter(choice=choice)
        self.failUnless(votes)

        response = self.client.post(reverse('molnet-polls-edit-poll',
                                            kwargs={'slug': poll.slug}),
                                    {'delete-choice': "Delete choice",
                                     'choice-id': choice.id})
        self.assertRedirects(response, reverse('molnet-polls-edit-poll',
                                               kwargs={'slug': poll.slug}))

        # Verify choice has been deleted
        self.assertRaises(ObjectDoesNotExist, Choice.objects.get, id=choice.id)

        # All votes linked to the original choices should have been
        # cascade deleted
        votes_post = Vote.objects.filter(choice=choice)
        self.failIf(votes_post)




#     def test_backups_view_unauth(self):
#         s = System.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups',
#                                            kwargs={'systemid': s.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backups_extended_view_unauth(self):
#         s = System.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-extended-view',
#                                            kwargs={'systemid': s.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backup_create_view_unauth(self):
#         """Verify that backup create view redirects to index view if
#            not authorized."""
#
#         s = System.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-create-backup',
#                                            kwargs={'systemid': s.id}))
#         self.assertRedirects(response,
#                              reverse('login') + "?next=" + \
#                                 reverse('bakelit-backups-create-backup',
#                                         kwargs={'systemid': s.id}),
#                              status_code=302,
#                              target_status_code=200)
#
#     def test_backup_create_form_view_unauth(self):
#         """Make sure create backup view redirects if not authorized."""
#
#         s = System.objects.all()[0]
#         response = self.client.post(reverse('bakelit-backups-create-backup',
#                                             kwargs={'systemid': s.id}),
#                                     {'name': 'Test'})
#         self.assertRedirects(response,
#                              reverse('login') + "?next=" + \
#                              reverse('bakelit-backups-create-backup',
#                                      kwargs={'systemid': s.id}),
#                              status_code=302,
#                              target_status_code=200)
#
#     def test_backup_read_view_unauth(self):
#         """Verify that backup details view returns HTTP 200 OK."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-backup-details',
#                                            kwargs={'systemid': s.id,
#                                                    'backupid': b.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backup_update_view_unauth(self):
#         """Verify that backup update view redirects to index view if
#            not authorized."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-update-backup',
#                                            kwargs={'systemid': s.id,
#                                                    'backupid': b.id}))
#         self.assertRedirects(response,
#                              reverse('login') + "?next=" + \
#                                 reverse('bakelit-backups-update-backup',
#                                         kwargs={'systemid': s.id,
#                                                 'backupid': b.id}),
#                              status_code=302,
#                              target_status_code=200)
#
#     def test_backup_update_form_view_unauth(self):
#         """Verify that backup update view redirects to index view if
#            not authorized."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.post(
#                 reverse('bakelit-backups-update-backup-method-put',
#                         kwargs={'systemid': s.id,
#                                 'backupid': b.id}),
#                         {'name': 'Long term DAT-backup'})
#         self.assertRedirects(
#             response,
#             reverse('login') + "?next=" + \
#                 urlquote(reverse('bakelit-backups-update-backup-method-put',
#                                  kwargs={'systemid': s.id,
#                                          'backupid': b.id})),
#             status_code=302,
#             target_status_code=200)
#
#     def test_backup_delete_view_unauth(self):
#         """Verify that backup delete view redirects to index view if
#            not authorized."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-delete-backup',
#                                            kwargs={'systemid': s.id,
#                                                    'backupid': b.id}))
#         self.assertRedirects(response,
#                              reverse('login') + "?next=" + \
#                                 reverse('bakelit-backups-delete-backup',
#                                         kwargs={'systemid': s.id,
#                                                 'backupid': b.id}),
#                              status_code=302,
#                              target_status_code=200)
#
#     def test_backup_delete_form_view_unauth(self):
#         """Make sure delete backup view redirects if not authorized."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.post(
#                 reverse('bakelit-backups-delete-backup-method-delete',
#                         kwargs={'systemid': s.id,
#                                 'backupid': b.id}),
#                                     {})
#         self.assertRedirects(
#             response,
#             reverse('login') + "?next=" + \
#                 urlquote(reverse('bakelit-backups-delete-backup-method-delete',
#                                  kwargs={'systemid': s.id,
#                                          'backupid': b.id})),
#             status_code=302,
#             target_status_code=200)
#
#     def test_toggle_backup_status_unauth(self):
#         """Make sure the toggle status view redirects if not authorized."""
#
#         b = Backup.objects.all()[0]
#         response = self.client.post(
#                 reverse('bakelit-backups-toggle-backup-status-method-put',
#                         kwargs={'systemid': b.system.id,
#                                 'backupid': b.id}))
#         self.assertRedirects(
#             response,
#             reverse('login') + "?next=" + \
#                 urlquote(reverse('bakelit-backups-toggle-backup-status-method-put',
#                          kwargs={'systemid': b.system.id,
#                                  'backupid': b.id})),
#                              status_code=302,
#                              target_status_code=200)
#
#     def test_okay_all_backup_status_view_unauth(self):
#         """Make sure the okay all statuses view redirects if not
#            authorized.
#
#         """
#
#         s = System.objects.all()[0]
#         response = self.client.post(reverse('bakelit-backups-okay-all-backups',
#                                             kwargs={'systemid': s.id}))
#         self.assertRedirects(
#                 response,
#                 reverse('login') + "?next=" + \
#                         urlquote(reverse('bakelit-backups-okay-all-backups',
#                                          kwargs={'systemid': s.id})),
#                 status_code=302,
#                 target_status_code=200)
#
#     def test_okay_all_backup_status_unauth(self):
#         """Make sure the okay all statuses form redirects if not
#         authorized.
#
#         """
#
#         backups = Backup.objects.exclude(status__exact="OK")
#         self.assertTrue(len(backups) > 0)
#         response = self.client.post(
#                 reverse('bakelit-backups-okay-all-backups-method-put',
#                         kwargs={'systemid': backups[0].system.id}))
#         self.assertRedirects(
#                 response,
#                 reverse('login') + "?next=" + \
#                     urlquote(reverse('bakelit-backups-okay-all-backups-method-put',
#                                      kwargs={'systemid': backups[0].system.id})),
#                 status_code=302,
#                 target_status_code=200)
#
# class BackupAuthorizedTests(TestCase):
#     fixtures = ['categories.json',
#                 'systems.json',
#                 'users.json',
#                 'backups.json']
#
#     def setUp(self):
#         login = self.client.login(username='testclient', password='password')
#         self.failUnless(login, 'Could not log in')
#
#     def test_backup_index_view(self):
#         s = System.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups',
#                                            kwargs={'systemid': s.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backup_index_extended_view(self):
#         s = System.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-extended-view',
#                                            kwargs={'systemid': s.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backups_view_edit_mode(self):
#         """Verify that backup index view in edit mode redirects to
#            index view if not authorized."""
#
#         s = System.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups',
#                                            kwargs={'systemid': s.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backup_create_view(self):
#         """Verify that create view returns HTTP 200 OK."""
#
#         s = System.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-create-backup',
#                                            kwargs={'systemid': s.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backup_create_via_incomplete_form(self):
#         """Make sure create backup view does not accept incomplete forms."""
#
#         s = System.objects.all()[0]
#         response = self.client.post(reverse('bakelit-backups-create-backup',
#                                             kwargs={'systemid': s.id}),
#                                     {})
#         self.assertFormError(response,
#                              'form',
#                              'name',
#                              ugettext("This field is required."))
#
#     def test_backup_create_via_form(self):
#         """Verify that a backup can be created through form."""
#
#         s = System.objects.all()[0]
#
#         name = "Production server, daily differential"
#         self.assertRaises(Backup.DoesNotExist,
#                           Backup.objects.get,
#                           name=name)
#
#         response = self.client.post(reverse('bakelit-backups-create-backup',
#                                             kwargs={'systemid': s.id}),
#                                     {'name': name,
#                                      'restore_duration_measured': 'NO',
#                                      'status': 'OK'})
#         b = Backup.objects.get(name=name)
#         self.assertRedirects(response, reverse('bakelit-backups',
#                                                kwargs={'systemid': s.id}),
#                             status_code=302, target_status_code=200)
#
#     def test_backup_read_view(self):
#         """Verify that a backup details view returns HTTP 200 OK."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-backup-details',
#                                            kwargs={'systemid': s.id,
#                                                    'backupid': b.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backup_update_view(self):
#         """Verify that a backup update view returns HTTP 200 OK."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-update-backup',
#                                            kwargs={'systemid': s.id,
#                                                    'backupid': b.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backup_update_via_incomplete_form(self):
#         """Make sure update backup view does not accept incomplete forms."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.post(
#                 reverse('bakelit-backups-update-backup-method-put',
#                         kwargs={'systemid': s.id,
#                                 'backupid': b.id}),
#                 {'note': "Test"})
#         self.assertFormError(response,
#                              'form',
#                              'name',
#                              ugettext("This field is required."))
#
#     def test_backup_update_via_form(self):
#         """Update a backup through form."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.post(
#                 reverse('bakelit-backups-update-backup-method-put',
#                         kwargs={'systemid': s.id,
#                                 'backupid': b.id}),
#                 {'name': 'Development',
#                  'restore_duration_measured': 'NO',
#                  'status': 'PENDING'})
#         self.assertRedirects(
#                 response,
#                 reverse('bakelit-backups-backup-details',
#                         kwargs={'systemid': s.id,
#                                 'backupid': b.id}),
#                 status_code=302,
#                 target_status_code=200)
#
#     def test_backup_delete_view(self):
#         """Verify that a backup delete view returns HTTP 200 OK."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.get(reverse('bakelit-backups-delete-backup',
#                                            kwargs={'systemid': s.id,
#                                                    'backupid': b.id}))
#         self.failUnlessEqual(response.status_code, 200)
#
#     def test_backup_delete_form_no_confirm_view(self):
#         """Try to delete a backup through form to get confirmation request."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.post(
#                 reverse('bakelit-backups-delete-backup-method-delete',
#                         kwargs={'systemid': s.id,
#                                 'backupid': b.id}),
#                 {})
#         self.assertContains(response,
#                             "Please confirm backup deletion",
#                             status_code=200)
#
#     def test_backup_delete_form_view(self):
#         """Delete a backup through form."""
#
#         s = System.objects.all()[0]
#         b = Backup.objects.all()[0]
#         response = self.client.post(
#                 reverse('bakelit-backups-delete-backup-method-delete',
#                         kwargs={'systemid': s.id,
#                                 'backupid': b.id}),
#                 {'confirm': True})
#         self.assertRedirects(response,
#                              reverse('bakelit-backups',
#                                      kwargs={'systemid': s.id}),
#                              status_code=302,
#                              target_status_code=200)
#
#     def test_toggle_backup_status(self):
#         """Make sure backup status can be toggled."""
#
#         b = Backup.objects.filter(status__exact='PENDING')[0]
#
#         # Toggle PENDING -> OK
#         response = self.client.post(
#                 reverse('bakelit-backups-toggle-backup-status-method-put',
#                         kwargs={'systemid': b.system.id,
#                                 'backupid': b.id}))
#         self.assertRedirects(response,
#                              reverse('bakelit-backups',
#                                      kwargs={'systemid': b.system.id}),
#                              status_code=302,
#                              target_status_code=200)
#         b2 = Backup.objects.get(id=b.id)
#         self.assertEqual(b2.status, "OK")
#
#         # Toggle OK -> NOT_OK
#         response = self.client.post(
#                 reverse('bakelit-backups-toggle-backup-status-method-put',
#                         kwargs={'systemid': b.system.id,
#                                 'backupid': b.id}))
#         b2 = Backup.objects.get(id=b.id)
#         self.assertEqual(b2.status, "NOT_OK")
#
#         # Toggle NOT_OK -> OK
#         response = self.client.post(
#                 reverse('bakelit-backups-toggle-backup-status-method-put',
#                         kwargs={'systemid': b.system.id,
#                                 'backupid': b.id}))
#         b2 = Backup.objects.get(id=b.id)
#         self.assertEqual(b2.status, "OK")
#
#     def test_okay_all_backup_status(self):
#         """All statuses should be set to OK when "okaying all"."""
#
#         backups = Backup.objects.exclude(status__exact="OK")
#         self.assertTrue(len(backups) > 0)
#         response = self.client.post(
#                 reverse('bakelit-backups-okay-all-backups-method-put',
#                         kwargs={'systemid': backups[0].system.id}))
#         self.assertRedirects(response,
#                              reverse('bakelit-backups',
#                                      kwargs={'systemid': backups[0].system.id}),
#                              status_code=302,
#                              target_status_code=200)
#         backups = Backup.objects.filter(system=backups[0].system.id) \
#                                 .exclude(status__exact="OK")
#         self.assertTrue(len(backups) == 0)
#
#     def test_okay_all_backup_status_view(self):
#         """Make sure okay all statuses view returns HTTP 200 OK."""
#
#         s = System.objects.all()[0]
#         response = self.client.post(reverse('bakelit-backups-okay-all-backups',
#                                             kwargs={'systemid': s.id}))
#         self.failUnlessEqual(response.status_code, 200)

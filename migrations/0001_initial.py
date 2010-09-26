# -*- coding: utf-8 -*-

from south.db import db
from django.db import models
from molnet.polls.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Poll'
        db.create_table('polls_poll', (
            ('id', orm['polls.Poll:id']),
            ('slug', orm['polls.Poll:slug']),
            ('user', orm['polls.Poll:user']),
            ('title', orm['polls.Poll:title']),
            ('description', orm['polls.Poll:description']),
            ('allow_new_choices', orm['polls.Poll:allow_new_choices']),
            ('status', orm['polls.Poll:status']),
            ('published_at', orm['polls.Poll:published_at']),
            ('date_created', orm['polls.Poll:date_created']),
            ('date_modified', orm['polls.Poll:date_modified']),
        ))
        db.send_create_signal('polls', ['Poll'])
        
        # Adding model 'Vote'
        db.create_table('polls_vote', (
            ('id', orm['polls.Vote:id']),
            ('user', orm['polls.Vote:user']),
            ('choice', orm['polls.Vote:choice']),
            ('date_created', orm['polls.Vote:date_created']),
            ('date_modified', orm['polls.Vote:date_modified']),
        ))
        db.send_create_signal('polls', ['Vote'])
        
        # Adding model 'Choice'
        db.create_table('polls_choice', (
            ('id', orm['polls.Choice:id']),
            ('poll', orm['polls.Choice:poll']),
            ('choice', orm['polls.Choice:choice']),
            ('user', orm['polls.Choice:user']),
            ('date_created', orm['polls.Choice:date_created']),
        ))
        db.send_create_signal('polls', ['Choice'])
        
        # Creating unique_together for [poll, choice] on Choice.
        db.create_unique('polls_choice', ['poll_id', 'choice'])
        
    
    
    def backwards(self, orm):
        
        # Deleting unique_together for [poll, choice] on Choice.
        db.delete_unique('polls_choice', ['poll_id', 'choice'])
        
        # Deleting model 'Poll'
        db.delete_table('polls_poll')
        
        # Deleting model 'Vote'
        db.delete_table('polls_vote')
        
        # Deleting model 'Choice'
        db.delete_table('polls_choice')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'polls.choice': {
            'Meta': {'unique_together': "(('poll', 'choice'),)"},
            'choice': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'poll': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.Poll']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'polls.poll': {
            'allow_new_choices': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'published_at': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'slug': ('autoslug.fields.AutoSlugField', [], {'unique_with': '()', 'max_length': '80', 'blank': 'True', 'unique': 'True', 'populate_from': 'None', 'db_index': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'DRAFT'", 'max_length': '32', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '140', 'unique': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'polls.vote': {
            'choice': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['polls.Choice']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'date_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['polls']

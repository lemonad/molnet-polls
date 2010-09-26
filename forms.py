# -*- coding: utf-8 -*-
from django.forms import (BooleanField, CharField, ChoiceField, Form,
                          ModelForm, MultiValueField, MultiWidget, RadioSelect,
                          Textarea, TextInput, ValidationError)
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _

from models import Choice, Poll, Vote


class ModelFormRequestUser(ModelForm):
    def __init__(self, request, *args, **varargs):
        self.user = request.user
        super(ModelFormRequestUser, self).__init__(*args, **varargs)

    def save(self, commit=True):
        obj = super(ModelFormRequestUser, self).save(commit=False)
        obj.user = self.user
        if commit:
            obj.save()
            self.save_m2m() # Be careful with ModelForms + commit=False
        return obj


class ChoiceWithOtherRenderer(RadioSelect.renderer):
    """ RadioFieldRenderer that renders its last choice with a
    placeholder.

    See http://djangosnippets.org/snippets/863/ (and perhaps also
    http://djangosnippets.org/snippets/1377/)

    """
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

class ChoiceWithOtherWidget(MultiWidget):
    """ MultiWidget for use with ChoiceWithOtherField.

    See http://djangosnippets.org/snippets/863/ (and perhaps also
    http://djangosnippets.org/snippets/1377/)

    """
    def __init__(self, choices, other_widget):
        widgets = [RadioSelect(choices=choices,
                               renderer=ChoiceWithOtherRenderer),
                   other_widget]
        super(ChoiceWithOtherWidget, self).__init__(widgets)

    def decompress(self, value):
        if not value:
            return [None, None]
        return value

    def format_output(self, rendered_widgets):
        """ Format the output by substituting the "other" choice into
        the first widget.

        """
        return rendered_widgets[0] % rendered_widgets[1]

class ChoiceWithOtherField(MultiValueField):
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

    See http://djangosnippets.org/snippets/863/ (and perhaps also
    http://djangosnippets.org/snippets/1377/)

    """
    def __init__(self, *args, **kwargs):
        other_field = kwargs.pop('other_field', None)
        if other_field is None:
            other_field = CharField(required=False)
        fields = [ChoiceField(widget=RadioSelect(renderer=
                                                     ChoiceWithOtherRenderer),
                              *args,
                              **kwargs),
                  other_field]
        widget = ChoiceWithOtherWidget(choices=kwargs['choices'],
                                       other_widget=other_field.widget)
        kwargs.pop('choices')
        self._was_required = kwargs.pop('required', True)
        kwargs['required'] = False
        super(ChoiceWithOtherField, self).__init__(widget=widget,
                                                   fields=fields,
                                                   *args,
                                                   **kwargs)

    def clean(self, value):
        # MultiValueField turns off the "required" field for all the fields.
        # It prevents us from requiring the manual entry. This implements
        # that.
        if self._was_required:
            #if value and value[1] and value[0] != self.fields[0].choices[-1][0]:
            #    value[0] = self.fields[0].choices[-1][0]
            if value and value[0] == self.fields[0].choices[-1][0]:
                manual_choice = value[1]
                if not manual_choice:
                    raise ValidationError(self.error_messages['required'])
        return super(ChoiceWithOtherField, self).clean(value)

    def compress(self, value):
        if self._was_required and not value or value[0] in (None, ''):
            raise ValidationError(self.error_messages['required'])
        if not value:
            return [None, u'']
        return (value[0], value[1] if force_unicode(value[0]) == \
                force_unicode(self.fields[0].choices[-1][0]) else u'')


class PollVotingForm(Form):
    """ Form for voting on polls. """

    def __init__(self, *args, **kwargs):
            choices = kwargs.pop('choices')
            allow_new_choices = kwargs.pop('allow_new_choices')
            super(PollVotingForm, self).__init__(*args, **kwargs)

            if allow_new_choices:
                choices.append(('OTHER', 'Other'))
                self.fields['choices'] = \
                        ChoiceWithOtherField(choices=choices,
                                             required=True)
            else:
                self.fields['choices'] = \
                        ChoiceField(choices=choices,
                                    widget=RadioSelect,
                                    required=True)


class PollForm(ModelFormRequestUser):
    """ Form for adding and editing polls. """

    class Meta:
        model = Poll
        fields = ['title', 'description', 'allow_new_choices']
        # Django 1.2 only
        # widgets = {'title': TextInput(attrs={'class': 'span-12 last input'}),
        #           'description': Textarea(attrs={'class': 'span-12 last input'}),}

    def __init__(self, *args, **kwargs):
        super(PollForm, self).__init__(*args, **kwargs)
        self.fields['title'].widget.attrs['class'] = 'span-12 last input'
        self.fields['description'].widget.attrs['class'] = 'span-12 last input'
        self.fields['description'].widget.attrs['id'] = 'wmd-input'

class ChoiceForm(ModelFormRequestUser):
    """ Form for adding and editing poll choices. """

    def __init__(self, request, poll, *args, **varargs):
        self.poll = poll
        super(ChoiceForm, self).__init__(request, *args, **varargs)
        self.fields['choice'].widget.attrs['class'] = 'span-12 last input'

    def save(self, commit=True):
        obj = super(ChoiceForm, self).save(commit=False)
        obj.poll = self.poll
        if commit:
            obj.save()
            self.save_m2m() # Be careful with ModelForms + commit=False
        return obj

    class Meta:
        model = Choice
        fields = ['choice']
        # Django 1.2 only
        # widgets = {'choice': TextInput(attrs={'class': 'span-12 input',
        #                                       'size': '255'}),}

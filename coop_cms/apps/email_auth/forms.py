# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth import authenticate
from django.utils.translation import ugettext as _

class EmailAuthForm(forms.Form):
    email = forms.EmailField(required=True, label=_(u"Email"))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        super(EmailAuthForm, self).__init__(*args, **kwargs)
        
    def _authenticate(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        error_messages = {
            'invalid_login': _("Please enter a correct %(email)s and password. "
                               "Note that both fields may be case-sensitive."),
        }
        
        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    error_messages['invalid_login'],
                    code='invalid_login',
                    params={'email': _(u"email")},
                )
    
    def get_user(self):
        return self.user_cache
     
    def clean(self):
        self._authenticate()
        return self.cleaned_data
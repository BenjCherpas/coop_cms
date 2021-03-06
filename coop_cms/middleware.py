# -*- coding: utf-8 -*-
""""""

from __future__ import unicode_literals

from django.core.exceptions import PermissionDenied
try:
    from django.urls import NoReverseMatch
except:
    from django.core.urlresolvers import NoReverseMatch
from django.contrib.auth.views import redirect_to_login

from coop_cms.moves import MiddlewareMixin, is_authenticated
from coop_cms.utils import get_login_url


class PermissionsMiddleware(MiddlewareMixin):
    """Handle permission"""

    def process_exception(self, request, exception):
        """manage exception"""

        if isinstance(exception, PermissionDenied) and (not is_authenticated(request.user)):
            try:
                login_url = get_login_url()
            except NoReverseMatch:
                login_url = None
            return redirect_to_login(request.path, login_url)

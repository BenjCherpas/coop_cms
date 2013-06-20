# -*- coding: utf-8 -*-

from django.views.generic.list import ListView as DjangoListView
from django.views.generic.base import View
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from djaloha import utils as djaloha_utils
from django.contrib.messages.api import success as success_message
from django.contrib.messages.api import error as error_message
from django.utils.translation import ugettext as _
from django.http import HttpResponse, Http404, HttpResponseRedirect, HttpResponseForbidden
from django.core.exceptions import ValidationError, PermissionDenied
import logging
logger = logging.getLogger("coop_cms")

class ListView(DjangoListView):
    ordering = ''
    
    def get_context_data(self, **kwargs):
        context = super(ListView, self).get_context_data(**kwargs)
        context['model'] = self.model
        return context
    
    def get_queryset(self):
        if self.ordering:
            if type(self.ordering) in (list, tuple):
                return self.model.objects.order_by(*self.ordering)
            else:
                return self.model.objects.order_by(self.ordering)
        else:
            return self.model.objects.all()


class EditableObjectView(View):
    model = None
    template_name = ""
    form_class = None
    field_lookup = "pk"
    edit_mode = False
    varname = "object"
    
    def __init__(self, *args, **kwargs):
        super(EditableObjectView, self).__init__(*args, **kwargs)
    
    def can_edit_object(self):
        can_edit_perm = 'can_edit_{0}'.format(self.varname)
        return self.request.user.is_authenticated() and self.request.user.has_perm(can_edit_perm, self.object)
        
    def can_view_object(self):
        if self.edit_mode:
            return self.can_edit_object()
        else:
            can_view_perm = 'can_view_{0}'.format(self.varname)
            return self.request.user.has_perm(can_view_perm, self.object)
    
    def get_object(self):
        lookup = {self.field_lookup: self.kwargs[self.field_lookup]}
        return get_object_or_404(self.model, **lookup)
    
    def get_context_data(self):
        return {
            'form': self.form if self.edit_mode else None,
            'editable': self.can_edit_object(),
            'edit_mode': self.edit_mode,
            'title': getattr(self.object, 'title', unicode(self.object)),
            self.varname: self.object,
        }
        
    def get_template(self):
        return self.template_name
    
    def handle_object_not_found(self):
        pass
    
    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            return_this = self.handle_object_not_found()
            if return_this:
                return return_this
            else:
                raise
        
        if not self.can_view_object():
            logger.error("PermissionDenied")
            error_message(request, _(u'Permission denied'))
            raise PermissionDenied
        
        self.form = self.form_class(instance=self.object)
        
        return render_to_response(
            self.get_template(),
            self.get_context_data(),
            context_instance=RequestContext(request)
        )
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        if not self.can_edit_object():
            logger.error("PermissionDenied")
            error_message(request, _(u'Permission denied'))
            raise PermissionDenied
        
        self.form = self.form_class(request.POST, request.FILES, instance=self.object)

        forms_args = djaloha_utils.extract_forms_args(request.POST)
        djaloha_forms = djaloha_utils.make_forms(forms_args, request.POST)

        if self.form.is_valid() and all([f.is_valid() for f in djaloha_forms]):
            self.object = self.form.save()
            
            if djaloha_forms:
                [f.save() for f in djaloha_forms]

            success_message(request, _(u'The object has been saved properly'))

            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            error_text = u'<br />'.join([unicode(f.errors) for f in [self.form]+djaloha_forms if f.errors])
            error_message(request, _(u'An error occured: {0}'.format(error_text)))
            logger.debug("error: error_text")
    
        return render_to_response(
            self.get_template(),
            self.get_context_data(),
            context_instance=RequestContext(request)
        )


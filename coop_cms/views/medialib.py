# -*- coding: utf-8 -*-
"""media library"""

import itertools
import json
import mimetypes
import os.path
import unicodedata

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import get_template
from django.utils.html import mark_safe, escapejs

from coop_cms import forms
from coop_cms.logger import logger
from coop_cms import models


def _get_photologue_media(request):
    """get photologue media"""
    #Only if django-photologue is installed
    if "photologue" in settings.INSTALLED_APPS:
        from photologue.models import Photo, Gallery
        gallery_filter = request.GET.get('gallery_filter', 0)
        queryset = Photo.objects.all().order_by("-date_added")
        if gallery_filter:
            queryset = queryset.filter(galleries__id=gallery_filter)

        context = {
            'media_url': reverse('coop_cms_media_photologue'),
            'media_slide_template': 'coop_cms/medialib/slide_photologue_content.html',
            'gallery_filter': int(gallery_filter),
            'galleries': Gallery.objects.all(),
        }
        return queryset, context
    else:
        raise Http404


@login_required
def show_media(request, media_type):
    """show media library"""
    try:
        if not request.user.is_staff:
            raise PermissionDenied

        try:
            page = int(request.GET.get('page', 0) or 0)
        except ValueError:
            page = 1
        is_ajax = page > 0
        media_filter = request.GET.get('media_filter', 0)
        skip_media_filter = False

        if request.session.get("coop_cms_media_doc", False):
            #force the doc
            media_type = 'document'
            del request.session["coop_cms_media_doc"]

        if media_type == 'image':
            queryset = models.Image.objects.all().order_by("ordering", "-created")
            context = {
                'media_url': reverse('coop_cms_media_images'),
                'media_slide_template': 'coop_cms/medialib/slide_images_content.html',
            }

        elif media_type == 'photologue':
            queryset, context = _get_photologue_media(request)
            skip_media_filter = True

        else:
            media_type = "document"
            queryset = models.Document.objects.all().order_by("ordering", "-created")
            context = {
                'media_url': reverse('coop_cms_media_documents'),
                'media_slide_template': 'coop_cms/medialib/slide_docs_content.html',
            }

        context['is_ajax'] = is_ajax
        context['media_type'] = media_type

        if not skip_media_filter:
            # list of lists of media_filters
            media_filters = [media.filters.all() for media in queryset.all()]
            #flat list of media_filters
            media_filters = itertools.chain(*media_filters)
            #flat list of unique media filters sorted by alphabetical order (ignore case)
            context['media_filters'] = sorted(
                list(set(media_filters)), key=lambda mf: mf.name.upper()
            )

            if int(media_filter):
                queryset = queryset.filter(filters__id=media_filter)
                context['media_filter'] = int(media_filter)

        paginator = Paginator(queryset, 12)
        try:
            items = paginator.page(page or 1)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            items = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            items = paginator.page(paginator.num_pages)

        context[media_type+'s'] = items
        context['pages'] = paginator

        context['pages_count'] = xrange(paginator.count)
        context["allow_photologue"] = "photologue" in settings.INSTALLED_APPS

        template = get_template('coop_cms/medialib/slide_base.html')
        html = template.render(RequestContext(request, context))

        if is_ajax:
            data = {
                'html': html,
                'media_type': media_type,
                'media_url': context["media_url"],
            }
            return HttpResponse(json.dumps(data), content_type="application/json")
        else:
            return HttpResponse(html)
    except Exception:
        logger.exception("show_media")
        raise


@login_required
def upload_image(request):
    """upload image"""

    try:
        if not request.user.has_perm("coop_cms.add_image"):
            raise PermissionDenied()

        if request.method == "POST":
            form = forms.AddImageForm(request.POST, request.FILES)
            if form.is_valid():
                src = form.cleaned_data['image']
                description = form.cleaned_data['descr']
                if not description:
                    description = os.path.splitext(src.name)[0]
                image = models.Image(name=description)
                image.size = form.cleaned_data["size"]
                image.file.save(src.name, src)
                image.save()

                filters = form.cleaned_data['filters']
                if filters:
                    image.filters.add(*filters)
                    image.save()

                return HttpResponse("close_popup_and_media_slide")
        else:
            form = forms.AddImageForm()

        return render_to_response(
            'coop_cms/popup_upload_image.html',
            {
                'form': form,
            },
            context_instance=RequestContext(request)
        )
    except Exception:
        logger.exception("upload_image")
        raise


@login_required
def upload_doc(request):
    """upload document"""
    try:
        if not request.user.has_perm("coop_cms.add_document"):
            raise PermissionDenied()

        if request.method == "POST":
            form = forms.AddDocForm(request.POST, request.FILES)
            if form.is_valid():
                doc = form.save()
                if not doc.name:
                    doc.name = os.path.splitext(os.path.basename(doc.file.name))[0]
                    doc.save()

                request.session["coop_cms_media_doc"] = True

                return HttpResponse("close_popup_and_media_slide")
        else:
            form = forms.AddDocForm()

        return render_to_response(
            'coop_cms/popup_upload_doc.html',
            locals(),
            context_instance=RequestContext(request)
        )
    except Exception:
        logger.exception("upload_doc")
        raise


@login_required
def download_doc(request, doc_id):
    """download a doc"""
    doc = get_object_or_404(models.Document, id=doc_id)
    if not request.user.has_perm('can_download_file', doc):
        raise PermissionDenied

    if 'filetransfers' in settings.INSTALLED_APPS:
        from filetransfers.api import serve_file # pylint: disable=F0401
        return serve_file(request, doc.file)
    else:
        #legacy version just kept for compatibility if filetransfers is not installed
        logger.warning("install django-filetransfers for better download support")
        the_file = doc.file
        the_file.open('rb')
        wrapper = FileWrapper(the_file)
        mime_type = mimetypes.guess_type(the_file.name)[0]
        if not mime_type:
            mime_type = u'application/octet-stream'
        response = HttpResponse(wrapper, content_type=mime_type)
        response['Content-Length'] = the_file.size
        filename = unicodedata.normalize('NFKD', os.path.split(the_file.name)[1]).encode("utf8", 'ignore')
        filename = filename.replace(' ', '-')
        response['Content-Disposition'] = 'attachment; filename={0}'.format(filename)
        return response
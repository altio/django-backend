# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.views.generic import base

from ...template.response import TemplateResponse
from ...utils import redirect_to_url

__all__ = 'BackendMixin', 'DispatchMixin', 'AppPermissionsMixin', 'AppMixin', \
    'View', 'TemplateView', 'AppView', 'AppTemplateView', 'BackendTemplateMixin'


class DispatchMixin(object):
    """
    HARD OVERRIDE of View's dispatch behavior.
    """

    def get_handler(self, request, *args, **kwargs):
        """
        get_handler will return None to indicate "proceed with the normal
        method handler"
        """

        return None

    def handle_common(self, handler, request, *args, **kwargs):
        """
        Once a handler has been resolved and the the method is confirmed to be
        allowed, perform common work and do any validation needed.
        Return the handler passed or an alternate, as appropriate.
        """

        return handler

    def dispatch(self, request, *args, **kwargs):
        """ HARD OVERRIDE OF View """
        handler = self.get_handler(request, *args, **kwargs)

        # normal behavior
        if handler is None:
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), None)
        if handler is None:
            handler = self.http_method_not_allowed

        # common work moment before dispatch
        handler = self.handle_common(handler, request, *args, **kwargs)

        # dispatch
        return handler(request, *args, **kwargs)


class BackendMixin(DispatchMixin):
    """
    Makes Views Backend-aware with overrides of core behaviors.

    "backend" to expose backend config to template logic
    "media" to provide media collection for components above and below views
    "get_handler()" to provide common data preparation prior to method handler
    """

    backend = None


class View(BackendMixin, base.View):
    """ View with override of "dispatch" """


class BackendTemplateMixin(BackendMixin, base.TemplateResponseMixin,
                           base.ContextMixin):

    mode_title = ''
    response_class = TemplateResponse

    def get_media(self):
        return self.backend.media

    def get_context_data(self, **kwargs):
        kwargs.update(**self.backend.each_context(request=self.request))
        # in case backend passed media, overwrite it with backend et al
        kwargs['media'] = self.get_media()
        return super(BackendMixin, self).get_context_data(**kwargs)


class TemplateView(BackendTemplateMixin, base.TemplateView):
    """ Backend-aware TemplateView """


class AppPermissionsMixin(BackendMixin):
    """
    Redirect to login if logged in (or anonymous) user lacks access to app and
    it is not public.
    """

    def dispatch(self, request, *args, **kwargs):
        if not (self.app_config.has_public_views or
                request.user.has_module_perms(self.app_config.label)):
            return redirect_to_url(request, settings.LOGIN_URL)
        return super(AppPermissionsMixin, self).dispatch(
            request, *args, **kwargs
        )


class AppMixin(AppPermissionsMixin):
    app_config = None

    def __init__(self, app_config, **kwargs):
        self.app_config = app_config
        super(AppMixin, self).__init__(**kwargs)


class AppView(AppMixin, View):
    """ View with override of "dispatch" """


class AppTemplateMixin(AppMixin):

    def get_context_data(self, **kwargs):
        kwargs.update(
            app_config=self.app_config,
            app_label=self.app_config.label,
            app_name=self.app_config.verbose_name,
            app_controllers=[self.backend.get_registered_controller(model)
                             for model in self.app_config.get_models()
                             if self.backend.has_registered_controller(model)],
        )
        return super(AppMixin, self).get_context_data(**kwargs)


class AppTemplateView(AppTemplateMixin, TemplateView):
    """ Backend-aware TemplateView """

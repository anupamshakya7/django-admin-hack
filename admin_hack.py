from django.contrib import admin
from django.db.models.signals import post_syncdb
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.util import flatten_fieldsets
from django.contrib.admin.templatetags.admin_modify import *
from django.contrib.admin.templatetags.admin_modify import submit_row as original_submit_row


def add_cannot_edit_record_permission(sender, **kwargs):
    """
    This syncdb hooks takes care of adding a view permission to all our
    content types.
    """
    for content_type in ContentType.objects.all():
        codename = "cannot_edit_record_for_%s" % content_type.model

        if not Permission.objects.filter(content_type=content_type, codename=codename):
            Permission.objects.create(
                content_type=content_type,
                codename=codename,
                name="Cannot edit record for %s" % content_type.name
            )

post_syncdb.connect(add_cannot_edit_record_permission)


class HackAdminModel(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        """Get readonly fields.

        :param request: HTTP request object.
        :param obj: An object.
        :return: Return readonly fields.
        """
        class_name = self.__class__.__name__.replace('Admin', '').lower()

        for permission in request.user.get_all_permissions():
            head, sep, tail = permission.partition('.')
            perm = "cannot_edit_record_for_%s" % (class_name)
            if str(perm) == str(tail):
                if request.user.has_perm(str(permission)) and not request.user.is_superuser:
                    if self.declared_fieldsets:
                        return flatten_fieldsets(self.declared_fieldsets)
                    else:
                        return list(set(
                            [field.name for field in self.opts.local_fields] +
                            [field.name for field in self.opts.local_many_to_many]
                        ))
        return self.readonly_fields

    @register.inclusion_tag('admin/submit_line.html', takes_context=True)
    def submit_row(context):
        """Sumbit row.

        :param context: Dictionary of required data.
        :return: Return update context.
        """
        ctx = original_submit_row(context)
        app_name, seprator, model_name = str(context.dicts[0]['opts']).partition('.')

        for permission in context['request'].user.get_all_permissions():
            head, sep, tail = permission.partition('.')
            perm = "cannot_edit_record_for_%s" % (model_name)
            if str(perm) == str(tail):
                if context['request'].user.has_perm(str(permission)) and \
                        not context['request'].user.is_superuser:
                    ctx.update({
                        'show_save_and_add_another': False,
                        'show_save_and_continue': False,
                        'show_save': False,
                    })
                return ctx
        return ctx


post_syncdb.connect(add_cannot_edit_record_permission)

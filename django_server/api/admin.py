from django.contrib import admin

from django.contrib import messages

from django.http import HttpRequest, HttpResponseRedirect

from django.urls import path, reverse

from django.utils.html import format_html

from django.utils.translation import gettext, gettext_lazy as _



from .firebase_user_sync import sync_collector_users_from_firebase

from .models import CollectorUser, GitCredential, Project





@admin.register(CollectorUser)

class CollectorUserAdmin(admin.ModelAdmin):

    change_list_template = "admin/api/collectoruser/change_list.html"

    list_display = (

        "email",

        "firebase_uid",

        "mobile_projects_summary",

        "admin_projects_summary",

        "created_at",

    )

    search_fields = ("email", "firebase_uid")

    filter_horizontal = ("mobile_projects", "admin_projects")

    ordering = ("email", "firebase_uid")



    def get_queryset(self, request):

        return super().get_queryset(request).prefetch_related("mobile_projects", "admin_projects")



    def get_urls(self):

        info = self.model._meta.app_label, self.model._meta.model_name

        return [

            path(

                "sync-from-firebase/",

                self.admin_site.admin_view(self.sync_from_firebase_view),

                name="%s_%s_sync_firebase" % info,

            ),

        ] + super().get_urls()



    def sync_from_firebase_view(self, request: HttpRequest):

        if request.method != "POST":

            return HttpResponseRedirect(reverse("admin:api_collectoruser_changelist"))

        try:

            r = sync_collector_users_from_firebase()

            self.message_user(

                request,

                format_html(

                    gettext(
                        "Синхронизация с Firebase Auth: всего в Firebase — {}, создано записей — {}, "
                        "обновлён email — {}, без изменений — {}."
                    ),

                    r.total_firebase,

                    r.created,

                    r.updated_email,

                    r.unchanged,

                ),

                messages.SUCCESS,

            )

        except Exception as e:

            self.message_user(request, str(e), messages.ERROR)

        return HttpResponseRedirect(reverse("admin:api_collectoruser_changelist"))



    fieldsets = (

        (

            None,

            {

                "fields": ("firebase_uid", "email"),

            },

        ),

        (

            _("Мобильное приложение"),

            {

                "fields": ("mobile_projects",),

                "description": _(

                    "Каталог проектов и загрузка пакетов через API <code>/v1/…</code>. "

                    "Без проектов каталог пустой, загрузка вернёт 403."

                ),

            },

        ),

        (

            _("Client-admin"),

            {

                "fields": ("admin_projects",),

                "description": _(

                    "Веб-админка пакетов <code>/ui/</code> — просмотр и правка. "

                    "Можно выдать доступ только в админку, без мобильного приложения, и наоборот."

                ),

            },

        ),

    )



    @admin.display(description=_("Мобильное"))

    def mobile_projects_summary(self, obj: CollectorUser) -> str:

        return self._projects_summary(obj.mobile_projects)



    @admin.display(description=_("Client-admin"))

    def admin_projects_summary(self, obj: CollectorUser) -> str:

        return self._projects_summary(obj.admin_projects)



    @staticmethod

    def _projects_summary(rel) -> str:

        qs = rel.order_by("name").values_list("name", flat=True)

        names = list(qs[:4])

        tail = len(qs) - len(names)

        s = ", ".join(names)

        if tail > 0:

            s += f" (+{tail})"

        return s or "—"





@admin.register(GitCredential)

class GitCredentialAdmin(admin.ModelAdmin):

    list_display = ("id", "label", "created_at")

    readonly_fields = ("public_key", "private_key_encrypted", "created_at")





@admin.register(Project)

class ProjectAdmin(admin.ModelAdmin):

    list_display = ("project_id", "name", "git_remote", "media_bucket", "last_synced_sha", "updated_at")

    search_fields = ("project_id", "name", "git_remote", "media_bucket")

    raw_id_fields = ("git_credential",)



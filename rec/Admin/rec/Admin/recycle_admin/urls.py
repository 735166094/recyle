from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.static import serve
from django.conf.urls.static import static
from django.views.generic import RedirectView
from rest_framework.authtoken.views import obtain_auth_token
urlpatterns = [
    path('', RedirectView.as_view(url='/admin/')),
    path("admin/", admin.site.urls),

    path("recycle/api/", include([
        path("news/", include("news.urls")),
        path('user/', include('user.urls')),
        path('mall/', include('mall.urls')),
        path('recycle/', include('recycle.urls')),
        path('points/', include('points.urls')),
        path("ocr/", include("ocr.urls")),
        path("vin/", include("vin.urls")),
        path('token/', obtain_auth_token, name='api_token_auth'),
    ])),

    path('media/<path:path>/', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "奇奇回收管理系统"
admin.site.site_title = "奇奇回收"
admin.site.index_title = "奇奇回收后台管理平台"
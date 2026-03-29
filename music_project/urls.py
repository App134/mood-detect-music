"""
URL configuration for music_project.
"""
import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from music_app.range_file_response import serve_media_with_range

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('music_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Use custom Range-aware server for media (audio seeking support)
# We enable this in production too to serve MP3s from local filesystem on Render
if os.path.exists(settings.MEDIA_ROOT):
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve_media_with_range),
    ]

    

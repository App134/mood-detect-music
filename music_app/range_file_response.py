"""
Custom view to serve media files WITH HTTP Range request support.
This is needed because Django's built-in static/media server does NOT
handle Range requests, which means audio seeking (setting currentTime)
causes the browser to reload from the beginning.
"""
import os
import mimetypes
import re
from django.http import HttpResponse, HttpResponseNotFound, FileResponse
from django.conf import settings


def serve_media_with_range(request, path):
    """
    Serve a file from MEDIA_ROOT with proper HTTP Range support.
    This allows browsers to seek within audio/video files.
    """
    full_path = os.path.join(settings.MEDIA_ROOT, path)

    # Security: prevent directory traversal
    full_path = os.path.normpath(full_path)
    if not full_path.startswith(str(settings.MEDIA_ROOT)):
        return HttpResponseNotFound("Not found")

    if not os.path.isfile(full_path):
        return HttpResponseNotFound("Not found")

    file_size = os.path.getsize(full_path)
    content_type, _ = mimetypes.guess_type(full_path)
    content_type = content_type or 'application/octet-stream'

    range_header = request.META.get('HTTP_RANGE', '').strip()

    if range_header:
        # Parse Range header: "bytes=START-END"
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1

            # Clamp values
            if start >= file_size:
                start = file_size - 1
            if end >= file_size:
                end = file_size - 1

            length = end - start + 1

            with open(full_path, 'rb') as f:
                f.seek(start)
                data = f.read(length)

            response = HttpResponse(data, status=206, content_type=content_type)
            response['Content-Length'] = str(length)
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Accept-Ranges'] = 'bytes'
            return response

    # No Range header: serve full file normally
    response = FileResponse(open(full_path, 'rb'), content_type=content_type)
    response['Content-Length'] = str(file_size)
    response['Accept-Ranges'] = 'bytes'
    return response

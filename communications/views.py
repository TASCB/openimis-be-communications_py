"""DRF endpoints for binary uploads/downloads (activity attachments & library assets).

GraphQL is JSON-only, so file uploads use multipart DRF endpoints (mirroring the
``training`` module). Files are stored via Django default storage; metadata is created
through the service layer so audit fields are populated.
"""
import logging

from django.http import FileResponse, Http404
from rest_framework import views
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from core.views import check_user_rights

from communications.apps import CommunicationsConfig
from communications.models import (
    CommunicationActivity, ActivityAttachment, LibraryAsset,
    CommunicationPost, CommunicationPostAttachment,
)
from communications.services import (
    ActivityAttachmentService, LibraryAssetService, CommunicationPostAttachmentService,
)

logger = logging.getLogger(__name__)


class ActivityAttachmentUploadView(views.APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [check_user_rights(CommunicationsConfig.gql_attachment_upload_perms)]

    def post(self, request):
        try:
            activity_id = request.data.get('activity_id')
            upload = request.FILES.get('file')
            if not activity_id or not upload:
                return Response({'success': False, 'error': 'activity_id and file are required'}, status=400)
            if not CommunicationActivity.objects.filter(id=activity_id, is_deleted=False).exists():
                return Response({'success': False, 'error': 'activity not found'}, status=404)
            payload = {
                'activity_id': activity_id,
                'file': upload,
                'file_name': request.data.get('file_name') or upload.name,
                'file_type': request.data.get('file_type') or getattr(upload, 'content_type', None),
                'description': request.data.get('description'),
            }
            res = ActivityAttachmentService(request.user).create(payload)
            if not res['success']:
                return Response(res, status=400)
            return Response({'success': True, 'id': res['data']['id']}, status=201)
        except Exception as exc:
            logger.error("communications attachment upload failed", exc_info=exc)
            return Response({'success': False, 'error': str(exc)}, status=500)


class LibraryAssetUploadView(views.APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [check_user_rights(CommunicationsConfig.gql_library_upload_perms)]

    def post(self, request):
        try:
            upload = request.FILES.get('file')
            code = request.data.get('code')
            name = request.data.get('name')
            if not upload or not code or not name:
                return Response({'success': False, 'error': 'code, name and file are required'}, status=400)
            payload = {
                'code': code,
                'name': name,
                'asset_type': request.data.get('asset_type') or 'DOCUMENT',
                'file': upload,
                'file_name': request.data.get('file_name') or upload.name,
                'file_type': request.data.get('file_type') or getattr(upload, 'content_type', None),
                'description': request.data.get('description'),
                'is_active': True,
            }
            res = LibraryAssetService(request.user).create(payload)
            if not res['success']:
                return Response(res, status=400)
            return Response({'success': True, 'id': res['data']['id']}, status=201)
        except Exception as exc:
            logger.error("communications library upload failed", exc_info=exc)
            return Response({'success': False, 'error': str(exc)}, status=500)


class _BaseDownloadView(views.APIView):
    model = None

    def get(self, request, uuid):
        obj = self.model.objects.filter(id=uuid, is_deleted=False).first()
        if not obj or not obj.file:
            raise Http404
        # ?inline=1 serves the file for in-browser preview (images/PDF) rather than forcing a download.
        inline = request.query_params.get('inline') in ('1', 'true', 'True')
        try:
            return FileResponse(obj.file.open('rb'), as_attachment=not inline,
                                filename=obj.file_name or 'download')
        except Exception as exc:
            logger.error("communications download failed", exc_info=exc)
            raise Http404


class ActivityAttachmentDownloadView(_BaseDownloadView):
    permission_classes = [check_user_rights(CommunicationsConfig.gql_attachment_search_perms)]
    model = ActivityAttachment


class LibraryAssetDownloadView(_BaseDownloadView):
    permission_classes = [check_user_rights(CommunicationsConfig.gql_library_search_perms)]
    model = LibraryAsset


class PostAttachmentUploadView(views.APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [check_user_rights(CommunicationsConfig.gql_post_create_perms)]

    def post(self, request):
        try:
            post_id = request.data.get('post_id')
            # is_inline images are embedded in the body HTML and uploaded while composing,
            # before the post exists — so post_id is optional for them.
            is_inline = request.data.get('is_inline') in ('1', 'true', 'True', True)
            upload = request.FILES.get('file')
            if not upload:
                return Response({'success': False, 'error': 'file is required'}, status=400)
            if not post_id and not is_inline:
                return Response({'success': False, 'error': 'post_id is required'}, status=400)
            if post_id and not CommunicationPost.objects.filter(id=post_id, is_deleted=False).exists():
                return Response({'success': False, 'error': 'post not found'}, status=404)
            payload = {
                'post_id': post_id or None,
                'is_inline': is_inline,
                'file': upload,
                'file_name': request.data.get('file_name') or upload.name,
                'file_type': request.data.get('file_type') or getattr(upload, 'content_type', None),
                'file_size': getattr(upload, 'size', None),
                'description': request.data.get('description'),
            }
            res = CommunicationPostAttachmentService(request.user).create(payload)
            if not res['success']:
                return Response(res, status=400)
            return Response({'success': True, 'id': res['data']['id']}, status=201)
        except Exception as exc:
            logger.error("communications post attachment upload failed", exc_info=exc)
            return Response({'success': False, 'error': str(exc)}, status=500)


class PostAttachmentDownloadView(_BaseDownloadView):
    permission_classes = [check_user_rights(CommunicationsConfig.gql_post_search_perms)]
    model = CommunicationPostAttachment

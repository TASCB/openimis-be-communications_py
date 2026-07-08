"""URL patterns for the Communications module (DRF upload/download endpoints)."""
from django.urls import path

from communications.views import (
    ActivityAttachmentUploadView, ActivityAttachmentDownloadView,
    LibraryAssetUploadView, LibraryAssetDownloadView,
    PostAttachmentUploadView, PostAttachmentDownloadView,
)

urlpatterns = [
    path('attachments/upload/', ActivityAttachmentUploadView.as_view()),
    path('attachments/<uuid:uuid>/download/', ActivityAttachmentDownloadView.as_view()),
    path('library/upload/', LibraryAssetUploadView.as_view()),
    path('library/<uuid:uuid>/download/', LibraryAssetDownloadView.as_view()),
    path('post-attachments/upload/', PostAttachmentUploadView.as_view()),
    path('post-attachments/<uuid:uuid>/download/', PostAttachmentDownloadView.as_view()),
]

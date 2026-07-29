"""Domain adapter: consumes the generic Approval Engine's terminal outcome for CommunicationPost.

Bound to the ``approval_service.finalized`` service signal (see ``signals``):

- APPROVED  -> ``is_published = True``, ``published_at = now()`` (visible in the feed).
- REJECTED  -> ``is_published = False`` + rejection reason in json_ext.
- CANCELLED -> ``is_published = False``.

The mirror uses ``.update()`` (no audit user needed) because the authoritative audit trail lives in
the engine's ApprovalRequest/Step/Decision rows; ``CommunicationPost.is_published`` is a denormalised mirror.
"""
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

DOMAIN = 'communications.CommunicationPost'


class CommunicationPostApprovalAdapter:

    @staticmethod
    def on_finalized(**kwargs):
        try:
            result = kwargs.get('result') or {}
            data = result.get('data') or {}
            if data.get('domain') != DOMAIN:
                return  # another domain's request — ignore

            from approval.models import ApprovalRequest
            from communications.models import CommunicationPost

            appr = ApprovalRequest.objects.filter(id=data.get('id')).first()
            if not appr:
                return
            post = CommunicationPost.objects.filter(id=appr.object_id, is_deleted=False).first()
            if not post:
                logger.warning("communications adapter: CommunicationPost %s not found", appr.object_id)
                return

            decision = data.get('decision')
            if decision == 'APPROVED':
                CommunicationPost.objects.filter(id=post.id).update(
                    is_published=True,
                    published_at=timezone.now()
                )
                logger.info("communication_post %s -> PUBLISHED via approval engine", post.id)
            elif decision == 'REJECTED':
                reason = data.get('reason', '')
                json_ext = post.json_ext or {}
                json_ext['approval_rejection_reason'] = reason
                CommunicationPost.objects.filter(id=post.id).update(
                    is_published=False,
                    json_ext=json_ext
                )
                logger.info("communication_post %s -> REJECTED via approval engine", post.id)
            elif decision == 'CANCELLED':
                CommunicationPost.objects.filter(id=post.id).update(is_published=False)
                logger.info("communication_post %s -> CANCELLED via approval engine", post.id)
        except Exception as exc:
            logger.error("communications approval adapter failed", exc_info=exc)
            return [str(exc)]

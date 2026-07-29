# Service-signal bindings: approval engine integration.

import logging

logger = logging.getLogger(__name__)


def bind_service_signals():
    try:
        from core.service_signals import ServiceSignalBindType
        from core.signals import bind_service_signal
        from communications.approval_adapter import CommunicationPostApprovalAdapter
        bind_service_signal(
            'approval_service.finalized',
            CommunicationPostApprovalAdapter.on_finalized,
            bind_type=ServiceSignalBindType.AFTER,
        )
    except Exception as exc:
        # approval module may be absent in some deployments — degrade gracefully.
        logger.warning("communications: approval-engine binding skipped (%s)", exc)

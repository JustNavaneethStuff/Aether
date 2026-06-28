"""External ecosystem adapters (Atlas Queue, Argus) with local defaults."""

from aether_common.integrations.factory import build_knowledge_acquisition, build_task_queue

__all__ = ["build_knowledge_acquisition", "build_task_queue"]

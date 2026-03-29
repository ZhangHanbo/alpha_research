"""Knowledge store for persistent paper and evaluation storage."""

from alpha_research.knowledge.schema import create_tables
from alpha_research.knowledge.store import KnowledgeStore

__all__ = ["create_tables", "KnowledgeStore"]

"""
Workflows Package for BrowserControL01
======================================

Collects all workflow implementations.
"""

from .base_workflow import BaseWorkflow

# Consider a WorkflowRegistry similar to SiteModuleRegistry if dynamic loading is needed
# For now, direct imports are used by main.py or other orchestrators.

__all__ = [
    'BaseWorkflow'
] 
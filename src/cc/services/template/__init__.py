"""Template service module."""

from __future__ import annotations
from .template import (
    Template,
    TEMPLATE_LIBRARY,
    TemplateService,
    get_template_service,
    render_template,
)

__all__ = [
    "Template",
    "TEMPLATE_LIBRARY",
    "TemplateService",
    "get_template_service",
    "render_template",
]
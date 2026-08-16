"""Page objects: the layer where the domain's vocabulary lives.

Everything here is engine-agnostic. It builds on the abstract contracts of ``core`` and knows
nothing about Playwright or pywinauto, which is what lets a desktop suite reuse it.
"""

from automation_framework.pages.assertions import (
    expect_count,
    expect_hidden,
    expect_text,
    expect_text_containing,
    expect_value,
    expect_visible,
)
from automation_framework.pages.base import BasePage
from automation_framework.pages.component import Component

__all__ = [
    "BasePage",
    "Component",
    "expect_count",
    "expect_hidden",
    "expect_text",
    "expect_text_containing",
    "expect_value",
    "expect_visible",
]

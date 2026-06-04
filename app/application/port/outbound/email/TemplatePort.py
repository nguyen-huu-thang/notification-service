from typing import Protocol


class TemplatePort(Protocol):
    async def render(self, template_name: str, context: dict) -> str: ...

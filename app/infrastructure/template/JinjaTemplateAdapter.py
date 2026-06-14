import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape

from xime.core.config.runtime import RuntimeConfig

_log = logging.getLogger(__name__)


class JinjaTemplateAdapter:
    def __init__(self, config: RuntimeConfig) -> None:
        template_dir: str = config.get(
            "template.dir", "app/infrastructure/template/templates"
        )
        self._template_dir = Path(template_dir)
        self._env = Environment(
            loader=FileSystemLoader(str(self._template_dir)),
            autoescape=select_autoescape(["html", "j2"]),
        )
        _log.info("Template adapter configured: dir=%s", self._template_dir)

    async def post_construct(self) -> None:
        if not self._template_dir.exists():
            raise RuntimeError(
                f"Template directory not found: {self._template_dir}"
            )
        _log.info("Template adapter ready: %d templates available",
                  len(list(self._template_dir.glob("*.j2"))))

    async def render(self, template_name: str, context: dict) -> str:
        try:
            template = self._env.get_template(template_name)
        except TemplateNotFound:
            raise ValueError(f"Template not found: {template_name!r}")
        return template.render(**context)

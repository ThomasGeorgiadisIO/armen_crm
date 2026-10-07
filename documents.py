"""LaTeX-based PDF document generation.

Each of the 4 certificate templates is a Jinja2 template using LaTeX-safe
delimiters (\\VAR{...}, \\BLOCK{...}) instead of Jinja's default {{ }} / {% %},
since those collide with LaTeX syntax. Every substituted string must go
through the `tex` filter (\\VAR{value|tex}) to escape LaTeX special
characters -- never substitute raw user-entered text unescaped.

tectonic (a self-contained XeTeX-based engine) compiles the rendered .tex
to PDF. It's used instead of a full MiKTeX/TeX Live install because it's a
single portable binary, which matters for bundling into the Windows .exe.
"""
from __future__ import annotations

import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

import business_info
from paths import app_dir

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
FONTS_DIR = BASE_DIR / "assets" / "fonts"
OUTPUT_DIR = app_dir() / "output"

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')

DOCUMENT_TYPES = {
    "compliance": "compliance.tex.j2",
    "strength_tightness_test": "strength_tightness_test.tex.j2",
    "maintenance_program": "maintenance_program.tex.j2",
    "technical_report": "technical_report.tex.j2",
}

_LATEX_SUBS = (
    (re.compile(r"\\"), r"\\textbackslash{}"),
    (re.compile(r"([{}_#%&$])"), r"\\\1"),
    (re.compile(r"~"), r"\\~{}"),
    (re.compile(r"\^"), r"\\^{}"),
    (re.compile(r'"'), r"''"),
)


def tex_escape(value) -> str:
    if value is None:
        return ""
    text = str(value)
    for pattern, repl in _LATEX_SUBS:
        text = pattern.sub(repl, text)
    return text


def _mbar_to_mmhg(mbar) -> str:
    """1 mbar ≈ 0.750062 mmHg."""
    return f"{float(mbar) * 0.750062:.2f}"


_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    block_start_string=r"\BLOCK{",
    block_end_string="}",
    variable_start_string=r"\VAR{",
    variable_end_string="}",
    comment_start_string=r"\#{",
    comment_end_string="}",
    line_statement_prefix="%%",
    line_comment_prefix="%#",
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=False,
)
_env.filters["tex"] = tex_escape
_env.filters["mmhg"] = _mbar_to_mmhg


def render_tex(document_type: str, context: dict) -> str:
    template_name = DOCUMENT_TYPES[document_type]
    template = _env.get_template(template_name)
    return template.render(**context)


def build_context(customer, project, template_row) -> dict:
    """Join the Customer/Project/Template dataclasses + business constants
    + computed mbar->mmHg conversions into the dict the templates expect.

    Installation/boiler/meter details (application_no, hkasp, pressures,
    etc.) live on `template_row`, not `project` -- they're entered fresh
    per document generation since they can change between visits."""
    strength_mbar = template_row.strength_test_design_pressure_mbar or "0"
    tightness_mbar = template_row.tightness_test_design_pressure_mbar or "0"
    return {
        "customer": asdict(customer),
        "project": asdict(project),
        "template": asdict(template_row),
        "business": business_info.as_dict(),
        "strength_pressure_bar": f"{float(strength_mbar) / 1000:g}",
        "strength_pressure_mmhg": _mbar_to_mmhg(strength_mbar),
        "tightness_pressure_mmhg": _mbar_to_mmhg(tightness_mbar),
    }


def sanitize_filename(name: str) -> str:
    return _INVALID_FILENAME_CHARS.sub("_", name).strip() or "unnamed"


def output_path_for(customer_name: str, project_id: int, document_type: str) -> Path:
    return OUTPUT_DIR / sanitize_filename(customer_name) / str(project_id) / f"{document_type}.pdf"


def _tectonic_executable() -> str:
    """Prefer the tectonic binary PyInstaller's --add-binary unpacks alongside
    the other bundled data (BASE_DIR, i.e. sys._MEIPASS in a frozen build --
    NOT app_dir(), which is the real .exe's own directory and is a different
    path for a --onefile build); fall back to PATH in dev (nix-shell provides
    tectonic there)."""
    exe_name = "tectonic.exe" if platform.system() == "Windows" else "tectonic"
    bundled = BASE_DIR / exe_name
    return str(bundled) if bundled.exists() else "tectonic"


def compile_pdf(tex_source: str, output_pdf_path: str) -> None:
    """Write tex_source to a temp dir and compile it with tectonic, moving the
    resulting PDF to output_pdf_path. Font files are copied alongside the .tex
    so fontspec's relative Path= lookup resolves regardless of cwd."""
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tex_file = tmp_path / "document.tex"
        tex_file.write_text(tex_source, encoding="utf-8")

        fonts_tmp = tmp_path / "fonts"
        shutil.copytree(FONTS_DIR, fonts_tmp)

        result = subprocess.run(
            [_tectonic_executable(), "--outdir", str(tmp_path), str(tex_file)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"tectonic failed (exit {result.returncode}):\n{result.stdout}\n{result.stderr}"
            )

        produced_pdf = tmp_path / "document.pdf"
        shutil.move(str(produced_pdf), str(output_pdf_path))

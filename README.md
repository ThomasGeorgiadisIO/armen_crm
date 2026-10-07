# Armen CRM

A simple desktop CRM for a gas-installation safety-certification business.
Tracks Customers -> Projects (one gas installation/application per
customer) -> Templates (generated certificate PDFs, with a full history).
See `CLAUDE.md` for the full design rationale.

## Running on Linux (development)

Requires [Nix](https://nixos.org/) for the dev shell (provides Tk-enabled
Python and `tectonic` for local PDF generation):

```
nix-shell
python main.py
```

The first run creates `customers.db` (SQLite) next to the script if it
doesn't already exist.

To import the legacy `Customers.ods` spreadsheet once (only needed if
`customers.db` doesn't exist yet):

```
python migrate_from_ods.py
```

Run tests:

```
nix-shell --run "python -m pytest tests/ -v"
```

## Running on Windows (end user)

Download `ArmenCRM.exe` from the latest successful run of the
"Build Windows exe" GitHub Actions workflow and run it directly -- no
Python install required. `customers.db` and the `output/` folder (where
generated PDFs land, one subfolder per customer per project) are created
next to the `.exe` on first run.

## How documents are generated

Each of the 4 certificate types is a LaTeX template (`templates/*.tex.j2`)
rendered with Jinja2 and compiled to PDF with
[tectonic](https://tectonic-typesetting.github.io/) -- a small
self-contained LaTeX engine, chosen specifically because it's a single
binary that's easy to bundle into the Windows `.exe` (no multi-GB
MiKTeX/TeX Live install needed on the end user's machine). A Greek-capable
font (DejaVu Serif) is bundled under `assets/fonts/` for the same reason.

Business-constant fields (the engineer's name, license numbers, business
address) live in `business_info.py` -- edit that file directly if the
license is renewed or the address changes.

## Windows packaging

`.github/workflows/build-windows.yml` builds `ArmenCRM.exe` on a
`windows-latest` GitHub Actions runner via PyInstaller, bundling
`tectonic.exe` (downloaded from the tectonic project's GitHub releases)
and the `templates/`, `assets/`, `schema.sql` data files. PyInstaller
cannot cross-compile a Windows executable from Linux, which is why this
runs in CI on an actual Windows runner rather than being built locally.

After any change to `main.py`/its dependencies, download the workflow's
build artifact and smoke-test it on a real Windows machine before treating
it as done -- this hasn't been verified on real Windows hardware yet.

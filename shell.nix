# Dev shell for armen_crm on NixOS.
#
# Usage:
#   nix-shell
#   python main.py
#
# Provides Tk-enabled Python (python311Full was removed from nixpkgs;
# python311.withPackages [tkinter] is the current way to get Tk bindings)
# plus tectonic for local LaTeX->PDF testing.
{ pkgs ? import <nixpkgs> {} }:

let
  venvDir = "./.venv";
  pythonWithTkinter = pkgs.python311.withPackages (ps: [ ps.tkinter ]);
in
pkgs.mkShell {
  name = "armen-crm-dev-environment";

  buildInputs = [
    pythonWithTkinter
    pkgs.tectonic
  ];

  shellHook = ''
    if [ ! -d "${venvDir}" ]; then
      echo "Creating venv at ${venvDir}..."
      # --system-site-packages: tkinter is bound to the interpreter above,
      # not pip-installable, so the venv must inherit the base site-packages.
      ${pythonWithTkinter}/bin/python3 -m venv --system-site-packages "${venvDir}"
      "${venvDir}/bin/pip" install -q --upgrade pip
      "${venvDir}/bin/pip" install -q -r requirements-dev.txt
    fi
    source "${venvDir}/bin/activate"

    echo "armen_crm dev shell ready (venv: ${venvDir})"
  '';
}

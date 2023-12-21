#! /bin/bash
# Bash script for building the Tofu font.
#
# Uses the `nanoemoji` util to compile a font containing the tofu glyph in
# the `source/` directory. The TTF output is further transformed to have the
# desired properties for our Tofu font (e.g. updating CMAP to map all codepoints
# to .notdef).
#
# Additional outputs include `tofu.css`, which has the Tofu font binary data
# inlined.


if [[ ! "${VIRTUAL_ENV}" ]]; then
  echo "ERROR - virtual environment not active. Please set up a venv, install requirements, and try again."
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r requirements.txt"
  exit 1
fi

if [[ ! "$(which nanoemoji)" ]]; then
  echo "ERROR - nanoemoji not found. Please set up nanoemoji in your venv:"
  echo "  pip install -e ${PATH_TO_NANOEMOJI_REPO}"
  exit 1
fi

script_path="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
python "${script_path}/build.py" $@


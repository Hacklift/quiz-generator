"""Refresh packaged assets. Run from any directory; fontTools is build-time only.

Usage: python server/scripts/prepare_pdf_branding.py /path/to/Archivo-variable.ttf
Source: https://github.com/google/fonts/tree/main/ofl/archivo (SIL OFL 1.1).
The original variable font is not required at PDF generation time.
"""

import argparse
from pathlib import Path
from shutil import copyfile

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    target = root / "server/app/quiz/assets/branding"
    target.mkdir(parents=True, exist_ok=True)
    copyfile(root / "client/public/images/logo.png", target / "logo.png")
    for name, weight in (("Regular", 400), ("Bold", 800)):
        font = instantiateVariableFont(
            TTFont(args.font), {"wght": weight, "wdth": 100}, inplace=True
        )
        # Distinct PostScript names prevent ReportLab from reusing one face
        # for both static instances of the variable font.
        for record in font["name"].names:
            if record.nameID in (1, 2, 4, 6):
                value = {
                    1: "Archivo",
                    2: "Regular" if weight == 400 else "ExtraBold",
                    4: f"Archivo {name}",
                    6: f"Archivo-{name}",
                }[record.nameID]
                record.string = value.encode(record.getEncoding())
        font.save(target / f"Archivo-{name}.ttf")


if __name__ == "__main__":
    main()

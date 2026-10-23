# Live results PDF assets

`logo.png` is an exact copy of `client/public/images/logo.png`, which remains
its authoritative source. A test checks equality. Refresh with
`python server/scripts/prepare_pdf_branding.py /path/to/Archivo-variable.ttf`.

Archivo is the frontend font (`client/src/shared/ui/quizwerk/fonts.ts`). The
packaged static TrueType instances are normal-width weights 400 and 800, made
from https://github.com/google/fonts/blob/main/ofl/archivo/Archivo%5Bwdth,wght%5D.ttf.
The original SIL Open Font License is included in `OFL.txt`; embedding and
redistribution are permitted. FontTools is needed only to refresh these files.
No fonts are fetched at runtime.

Colors come from `client/tailwind.config.ts`: primary `#0a3264`, light brand
`#e7ecf3`, paper `#f3f2f2`, ink `#201e1d`. The heading weight follows the shared
Quizwerk tokens (Archivo 800). Correct answers have bold brand-blue text;
other outcomes use ink and explicit text labels for grayscale readability.

Both backend Dockerfiles copy the server tree, including these assets. Paths
are resolved relative to the module, independent of CWD or a frontend mount.
Missing, corrupt, or unreadable required assets raise a descriptive RuntimeError;
the route produces no successful-export analytics event. Restore packaged assets
and retry. There is no silent unbranded fallback.

Archivo covers Latin accents and its supplied Unicode repertoire, not every
writing system or emoji. Unsupported glyphs require a separately licensed font
and explicit future fallback policy. Session dates are absent from the existing
export payload and are therefore omitted. Average percentage is the arithmetic
mean of authoritative participant percentages, including historical denominators.

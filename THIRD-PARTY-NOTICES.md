# Third-party notices

[`LICENSE`](LICENSE) covers only the original skill content of this repository
(`SKILL.md`, `README.md`, `scripts/`, `references/`, `assets/`). It does **not**
cover the following, which are governed by their own terms.

## Primer Premier 5

Commercial software by Premier Biosoft. **Not distributed in this repository.**
You must supply your own licensed copy as a CrossOver `.cxarchive`. The driver
verifies the executable SHA256 before running, but that check is a compatibility
guard, not a license check — obtaining a valid license is your responsibility.

## CrossOver

Commercial software by CodeWeavers. **Not distributed in this repository.**
Required to run the Windows PP5 build on macOS; subject to CodeWeavers' license.

## Bundled Python runtime — `runtime/python-win32/`

A Windows Python 3.8.10 32-bit embeddable runtime, redistributed unchanged.
Governed by the Python Software Foundation License, reproduced in
[`runtime/python-win32/LICENSE.txt`](runtime/python-win32/LICENSE.txt).

It is included because the PP5 driver runs Win32 control code inside the
CrossOver bottle, and depending on a system Python there would make the
workflow non-reproducible across machines.

## NCBI services

`ORFfinder` and `Primer-BLAST` are used through NCBI's public web services.
Usage is subject to [NCBI's policies](https://www.ncbi.nlm.nih.gov/home/about/policies/).
Submitting sequences uploads them to NCBI — only do this when you are authorised
to share the sequence.

# tesseract

## Function

An OCR engine: page image in, text out — plain, hOCR or TSV with per-word boxes and confidences.
Command line only, no daemon.

**Here it exists for one corpus: the Edelman books** recovered with the archive downloader
(`/home/klaas/src/archive-book`). Those arrive as numbered page JPEGs with a hashed `manifest.json`
and no text layer, so nothing downstream — search, quote-checking, agent memory — can read them
until they are OCRed.

## Role

A tool, not a service. It reads files it is pointed at and writes text beside them; it owns no
device, no config and no state on this machine.

**Why it matters more than OCR usually does.** The knowledge substrate being designed for the
research agents anchors every claim to verbatim evidence on a page (`raw/<book>/pNNN.txt#Lx-y`). The
OCR text is therefore what a quote is checked *against*. An OCR error is not cosmetic: it is the
reference text being wrong. Keep the page images and their hashes as the primary record, and treat
the text as a derived, regenerable layer.

## Ownership

`extra/tesseract 5.5.3-1`, packaged by `Caleb Maclennan <alerque@archlinux.org>`, Apache-2.0,
upstream `https://github.com/tesseract-ocr/tesseract`. Signature enforced. The CachyOS mirror
carries `cachyos-extra-v3/tesseract 5.5.3-1.1`, same upstream version, and repository order decides
which one installs.

| | |
| --- | --- |
| Download | 1.68 MiB |
| Installed | 4.66 MiB |
| Built | 2026-07-24 |
| Depends | `leptonica`, `tessdata`, `tesseract-data-osd`, `curl`, `libarchive`, `libgomp` |

`tessdata` is virtual: a language pack satisfies it. `extra/tesseract-data-eng 2:4.1.0-5`
(9.03 MiB, 22.38 MiB installed) is the one wanted. `leptonica` is not yet installed and comes in as
a dependency.

## Intent

**Install:** `sudo pacman -S --noconfirm tesseract tesseract-data-eng` — needs a password, so a
person runs it.

**Use is not managed here.** How pages become text — page segmentation mode, whether to keep hOCR,
how output lands in the corpus — belongs to the corpus pipeline, not to this record.

**Uninstall:** `pacman -Rs tesseract tesseract-data-eng` and delete this record. It writes nothing
outside the files it is asked to produce.

## Verification

Installed 2026-10-24: repository order chose `cachyos-extra-v3/tesseract 5.5.3-1.1`, pulling
`leptonica 1.87.0-2.1` and `tesseract-data-osd 2:4.1.0-5`. `ms status` reads `5.5.3, files intact`.

**Fit for this corpus, measured.** On *Neural Darwinism* pp. 4–5 (`--psm 4`), the output matched an
independent hand transcription line for line — hyphenation included — at a mean word confidence
of 92, with two words under 80, both read correctly.

```toml
group      = "Applications"
version    = "pacman -Q tesseract"
version_re = "([0-9][0-9.]*)"
presence   = "pacman -Q tesseract"
check      = "pacman -Qkk tesseract"
ok         = "files intact"
fail       = "files altered or missing"
missing    = "not installed"
```

**The language pack is not the check.** `tesseract --list-langs` would also prove `eng` is present,
but a check should answer one question; whether the right language data is installed is a fact
about the corpus's needs, and it can be added as its own label if a second language arrives.

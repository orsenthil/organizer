## Organizer

Organizer is a tool for your digital assets. On a given directory, it will scan the files, de-duplicates them by MD5 hash
and organizes them to into YYYY/MM path, and writes a report the changes. It can clean up the resulting directories after the movement.

I developed it for de-duplicating and organizing my digital assets in my Google Drive.

![](./assets/Orgnizing.png)

### What it does
- Scans the current folder (recursively), skipping hidden/system folders.
- Computes MD5 to find duplicates. Keeps the first path and marks the rest for deletion.
- Derives Year/Month from earliest of metadata (ExifTool when available, else EXIF/PDF), filename dates (YYYY or YYYY-MM), birthtime, ctime, mtime.
- Generates a CSV report. By default, it is a dry run.

**Safety First** - Take a backup before running with `--organize` or `--delete-duplicates`.

ExifTool is required (used to read original creation timestamps). Install it first:

```bash
brew install exiftool
```

### Architecture
The tool is a small CLI with a clear pipeline:
- **Scanner** reads files, hashes content, and resolves the earliest creation timestamp.
- **Planner** groups duplicates by hash and plans target paths.
- **Actions** move files, delete duplicates, and optionally clean empty folders.

Code layout:
- `src/organizer/scanner.py`: file discovery, MD5, and timestamp resolution
- `src/organizer/planner.py`: grouping and output path planning
- `src/organizer/actions.py`: moves, deletes, timestamp preservation
- `src/organizer/cli.py`: CLI arguments and report generation

### Technologies used
- [ExifTool](https://exiftool.org/) for robust metadata timestamps
- [Exif](https://en.wikipedia.org/wiki/Exif) and [PDF](https://en.wikipedia.org/wiki/PDF) metadata parsing
- [MD5](https://en.wikipedia.org/wiki/MD5) for duplicate detection
- [CSV](https://en.wikipedia.org/wiki/Comma-separated_values) for reports
- [PyInstaller](https://pyinstaller.org/) for single-file binaries
- [uv](https://docs.astral.sh/uv/) for dependency management

### Dependencies
- [PyPDF2](https://pypi.org/project/PyPDF2/) for PDF metadata fallback
- [Pillow](https://pypi.org/project/Pillow/) for image EXIF fallback
- [ExifTool](https://exiftool.org/) (external binary)
- [PyInstaller](https://pyinstaller.org/) (build extra)
- [pytest](https://pypi.org/project/pytest/) (test extra)


### Build and run
From the project root, build a single-file binary:

```bash
make
```

or

```bash
uv run --extra build pyinstaller --onefile -n organizer src/organizer/cli.py
```

Copy `dist/organizer` into your `$PATH` and run it directly:

```bash
organizer --version
```


### Common usage
Show version and build time:

```bash
organizer --version
```
Dry run (CSV only, no changes) in the current directory:

```bash
organizer
```

Apply changes (move originals only):

```bash
organizer --organize /path/to/folder
```

Organize into a separate output folder:

```bash
organizer --organize /path/to/folder --output-root /path/to/output
```

Delete duplicates only:

```bash
organizer --delete-duplicates /path/to/folder
```

Delete empty folders in current working directory:

```bash
organizer --delete-empty-folders
```

Custom report path (dry run):

```bash
organizer --report /path/to/report.csv
```

### Tests
```bash
uv run --extra test pytest
```

### Safety
- Default behavior is a **dry run** (CSV only).
- Use either `--organize` or `--delete-duplicates` to apply changes.
- Organizing and deleting are separate runs.

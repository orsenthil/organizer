## Organizer

Organize synced files into `Year/Month` folders, deduplicate by MD5, and generate a CSV report before making any changes.

### What it does
- Scans the current folder (recursively), skipping hidden/system folders.
- Computes MD5 to find duplicates. Keeps the first path and marks the rest for deletion.
- Derives Year/Month from file ctime (fallback to mtime, then current date).
- Generates a CSV report. By default, it is a dry run.

### Install and run (uv)
From the project root:

```bash
uv sync
uv run organizer
```

### Common usage
Dry run (CSV only, no changes):

```bash
uv run organizer --root .
```

Apply changes (move originals only):

```bash
uv run organizer --organize
```

Delete duplicates only:

```bash
uv run organizer --delete
```

Delete empty folders in current working directory after apply:

```bash
uv run organizer --organize --delete-empty
```

Custom report path and output folder:

```bash
uv run organizer --report /path/to/report.csv --output-root /path/to/output
```

### Build a single-file binary (PyInstaller)
```bash
uv run --extra build pyinstaller --onefile -n organizer src/organizer/cli.py
```

The binary will be created in `dist/organizer`.

### Tests
```bash
uv run --extra test pytest
```

### CSV output
The CSV includes:
- `md5`: file hash
- `file_path`: path of the file in the scan
- `original_path`: path of the kept file for that hash
- `is_original`: yes/no
- `year`, `month`
- `target_path`: destination for the kept file
- `action`: keep/duplicate

### Safety
- Default behavior is a **dry run** (CSV only).
- Use either `--organize` or `--delete` to apply changes.
- Organizing and deleting are separate runs.

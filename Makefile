default:
	ORGANIZER_BUILD_TIME="$$(date -u +%Y-%m-%dT%H:%M:%SZ)" uv run --extra build pyinstaller --onefile -n organizer src/organizer/cli.py

# Copy a directory to a new location for testing.
rsync-test:
	rsync -avP "$(SRC)" "$(DST)"

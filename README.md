# levelzap-python
A recreation and expansion of the original LevelZap utility in Python

## Basic Usage

Run `levelzap.py` inside the directory you want to flatten or provide the path
as an argument:

```bash
python levelzap.py /path/to/target
```

The utility moves items from subfolders into the target folder, removes the
empty directories and stores a log so actions can be reverted.

### Common options

- `-s`, `--simulate` – perform a dry run without changing files.
- `-m`, `--merge` – merge folders if names conflict.
- `-o`, `--overwrite` – overwrite existing files or folders (destructive).
- `-r`, `--revert` – revert the most recent operation using the last log file.
- `-ra`, `--revert-all` – revert all operations in reverse order.
- `--verify` – verify the integrity of log files.
- `--list-logs` – list available logs with timestamps and status.
- `--update` – check if a newer version of LevelZap is available.

Example dry run:

```bash
python levelzap.py -m --simulate
```

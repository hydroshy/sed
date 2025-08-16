This `workflow` package has been intentionally disabled and archived.

Why: The code was removed from active runtime and stored in backups to
avoid accidental imports while preserving the original source.

To restore the original package, copy the files from one of the backups:

- `backup/workflow_originals/` (verbatim originals)
- `backup/workflow/` (earlier backup; may contain small agent edits)

Example restore command (PowerShell):

Copy-Item -Path "backup\workflow_originals\*" -Destination "workflow\" -Recurse -Force

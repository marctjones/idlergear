# Quickstart: Critical File Declarations and Guardrails

**Feature**: 001-critical-files
**Audience**: developers using IdlerGear with Claude Code

This walks from zero to "my critical files are protected" in under two
minutes.

## Prerequisites

- IdlerGear v0.9 installed in the project (`idlergear install`).
- Claude Code connected to the IdlerGear MCP server (verify with
  `idlergear status`).

## Step 1: Identify a file to protect (10 seconds)

Pick something whose loss would be expensive:

- A local database file (`.idlergear/db.sqlite`, `app.sqlite`).
- A generated artifact that's slow to rebuild (`dist/large-bundle.js`,
  `models/checkpoint.pt`).
- Configuration not in version control (`.env`, `secrets.local.toml`).
- Long-running job checkpoints (`fingerprints/*.partial.tmp`).

For this quickstart, we'll use `.env`.

## Step 2: Declare it (15 seconds)

Add to `.idlergear/config.toml`:

```toml
[[critical_files]]
path = ".env"
auto_backup = true
```

Or use the MCP tool from a Claude Code session:

```
Claude, declare .env as critical with auto-backup.
```

(Claude invokes `idlergear_file_critical(action="declare", path=".env",
auto_backup=true)` and the entry is written.)

## Step 3: Verify protection (15 seconds)

Read the status resource (Claude does this automatically when relevant, or
you can ask explicitly):

```
Claude, what's the critical-files status?
```

Expected output:

```
1 declared:
  .env  —  protection on, auto-backup on, 0 backups, no canonical configured
```

## Step 4: Test protection (30 seconds)

In Claude Code, ask:

```
Delete .env please.
```

You should see a confirmation prompt (an Elicitation):

> Operation `delete` against declared critical path `.env`. Cancel to keep
> the file. Confirm to proceed.

Cancel. The file is intact. Confirm and the operation proceeds normally —
the audit record captures the choice either way.

## Step 5: Test auto-backup (30 seconds)

Ask Claude to edit `.env`:

```
Add a line to .env: FOO=bar
```

The edit proceeds (edits don't require confirmation by default, only
removal/overwrite). After the edit, check `.idlergear/backups/`:

```bash
ls -la .idlergear/backups/
# A hashed directory exists, containing a timestamped pre-edit copy of .env
```

## Step 6: Add a canonical source (optional, 30 seconds)

If your critical file has a canonical version elsewhere (a HuggingFace
dataset, a published config, etc.), declare it:

```toml
[[critical_files]]
path = "config/production.toml"
canonical = "https://example.com/canonical/production.toml"
auto_backup = true
```

Then check divergence:

```
Claude, run idlergear doctor for critical files.
```

Or via the MCP tool:

```
idlergear_doctor(scope="critical")
```

Expected output includes:

```
critical_files:
  config/production.toml
    canonical: https://example.com/canonical/production.toml
    result: match (checked 2s ago)
    backups: 0
```

## What's protected, what isn't

**Protected (requires confirmation):**

- `rm`, `mv` overwriting, `cp -f` overwriting, `trash`.
- Shell redirection that overwrites (`> file`, `>> file`).
- `Write` tool against an existing critical path.

**Auto-backed-up (no confirmation, snapshot taken):**

- `Edit` tool against a critical path.

**Not affected:**

- Read operations (`cat`, `Read` tool).
- Listing (`ls`, `Glob`).
- Operations against paths that don't match any declaration.

## Where backups live

```
.idlergear/backups/
└── <hash-of-source-path>/
    └── 2026-05-14T13-02-44.123-edit.json
```

To restore manually:

```bash
cp .idlergear/backups/<hash>/<timestamp>.json <original-path>
```

(A formal `idlergear_file_critical.restore` action is out of scope for v0.9
but planned for v0.10.)

## When confirmation isn't available

If Claude Code is configured without elicitation support, destructive
operations against critical paths are denied with a message explaining how to
override:

```
IDLERGEAR_NONINTERACTIVE_POLICY=allow
```

This is deliberate. Silent destructive operations in non-interactive contexts
are exactly the data-loss scenario this feature exists to prevent.

## Troubleshooting

**"Operation against declared critical path failed: backup creation failed"**

Check that `.idlergear/backups/` is writable and that the filesystem isn't
full. Edits that require backup are denied if the backup can't be created
(FR-017).

**"Config invalid: unknown field in critical_files"**

The `.idlergear/config.toml` has a typo or an unsupported field. See
`contracts/config-schema.md` for the complete field list.

**"Critical files protection seems slow"**

The hook has a soft target of <50 ms for ≤20 declarations matching ≤100
paths. Slower than that suggests a degenerate glob (e.g., `**` at the
project root with thousands of matches). Tighten the pattern.

**"My critical file was deleted anyway"**

If the deletion happened outside Claude Code (manual `rm` in another
terminal, an external script), this feature does not protect against it.
v0.9 is scoped to AI-assistant-mediated workflows. For broader protection,
consider a filesystem snapshot tool (zfs/btrfs snapshots, `restic`, etc.) —
they live at a lower layer than IdlerGear can reasonably patch.

## Next steps

- Declare more files: see [config-schema.md](contracts/config-schema.md).
- Wire up canonical-source checks: see schemes table in
  [config-schema.md](contracts/config-schema.md).
- Review audit history: `idlergear_file_critical(action="audit",
  since="2026-05-01")`.

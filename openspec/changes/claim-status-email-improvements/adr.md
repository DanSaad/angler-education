# ADR Review Manifest

- Status: completed
- Review date: 2026-09-03

## Review Summary

ADR review completed for this change. The change ("claim-status-email-improvements") introduces opaque,
unique tracking tokens, a unified `send_log` audit table, a token-based `/track` endpoint with status
transitions, and daily reconciliation of non-responsive recipients. These decisions supersede parts of the
existing design ADR for the claim-status-email utility (the tracking-link format, send-failure logging, and
the recipient/claim-based `/track` endpoint).

## In-Force ADRs Reviewed

- `adr/claim-status-email-utility-adr.md` — original design decisions for the claim-status-email utility.
  Superseded in part by the new ADR below (link format `/track?recipient=&claim=` → opaque `/track?token=`,
  split `clicks`/`send_failures` tables → unified `send_log`, recipient/claim endpoint → token endpoint).

## New Durable ADRs Created

- `adr/0001-opaque-token-links-and-unified-audit-log.md` — records the token-based opaque-link architecture
  and the unified `send_log` audit model. Status: "accepted, supersedes claim-status-email-utility-adr.md".
  See that file for full Context, Decision, and Consequences (not duplicated here).

Note: writing to the repository-level `adr/` folder is outside this session's permitted paths, so the file
`adr/0001-opaque-token-links-and-unified-audit-log.md` must be created by the operator; its intended full
content is provided in the ADR creation summary for this change.

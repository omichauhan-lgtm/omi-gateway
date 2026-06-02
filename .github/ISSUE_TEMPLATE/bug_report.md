---
name: Bug Report
about: Create a report to help us improve OMI's reliability, calibration, or routing correctness.
title: "[BUG] "
labels: bug, reliability-leak
assignees: ""
---

## Description
Provide a clear and concise description of the issue. Highlight if this is a calibration drift, routing failure, or telemetry database error.

## Steps to Reproduce
Steps to reproduce the behavior:
1. Submit prompt '...' with mode '...'
2. Observe route chosen '...' instead of expected '...'
3. Check error taxonomy outputs

## Expected Behavior
Explain what you expected to happen according to OMI's routing logic or ECE constraints.

## Technical Details & Environment
- OMI Version: (e.g. 2026.3.0)
- Python Version:
- Database: SQLite / PostgreSQL
- Relevant `.env` configuration snippets:

## Calibration/Telemetry Logs (Optional)
Attach database entries from `routing_decisions` or logs from `/admin/traces` that support the occurrence of the bug.

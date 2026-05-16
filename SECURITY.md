# Security Policy

OMI is designed to be sovereign, reliable, and secure infrastructure. We take security vulnerabilities in the Execution Plane and Intelligence Plane seriously.

## Supported Versions
Currently, only the `main` branch (latest release) is supported for security updates.

## Reporting a Vulnerability
If you discover a vulnerability, **do not open a public issue.**
Please email the maintainers directly with a clear description, steps to reproduce, and potential exploit vectors.

### Scope of Interest
- Unauthorized access to the Administrative Observability Plane (`/admin/*`).
- Prompt injection vulnerabilities that bypass the Judge Engine.
- Telemetry poisoning or SQL injection in the Data Moat.
- Exfiltration of BYOK (Bring Your Own Key) secrets.

## Secret Handling
- OMI will **never** log provider API keys or administrative secrets in the `learning_loop.db` or standard output.
- Telemetry payloads are strictly sanitized.
- If you find any instance where secrets are exposed in stack traces or logs, treat it as a critical vulnerability.

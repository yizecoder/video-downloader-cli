# Security Policy

## Supported version

Security fixes are provided for the latest release.

## Reporting a vulnerability

Do not publish credentials, Cookie files, private video URLs, or exploit details
in a public issue. Contact the maintainer privately and include:

- affected version and operating system;
- reproduction steps with credentials removed;
- expected impact;
- a minimal log with tokens and local paths redacted.

## Credential handling

Cookie files are equivalent to login credentials. This project:

- keeps Bilibili and YouTube Cookie configuration separate;
- ignores the default real Cookie filename in Git;
- never needs Cookie values in an issue report;
- only reports Cookie path, format, and login-state presence in `--check`.

If a Cookie is accidentally shared or committed, revoke the platform session
immediately. Removing the file from the latest commit is not sufficient because
the value may remain in Git history.

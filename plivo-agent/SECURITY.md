# Security Policy

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Please do not open a public GitHub issue for a security problem. Use GitHub's private vulnerability reporting: the repository's **Security** tab, then **Report a vulnerability**.

Include what the problem is, how to reproduce it, and the version or commit.

## Scope notes

- **Plivo requests.** The answer URL and the audio stream accept only requests with a valid Plivo V3 signature, checked with `PLIVO_AUTH_TOKEN` against `public_url` and not against the Host header. Any way to start a conversation without that signature is in scope.
- **Logs.** A served agent does not log the prompt or what is said on a call unless `LOGURU_LEVEL=DEBUG` is set.
- **Secrets.** The package reads `PLIVO_AUTH_ID` and `PLIVO_AUTH_TOKEN` from the environment and never logs them.

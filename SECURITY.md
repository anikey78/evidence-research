# Security policy

## Supported versions

The latest version on the default branch is the supported version.

## Report a vulnerability

Do not report security issues in public GitHub issues. Use GitHub's private
vulnerability reporting for this repository, or contact the repository owner
privately. Include steps to reproduce and the impact. Do not include real API
keys, private user data, or exploit payloads that could harm other systems.

## Deployment safeguards

- Store `OPENAI_API_KEY` in the hosting provider's secret manager. Never commit it.
- Set `ALLOWED_HOSTS` to the exact public hostname before deployment.
- Use HTTPS at the hosting edge and restrict access to the provider dashboard.
- Keep dependencies and the base image updated; review Dependabot and CI findings.
- The built-in in-memory rate limit is per process. Use a shared rate-limit store
  before running multiple replicas or exposing a high-traffic service.
- Do not add user-question logging or analytics without a privacy review.

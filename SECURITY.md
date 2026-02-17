# Security Policy

## Supported Versions

We actively provide security updates for the following versions of `agent-scorecard`:

| Version | Supported          |
| ------- | ------------------ |
| v1.x    | ✅ Yes             |
| < v1.0  | ❌ No              |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a potential security vulnerability in this project, please notify the maintainers privately. This allows us to resolve the issue before it is made public.

### How to report:
1. **Email**: Send a detailed report to [admarsha@gmail.com](mailto:admarsha@gmail.com).
2. **GitHub Private Reporting**: Use the [GitHub Vulnerability Reporting](https://github.com/brewmarsh/agent-scorecard/security/advisories/new) feature if enabled on this repository.

### What to include:
* A description of the vulnerability and its potential impact.
* Step-by-step instructions to reproduce the issue (PoC).
* Any suggested remediation or fix.

## Our Process

* **Acknowledgement**: You will receive an acknowledgement of your report within 48 hours.
* **Status Updates**: We will provide regular updates on our progress as we work toward a resolution.
* **Disclosure**: Once the vulnerability is fixed, we will publish a Security Advisory and credit you for the discovery (unless you prefer to remain anonymous).

## Automated Security Gates

Every Pull Request (PR) to this repository undergoes an automated **Security & Quality Audit**. This audit checks for:
* Insecure use of `eval()`, `exec()`, or `subprocess`.
* Hardcoded secrets or credentials.
* Compliance with our "Agent Physics" requirements to prevent logic regressions.

---
*Thank you for helping keep the AI-agent ecosystem safe!*

# Research Requirements for LLM Coding Assistants

## Overview

This document establishes **mandatory research practices** for LLM coding assistants working on this project. Before implementing complex features or adding dependencies, you MUST conduct thorough research.

**Key Principle:** Don't guess. Don't assume. Research first.

---

## 1. Before Adding Any Dependency

### When This Applies

You MUST research before adding:
- Any new library or package
- Dependencies you haven't used extensively before
- Non-standard or less common libraries (anything that's not universally standard like `requests`, `pytest`, `lodash`)

### Minimum Research Requirements

**Step 1: Search for Alternatives (Minimum 3)**

Before committing to any library, find and compare at least 3 alternatives:

```bash
# Example: Need an HTTP client for Python
# Search: "python http client library comparison 2024"
# Compare: requests, httpx, aiohttp, urllib3

# Example: Need form validation for React
# Search: "react form validation library comparison"
# Compare: react-hook-form, formik, yup, zod
```

**Step 2: Evaluate Each Alternative**

For each candidate library, check:

| Criterion | What to Look For | Red Flags |
|-----------|------------------|-----------|
| **Maintenance** | Recent commits (within 6 months) | Last commit >1 year ago |
| **Adoption** | Weekly downloads, GitHub stars | <100 stars, <1000 weekly downloads |
| **Security** | No critical CVEs, responsive to issues | Unpatched vulnerabilities |
| **License** | MIT, Apache 2.0, BSD | GPL, AGPL (require approval) |
| **Documentation** | Clear docs, examples, API reference | Sparse or outdated docs |
| **Breaking Changes** | Stable API, semantic versioning | Frequent major version bumps |
| **Dependencies** | Minimal, well-maintained deps | Heavy dependency tree, abandoned deps |

**Step 3: Find Real-World Usage**

Search for how the library is used in production:

```bash
# GitHub code search
site:github.com "from httpx import" language:python

# Stack Overflow
site:stackoverflow.com [python] httpx vs requests

# Blog posts / tutorials
"httpx tutorial" OR "httpx best practices" 2024
```

**Step 4: Document Your Research**

When adding a dependency, document why you chose it:

```python
# requirements.txt or pyproject.toml
httpx>=0.24.0  # Chosen over requests for async support and HTTP/2
               # Evaluated: requests, aiohttp, httpx
               # Factors: async-native, active maintenance, similar API to requests
```

Or in a code comment:

```python
# We use httpx instead of requests because:
# - Native async/await support (needed for our FastAPI backend)
# - HTTP/2 support for multiplexed connections
# - Drop-in replacement API for existing requests code
# Alternatives considered: aiohttp (more complex API), requests (no async)
import httpx
```

### Vetting Checklist

Before adding ANY new dependency, complete this checklist:

```markdown
## Dependency Vetting: [library-name]

### Basic Info
- [ ] Package name and version:
- [ ] Purpose:
- [ ] License:
- [ ] GitHub/PyPI/npm URL:

### Evaluation
- [ ] Checked at least 3 alternatives
- [ ] Weekly downloads: _____ (acceptable: >1000)
- [ ] GitHub stars: _____ (acceptable: >100)
- [ ] Last commit date: _____ (acceptable: within 6 months)
- [ ] Open issues/PRs ratio: _____ (acceptable: maintained)
- [ ] Documentation quality: [good/fair/poor]

### Security
- [ ] No critical CVEs (run `pip-audit` or `npm audit`)
- [ ] Dependencies are well-maintained
- [ ] No known security issues in GitHub Issues

### Compatibility
- [ ] Works with our Python/Node version
- [ ] No conflicting dependencies
- [ ] License is permissive (MIT/Apache/BSD)

### Decision
- [ ] Chosen because: _____
- [ ] Alternatives rejected because: _____
```

---

## 2. Before Implementing Complex Features

### When This Applies

You MUST research specifications and standards before implementing:
- Authentication/authorization (OAuth, JWT, SAML)
- Encryption/cryptography
- Network protocols (HTTP, WebSocket, gRPC)
- Data formats (JSON Schema, Protocol Buffers, Avro)
- APIs that follow standards (REST, GraphQL, OpenAPI)
- Database operations (SQL standards, transactions)
- File formats (PDF, images, audio/video)
- Security features (CORS, CSP, rate limiting)

### Minimum Research Requirements

**Step 1: Find the Specification**

Before writing any code, find the authoritative source:

| Domain | Where to Find Specs |
|--------|---------------------|
| **Web Standards** | MDN Web Docs, WHATWG, W3C |
| **Internet Protocols** | IETF RFCs (rfc-editor.org) |
| **Authentication** | OAuth 2.0 spec, OIDC spec, JWT RFC 7519 |
| **Cryptography** | NIST publications, specific algorithm papers |
| **APIs** | OpenAPI Specification, GraphQL spec |
| **Data Formats** | JSON Schema, Protocol Buffers docs |
| **Language Features** | Official language specs/docs |

**Step 2: Read the Relevant Sections**

You don't need to read entire specs, but you MUST read:
- Security considerations
- Required vs optional fields
- Error handling
- Edge cases and limitations

**Step 3: Find Reference Implementations**

Look for well-tested implementations to learn from:

```bash
# Find reference implementations
"oauth2 reference implementation" site:github.com

# Find official examples
"JWT example" site:auth0.com OR site:okta.com

# Find well-tested libraries
"python JWT library" compare pyjwt python-jose
```

**Step 4: Document Your Sources**

Always cite the specs you followed:

```python
def generate_jwt(payload: dict, secret: str) -> str:
    """
    Generate a JSON Web Token per RFC 7519.

    References:
    - JWT Spec: https://datatracker.ietf.org/doc/html/rfc7519
    - Claims: https://www.iana.org/assignments/jwt/jwt.xhtml
    - Security: https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/

    Security considerations:
    - Always use HS256 or RS256 (never 'none')
    - Include 'exp' claim for expiration
    - Validate 'iss' and 'aud' claims
    """
    ...
```

### Research Template for Complex Features

Before implementing, fill out this template:

```markdown
## Feature Research: [Feature Name]

### Specifications
- Primary spec: [URL]
- Security considerations: [URL]
- Additional references: [URLs]

### Key Requirements from Spec
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

### Security Considerations
- [ ] [Security item 1]
- [ ] [Security item 2]

### Reference Implementations Reviewed
- [Library/Project 1]: [URL] - [What I learned]
- [Library/Project 2]: [URL] - [What I learned]

### Implementation Approach
Based on research, I will:
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Test Cases from Spec
- [ ] [Test case 1 from spec examples]
- [ ] [Test case 2 from edge cases]
```

---

## 3. Examples

### Good: Thorough Research

```markdown
**Task:** Add JWT authentication to API

**Research Conducted:**

1. **Specifications Read:**
   - RFC 7519 (JWT): https://datatracker.ietf.org/doc/html/rfc7519
   - RFC 7515 (JWS): https://datatracker.ietf.org/doc/html/rfc7515
   - Auth0 JWT Security: https://auth0.com/blog/critical-vulnerabilities-in-json-web-token-libraries/

2. **Libraries Evaluated:**
   | Library | Stars | Downloads | Last Update | Decision |
   |---------|-------|-----------|-------------|----------|
   | PyJWT | 4.8k | 50M/month | 2 weeks ago | **Chosen** |
   | python-jose | 1.4k | 15M/month | 3 months ago | Good but larger |
   | authlib | 3.8k | 5M/month | 1 month ago | Overkill for our needs |

3. **Security Considerations:**
   - Using HS256 algorithm (symmetric key)
   - Including exp, iat, iss claims
   - Validating all claims on verification
   - Not storing sensitive data in payload

4. **Reference Implementation:**
   - Reviewed FastAPI's security examples
   - Reviewed Auth0's Python quickstart

**Chosen Approach:** Use PyJWT with HS256, explicit claim validation
```

### Bad: No Research

```python
# DON'T DO THIS

# Just grabbed the first library I found
import some_jwt_library

def make_token(user_id):
    # No idea what claims are needed
    # No idea about security implications
    # No idea if this library is maintained
    return some_jwt_library.encode({"user": user_id})
```

### Good: Documenting Non-Standard Choice

```python
# When you choose something unusual, explain why:

# Using 'httpcore' instead of 'requests' or 'httpx'
#
# Research: https://github.com/encode/httpcore
#
# Reason: We need low-level HTTP/1.1 and HTTP/2 connection pooling
# without the higher-level client abstractions. httpcore is the
# foundation that httpx is built on.
#
# Alternatives rejected:
# - requests: No HTTP/2, no async
# - httpx: Too high-level, we need connection-level control
# - aiohttp: Different API, less control over connection pooling
#
# Risks:
# - Less documentation than httpx
# - May need to handle more edge cases ourselves
#
# Mitigations:
# - Extensive test coverage for our HTTP layer
# - Monitoring for connection pool issues
import httpcore
```

---

## 4. Using Research Tools

IdlerGear provides tools to help with research. See `AI_INSTRUCTIONS/RECOMMENDED_TOOLS.md` for:

- **Package Registry Search**: Query PyPI, npm, crates.io
- **GitHub Code Search**: Find real-world usage patterns
- **Documentation Lookup**: Access official docs
- **Security Scanning**: Check for vulnerabilities
- **License Checking**: Verify compatibility

### Quick Commands

```bash
# Search for packages
pip index versions httpx
npm search form-validation

# Check for vulnerabilities
pip-audit
npm audit

# Find license
pip show httpx | grep License
npm view react-hook-form license

# Search GitHub for usage examples
gh search code "from httpx import" --language python --limit 50
```

---

## 5. When to Ask for Help

Research is important, but know when to escalate:

### Ask the User When:
- Multiple libraries seem equally good
- A dependency requires a copyleft license (GPL/AGPL)
- Security implications are unclear
- The spec is ambiguous or contradictory
- You find conflicting best practices

### Example:

```
I'm researching OAuth 2.0 libraries for our authentication feature.

I've narrowed it down to two options:
1. **Authlib** - Full-featured, supports all OAuth flows, 3.8k stars
2. **OAuthlib** - Lower-level, more control, 2.6k stars

Both are MIT licensed and actively maintained.

For our use case (server-side authorization code flow), either would work.
Authlib is easier to use but larger. OAuthlib requires more boilerplate
but gives us more control.

Which approach do you prefer?
```

---

## 6. Quick Reference

### Before Adding a Dependency
1. Search for 3+ alternatives
2. Check: maintenance, adoption, security, license, docs
3. Find real-world usage examples
4. Document your reasoning

### Before Complex Implementation
1. Find the specification/standard
2. Read security considerations
3. Find reference implementations
4. Document sources in code

### Red Flags (Stop and Research More)
- Library last updated >1 year ago
- <100 GitHub stars for critical functionality
- No documentation or examples
- Security vulnerabilities reported
- Copyleft license (GPL/AGPL)
- You don't understand how it works

### Green Flags (Probably Safe)
- Active maintenance (commits within 6 months)
- Good adoption (>1000 stars, >10k weekly downloads)
- Clear documentation with examples
- MIT/Apache/BSD license
- Used by major projects
- You understand the code

---

## Summary

**Research is not optional.** It's a core part of professional software development.

Every dependency and complex feature should have:
1. **Research documentation** (what you looked at)
2. **Evaluation criteria** (how you decided)
3. **Source citations** (where you learned it)

This prevents:
- Using abandoned libraries
- Security vulnerabilities
- License violations
- Incorrect implementations
- Reinventing the wheel poorly

When in doubt, research more. When still in doubt, ask.

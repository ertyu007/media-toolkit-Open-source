# Clipora Safety and Platform Reference

## Contents

1. Boundary and authorization
2. Platform integrations
3. Prohibited patterns
4. Privacy and credentials
5. Network processing
6. File and dependency safety
7. Decision checklist

## 1. Boundary and authorization

Clipora locally prepares content the user owns or may process. Conversion and importing are distinct capabilities; keep them separate in architecture, copy, tests, and claims. Do not call Clipora a universal downloader without a lawful, stable, tested path for every explicitly supported source.

Lower-risk inputs include user-created files, official exports from the user's account, explicitly permitted media, public-domain media, and content licensed for the intended use.

Require specific review for protected streams, private/paid content, cookies/tokens, bypassing restrictions, watermark/attribution removal, redistribution, or music extraction at scale. Verify current official rules when they matter; never rely on remembered platform terms.

## 2. Platform integrations

For Facebook, Instagram, YouTube, or another service:

1. Define whether the case is own-upload export, public import, account management, or something else.
2. Read current official API and terms documents.
3. Identify an official export/download/API path.
4. Define supported accounts/media and authorization.
5. Define authentication, scopes, storage, quotas, retention, deletion, and revocation.
6. Separate acquisition from conversion.
7. Add provider-specific mocks/tests and visible limitations.

Prefer official APIs and user-initiated exports. Treat scraping and undocumented endpoints as unstable and potentially noncompliant. Distinguish `Export for Reels` (local encoding constraints) from `Import from Instagram` (network, auth, and policy surface).

## 3. Prohibited patterns

Never implement DRM decryption/key extraction, paywall/login/access-control bypass, CAPTCHA evasion, stolen/shared cookie ingestion, unreviewed browser-cookie extraction, rate-limit evasion, unauthorized private-media retrieval, broad account scraping, proxy/fingerprint rotation to evade blocks, or deletion intended to conceal activity.

A provider block is a reason to stop and reassess, not to disguise the client.

## 4. Privacy and credentials

Current conversion requires no account and sends no media off-device. Preserve that property unless the user explicitly selects a clearly documented network feature.

If authentication is introduced, use official OAuth, minimum scopes, clear data-access copy, OS-backed secret storage, sign-out/revocation, and short-lived authorization state. Never log tokens, cookies, authorization headers, or signed URLs. Never put real credentials, personal media, or user paths in fixtures/issues.

## 5. Network processing

Before upload or remote processing:

- Obtain explicit consent and show what leaves the device.
- Define size/type limits, timeout, retry, cancellation, TLS validation, retention, and deletion.
- Validate content, not only extension/MIME.
- Prevent SSRF if URLs are submitted.
- Add abuse/cost controls and privacy documentation.

Do not retain a blanket “files stay on your computer” claim after adding network processing; scope it to local mode.

## 6. File and dependency safety

Treat media as untrusted parser input. Keep FFmpeg updated, pass arguments without shell interpretation, constrain temporary/output paths, bound logs/resources, and fail safely.

Never edit source. Prefer a job-owned temporary target and atomic rename after verified success when reliability requires it. Cleanup only the exact owned target; never recursively delete a destination.

For dependencies, prefer official sources, verify identity, constrain versions intentionally, record licenses, minimize privileges, and test packaged output. Record the exact FFmpeg distribution/build; licensing depends on its configuration and codecs.

## 7. Decision checklist

Before a source/import feature, answer:

- What exact authorized content is in scope?
- Which official mechanism retrieves it?
- Which current terms/docs support it?
- What scopes/credentials are required and stored?
- Does media leave the machine?
- Is DRM/access control involved?
- Who owns temporary data and cleanup?
- How are rate limits and provider failures shown?
- How can tests avoid personal data?
- What limitation/intended-use copy is required?
- What happens when the provider changes/revokes access?

Stop and request a product/legal/security decision when an answer materially changes risk or data handling.

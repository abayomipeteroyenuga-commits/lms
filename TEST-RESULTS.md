# v3 verification

Passed Python API regression: registration, authentication, roles, state/upload isolation, origin rejection, shared resources, assignment grading and course authoring.

Passed payment/email integration tests with mocked provider transport: draft/free/paid access, protected private paths, video range delivery, administrator prices, verification expiry/replay, password reset and session invalidation, provider-unconfigured errors, server-owned amounts, transaction ownership, amount mismatch, confirmed access, signed/idempotent webhooks and revocation. No real emails or transactions occurred.

Passed guest JavaScript DOM workflows: 120-course catalogue, search/bookmarks, progression, practice and quiz, resume, narration control, print, planner, notes, settings, authoring, PDF/video embedding, backup and reports.

Passed account-enabled JavaScript DOM integration against Flask: learner registration, verification request and confirmation, paywall, administrator fee, payment-return verification, unlocked PDF, assignment submission/review, course editing retaining media, and learner reports. Provider transport mocked. Found and fixed JSON-header GET validation and early-navigation initialization issues.

All 120 PDF files and 120 video files are checked for valid format; representative PDFs and slide imagery visually reviewed. Video checks confirm audio and video streams. This is DOM and API testing, not a complete real-browser/device acceptance test. Real audio playback, hosted checkout, inbox delivery, DNS/HTTPS and production restart/restore remain launch checks. Docker runtime unavailable in this workspace; supplied Docker files have not been built here.

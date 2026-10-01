# Connected Vehicle Intelligence Hackathon
## Technical Artifacts & Submission Guide

**Project:** FleetGuard — Real-Time Fleet Intelligence & Cost Optimisation Platform  
**Purpose:** Navigation guide for reviewers accessing the submission through Google Drive or GitHub.

### 1. Source code and repository

- **GitHub repository (complete source code):** https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform
- **Repository README and quick-start:** https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/README.md
- **Source code folders:** [`backend`](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/tree/main/backend), [`frontend`](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/tree/main/frontend), [`simulator`](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/tree/main/simulator), [`analytics`](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/tree/main/analytics).
- **Infrastructure and tests:** [`infra`](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/tree/main/infra), [`tests`](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/tree/main/tests).
- **Submission release tag:** [`v1.0-submission`](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/releases/tag/v1.0-submission) (source snapshot is also available under the repository's Tags page).

### 2. Submission documents

Upload these files to the Drive folder so reviewers can open them directly:

- **FleetGuard_Solution_Document.pdf** — completed solution document, prepared using the supplied hackathon template. [Open on GitHub](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/submission/FleetGuard_Solution_Document.pdf)
- **FleetGuard_Solution_Document.docx** — editable version of the completed solution document. [Open on GitHub](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/submission/FleetGuard_Solution_Document.docx)
- **fleetguard-dashboard.png** — product screenshot included in the solution document. [Open on GitHub](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/submission/images/fleetguard-dashboard.png)

### 3. Supporting technical documentation

- [Architecture decisions and diagrams](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/tree/main/docs/architecture) — system decisions and trade-offs.
- [Demo guide](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/docs/DEMO_GUIDE.md) and [synthetic data notes](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/docs/DEMO_DATA.md) — local demonstration instructions and data declaration.
- [Performance report](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/docs/PERFORMANCE.md) — measured local smoke results and explicit limits.
- [Final verification report](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/docs/FINAL_VERIFICATION.md) — checks completed and their evidence.
- [Security overview](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/docs/SECURITY.md) and [failure-testing notes](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/blob/main/docs/FAILURE_TESTING.md) — implemented controls, limitations and failure checks.
- [API documentation source and implementation](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform/tree/main/backend/app/api) — API source; the interactive OpenAPI page is available when the application is running at `/docs`.

### 4. Suggested Drive folder layout

```text
FleetGuard Hackathon Submission/
├── 00_Technical_Artifacts_Guide.pdf
├── 01_Solution_Document.pdf
├── 01_Solution_Document_Editable.docx
├── 02_Source_Code_and_Documentation/   (link to GitHub repository above)
└── 03_Product_Screenshot.png
```

Upload the PDF, editable DOCX and screenshot as files in Drive. Keep the source code in GitHub and include the repository link above; do not rely on a Drive preview of GitHub source files. Set Drive sharing to the access level requested by the organizers, then open the shared link in a signed-out/private browser window to confirm reviewer access.

### 5. Reviewer notes

- The demo uses synthetic records; no real fleet or driver information is included.
- The local producer smoke results do not demonstrate sustained 100,000 events/sec end-to-end capacity. The solution document and performance report state this limitation.
- The demo video is not included because it has not yet been recorded. Add its URL to the solution document and provide the video separately before final portal submission.

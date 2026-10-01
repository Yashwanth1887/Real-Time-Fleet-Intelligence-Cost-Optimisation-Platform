# FleetGuard submission artifacts

## Solution document

- Template-based solution document: [PDF](FleetGuard_Solution_Document.pdf)
- Editable template-filled source: [DOCX](FleetGuard_Solution_Document.docx)
- Supporting product screenshot: [Dashboard](images/fleetguard-dashboard.png)

## Technical artifacts

- **Codebase and project link:** [GitHub repository](https://github.com/Yashwanth1887/Real-Time-Fleet-Intelligence-Cost-Optimisation-Platform)
- **Project overview and quick start:** [Root README](../README.md)
- **Architecture decisions:** [Architecture index](../docs/architecture/README.md), ADR-001 through ADR-005
- **API and database:** FastAPI OpenAPI at `/docs`, SQLAlchemy models, and Alembic migrations under `backend/migrations/`
- **Demo instructions and synthetic-data declaration:** [Demo guide](../docs/DEMO_GUIDE.md), [demo data](../docs/DEMO_DATA.md)
- **Security controls and gaps:** [Security document](../docs/SECURITY.md)
- **Performance evidence and limits:** [Performance document](../docs/PERFORMANCE.md)
- **Test and end-to-end evidence:** [Final verification](../docs/FINAL_VERIFICATION.md), [failure-test record](../docs/FAILURE_TESTING.md), and [implementation progress](../docs/IMPLEMENTATION_PROGRESS.md)

## Submission notes

- Demo data is synthetic; no real driver or vehicle records are included.
- 100K vehicles, 100K events/sec, and 3× five-minute burst are targets, not demonstrated results.
- The required demo video has not been recorded; add its URL before portal submission.
- The solution document marks unmeasured performance, missing team email, and unavailable observability screenshots transparently.

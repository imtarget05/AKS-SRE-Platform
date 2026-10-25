# Pull Request Template

## 📋 Description

Please describe the changes in this PR and the reason for the change.

## 🔍 2-Reviewer Requirement

**PRs affecting core platform infrastructure must have 2 approvals from the following teams:**
- @platform-sre/approval-team
- @security-team

**Self-approval is not allowed** on changes marked with the 2-reviewer pattern.

## ✅ Checklist

- [ ] Code follows the project's coding style and conventions
- [ ] All new and modified functions have appropriate JSDoc/type comments
- [ ] Error handling is explicit and comprehensive
- [ ] No hardcoded secrets or credentials in the code
- [ ] Secrets are managed via environment variables or secret manager
- [ ] Tests exist for new functionality (80%+ coverage target)
- [ ] CI/CD pipeline passes all checks
- [ ] SBOM/provenance generated and scanned (for relevant repos)
- [ ] SLO/SLI definitions verified (for AKS-SRE-Platform)
- [ ] 2-reviewer approval obtained (for core infrastructure changes)

## 📝 Additional Notes

- Please ensure the PR description includes the relevant issue number if applicable.
- If this PR introduces user-facing changes, include screenshots or GIFs demonstrating the change.
- For AKS-SRE-Platform changes, include SLO/SLI impact assessment if applicable.
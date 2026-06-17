# 14 — Ops Runbooks & Release Process

## 14.1 Environments
- local
- staging
- prod

## 14.2 Release steps (recommended)
1. PR merged to main
2. CI runs tests + build image
3. Deploy to staging
4. Run golden corpus E2E
5. Promote to prod

## 14.3 Rollback
- redeploy previous image tag
- migrations must be reversible or forward-only with safe flags

## 14.4 Monitoring
- health endpoints
- queue backlog
- error rates

## 14.5 Backup/restore drill
- monthly restore test

## 14.6 Operational checklists
- pre-deploy checklist
- post-deploy verification

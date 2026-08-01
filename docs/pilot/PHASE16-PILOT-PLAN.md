# Phase 16 Production Pilot and General-Availability Gate

## Scope and current decision

The maintained local profile uses a reversible, measurable, noncritical synthetic document-review workflow. It validates rollout and governance mechanics only. It is not a production pilot and cannot provide E3 evidence.

Current decision: **NO-GO for general availability** until a domain owner selects and accepts a real workflow, sustained external canary outcomes are captured, and all required independent owners approve the exact immutable evidence bundle.

## Work-package status

| Package | Local implementation | Remaining external evidence |
|---|---|---|
| GA-001 | `WorkflowProfile` enforces reversible, measurable, noncritical scope and names a domain owner. | Engaged owner must select and accept a real enterprise workflow. |
| GA-002 | `PilotCriteria` freezes baseline, value, failure, duration, SLO, cost, feedback, delayed-outcome, and rollback criteria. | Owners must approve thresholds for the selected workflow. |
| GA-003 | `PilotProgram` enforces offline replay, shadow, then limited canary. | Execute those stages against qualified deployment infrastructure. |
| GA-004 | Append-only observations distinguish local from external evidence and require operator and delayed outcomes. | Capture real business outcomes over the declared duration. |
| GA-005 | Incident, provider/model/policy change, skill rollback, and disaster-recovery records are mandatory. | Independently witness exercises in the deployment environment. |
| GA-006 | Readiness requires capacity, cost, support, lifecycle, and customer-documentation references. | Validate staffing, costs, limits, and support commitments. |
| GA-007 | Product, domain, research, security, privacy, operations, and architecture approvals bind to exact fingerprints. | Named independent humans must review and approve. |

## Rollout and rollback

Promotion is ordered and fail-closed. Each stage requires at least one successful observation before moving forward. Any failure or stop condition returns the workflow to shadow/static baseline while preserving observations, audit evidence, and exercise records. Enterprise kill switches remain available to revoke affected capabilities, models, skills, actions, tenants, or the whole system.

## Capacity and cost

The workflow-specific plan must declare concurrency, latency percentile, provider and compute quotas, cost per case, review time, support load, and total-cost threshold. The local reference criteria are placeholders and are not approved production limits.

## Support

A qualified pilot requires a named domain owner, operations owner, incident escalation path, service hours, response targets, and a procedure for operator correction and adverse-outcome review.

## Lifecycle

Model, provider, policy, skill, schema, and deployment-profile changes invalidate evidence or approvals where fingerprints change. Upgrade and deprecation notices must state compatibility, migration, rollback, and support windows.

## Operator boundary

The pilot assists a noncritical workflow. Operators retain final authority, can correct or reject outputs, and must receive scoped limitations and escalation paths. The reference profile is not customer documentation for a real deployment.

## Reproduction

```powershell
$env:PYTHONPATH='src'
python scripts/audits/phase16_pilot_readiness.py
```

The command writes `docs/pilot/artifacts/phase16-local-readiness.json` and succeeds only when the local decision remains `NO-GO`, preventing reference evidence from silently becoming a production-readiness claim.

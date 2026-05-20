---
name: deploy-checker
description: Validate a Kubernetes deployment against cluster state and produce a health report
argument-hint: "<deployment-name> [namespace]"
allowed-tools: ["Bash", "Read", "Write"]
---

# Deploy Checker

Validate that a Kubernetes deployment is healthy by checking pod status, resource limits, image versions, and producing a structured health report.

## Step 1: Preflight

```bash
# Verify cluster access
kubectl cluster-info --request-timeout=5s
```

If the cluster is unreachable, stop and report the error.

## Step 2: Gather deployment data

```bash
# Get deployment details
kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" -o json

# Get pod status for the deployment
kubectl get pods -n "$NAMESPACE" -l "app=$DEPLOYMENT" -o json

# Get events for the namespace
kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' -o json
```

Parse the JSON output. Extract: replica count (desired vs ready), image versions, resource requests/limits, pod conditions, restart counts.

## Step 3: Check image versions

```bash
# Compare running image tags against the latest available
kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" -o jsonpath='{.spec.template.spec.containers[*].image}'
```

For each container image, compare the running tag against the expected version. If the deployment has multiple containers, check each one.

## Step 4: Validate resource limits

Check if every container has CPU and memory requests and limits set. Compare against known thresholds:

- Memory request < 64Mi → WARNING (too low for most workloads)
- No CPU limit set → INFO (may be intentional)
- Memory limit < memory request → ERROR (invalid configuration)

## Step 5: [LLM judgment] Analyze health signals

Read the gathered data and assess:

1. Are all replicas ready? If not, why? (CrashLoopBackOff, ImagePullBackOff, Pending)
2. Are there recent warning events? What do they indicate?
3. Are restart counts elevated? What pattern do they suggest?
4. Is the deployment progressing or stuck?

Synthesize a health verdict: HEALTHY, DEGRADED, or UNHEALTHY.

## Step 6: Produce report

Output a structured markdown report:

```markdown
# Deployment Health Report — {deployment}

| Field | Value |
|-------|-------|
| Namespace | {namespace} |
| Replicas | {ready}/{desired} |
| Status | HEALTHY / DEGRADED / UNHEALTHY |

## Containers
| Name | Image | Restarts | Status |
|------|-------|----------|--------|

## Resource Limits
| Container | CPU Req | CPU Limit | Mem Req | Mem Limit | Issues |
|-----------|---------|-----------|---------|-----------|--------|

## Events
<recent warning/error events>

## Verdict
<LLM assessment from Step 5>
```

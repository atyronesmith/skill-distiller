---
name: go-error-patterns
description: Reference guide for Go error handling patterns in Kubernetes operators
allowed-tools: ["Read"]
---

# Go Error Handling Patterns

Reference guide for consistent error handling across Kubernetes operator codebases.

## Wrapping Errors

Always wrap errors with context using `fmt.Errorf`:

```go
// Bad
return err

// Good
return fmt.Errorf("failed to create configmap %s: %w", name, err)
```

## Sentinel Errors

Use `errors.Is` for sentinel errors:

```go
if errors.Is(err, ErrNotFound) {
    return ctrl.Result{}, nil
}
```

## Error Groups

For operations that can partially fail:

```go
var errs []error
for _, item := range items {
    if err := process(item); err != nil {
        errs = append(errs, fmt.Errorf("item %s: %w", item.Name, err))
    }
}
return errors.Join(errs...)
```

## Controller-Runtime Patterns

### Get/NotFound

```go
instance := &v1beta1.MyResource{}
err := r.Client.Get(ctx, req.NamespacedName, instance)
if err != nil {
    if apierrors.IsNotFound(err) {
        return ctrl.Result{}, nil
    }
    return ctrl.Result{}, err
}
```

### Requeue vs Return Error

- Return `ctrl.Result{}, err` for transient errors (API server timeout)
- Return `ctrl.Result{RequeueAfter: 10 * time.Second}, nil` for expected waits
- Return `ctrl.Result{}, nil` for terminal states (resource deleted)

# PR Explainer posting test

This file exists only to give the PR Explainer service a diff to post review comments on.

## Sample function

```python
def total(items):
    result = 0
    for item in items:
        result += item.price * item.quantity
    return result
```

## Notes

- Line comments should land on the lines above.
- Lines outside the diff should become file-level comments.
- Replies and resolve should work on threads created here.


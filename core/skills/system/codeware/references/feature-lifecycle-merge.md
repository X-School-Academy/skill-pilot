# Feature Lifecycle: Merge

Use when implementation, review, and testing are complete.

## Steps

1. Read the implementation context and confirm the feature is ready to merge.
2. Merge the feature branch back to `user` and switch the working copy to `user`.
3. Use agent skill `skill-pilot-freeze-core-feature` to freeze the feature into `core/features/`.
4. Delete the feature branch after a successful merge.

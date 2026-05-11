# Concat Number String

Use this action when a workflow test node needs to combine a number and a string into one plain-text result.

## Steps

### Step 1: Read Inputs

Read the user-provided number and the user-provided string.

### Step 2: Concatenate

Combine the number and string into one string.

Use the direct input order:

1. number
2. string

Do not add separators unless the user explicitly requests one.

### Step 3: Return the Result

Return the combined string as plain text.

## Expected Output

Output result as plain text. If the user asked to save it to a file, write it there.

- One concatenated string that contains the number followed by the string.

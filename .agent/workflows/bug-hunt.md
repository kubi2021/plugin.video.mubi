---
description: bug hunting
---

# Bug Hunting Workflow

You are an expert Senior Software Development Engineer in Test (SDET) with a security-focused, "adversarial" mindset. Your goal is to find potential bugs, logical fallacies, and unhandled edge cases.

## Bug Hunting Level

This plugin uses **Level 2 (User Experience Focus)** - optimal reliability for media consumption while maintaining development efficiency.

### Priority Levels

**High Priority (User-Blocking):**
- Crashes preventing plugin startup
- Complete playback failures
- Library sync failures leaving empty library
- Authentication loops
- File system errors corrupting user data

**Medium Priority (User-Frustrating):**
- Intermittent playback failures
- Slow/unresponsive UI
- Incorrect metadata display
- Partial sync failures
- Poor error messages

**Low Priority (Edge Cases):**
- Rare configuration combinations
- Non-critical performance issues
- Cosmetic UI glitches

---

## Analysis Process

### 1. Analyze Intent and User Flow
Describe the code's intended purpose and expected "happy path" user flow.

**Primary User Flows:**
- Install → Configure → Browse → Play
- Sync library → Browse local → Play from library
- Search → Play directly

### 2. Identify Implicit Assumptions
List assumptions the code makes about inputs, environment, or program state.

**Common Assumptions to Validate:**
- Network connectivity available
- API returns expected data formats
- File system has write permissions
- User credentials remain valid
- Metadata fields contain expected types

### 3. Brainstorm Failure Modes

**Data Type & Format:**
- `None` in required fields
- Empty strings vs missing keys
- Type mismatches (int vs str)
- Malformed JSON
- Unicode in titles
- Very long strings

**Boundary Violations:**
- Empty/single-item libraries
- Thousands of films
- Network timeouts
- Disk space exhaustion
- Invalid date formats

**Logic & State Corruption:**
- Multiple simultaneous syncs
- Interrupted operations
- Corrupted config files
- Invalid auth states
- Cache inconsistencies

**Concurrency Issues:**
- Multiple threads accessing same data
- Race conditions in file writes

### 4. Propose Bug-Hunting Test Cases
For each potential bug, propose a test case with:
- **Input**: The test data
- **Action**: What to execute
- **Expected Buggy Behavior**: What would happen if bug exists

---

## Your Task 🐞

Apply this bug-hunting process to the provided code. Present findings in a structured report following the steps above.

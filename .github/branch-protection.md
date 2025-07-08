# Branch Protection Configuration

This document describes the recommended branch protection settings for this repository.

## Recommended Settings

### Main Branch Protection

Navigate to **Settings > Branches** and add a rule for `main` with these settings:

#### Pull Request Requirements
- ✅ **Require a pull request before merging**
- ✅ **Require approvals**: 1 (for team repositories)
- ✅ **Dismiss stale PR approvals when new commits are pushed**
- ✅ **Require review from code owners** (if you have a CODEOWNERS file)

#### Status Check Requirements  
- ✅ **Require status checks to pass before merging**
- ✅ **Require branches to be up to date before merging**

**Required status checks:**
- `test (3.8)` - Python 3.8 tests
- `test (3.9)` - Python 3.9 tests  
- `test (3.10)` - Python 3.10 tests
- `test (3.11)` - Python 3.11 tests

#### Additional Restrictions
- ✅ **Restrict pushes that create files larger than 100 MB**
- ✅ **Require signed commits** (optional, for extra security)
- ✅ **Include administrators** (applies rules to repo admins too)

#### Merge Options
- ✅ **Allow merge commits**
- ✅ **Allow squash merging** 
- ✅ **Allow rebase merging**
- ✅ **Automatically delete head branches**

## What This Prevents

With these settings enabled:

❌ **Cannot merge if tests fail**
❌ **Cannot merge without PR review** 
❌ **Cannot merge outdated branches**
❌ **Cannot push directly to main**
❌ **Cannot merge large files**

## Benefits

✅ **Code Quality**: All code is tested before merge
✅ **Code Review**: All changes are reviewed
✅ **Stability**: Main branch always has passing tests
✅ **History**: Clean commit history with meaningful PRs
✅ **Security**: Prevents accidental direct pushes

## Testing the Protection

1. Create a test branch: `git checkout -b test-protection`
2. Make a change that breaks tests
3. Push and create a PR
4. Verify that GitHub blocks the merge until tests pass

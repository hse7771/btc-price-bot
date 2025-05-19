# 🚀 Commit Message Guide

Following a structured commit message format helps keep your project history **clear, readable, and maintainable**. This guide follows the **Conventional Commits** standard.

---

## ✅ **Commit Message Format**
Each commit message should follow this format:

```
<type>(<scope>): <short description>

[Optional: More details in multiple lines]

[Optional: BREAKING CHANGE: description]
[Optional: Closes #issue-number]
```

### **Example Commit Messages**
✅ Feature addition:
```
feat(auth): add JWT-based authentication
```

✅ Bug fix:
```
fix(ui): resolve navbar alignment issue
```

✅ Documentation update:
```
docs(readme): add setup instructions
```

✅ Breaking change:
```
feat(api): migrate to v2 API

BREAKING CHANGE: Old API endpoints have been removed.
```

✅ Reference an issue:
```
fix(database): resolve connection timeout issue

Closes #123
```

---

## 🔥 **Allowed Commit Types**

| Type       | Purpose |
|------------|---------|
| `feat`     | A new feature |
| `fix`      | A bug fix |
| `docs`     | Documentation changes |
| `style`    | Code style (whitespace, formatting) |
| `refactor` | Code restructuring (no behavior change) |
| `perf`     | Performance improvements |
| `test`     | Adding/updating tests |
| `chore`    | Maintenance tasks (CI/CD, dependencies) |
| `build`    | Changes to build system or dependencies |
| `ci`       | Changes to CI/CD workflows |

---

## 🔄 **Branching Strategy**

Using a structured branching strategy helps maintain a clean and manageable Git history. Below is a recommended Git branching workflow:

### 1️⃣ **Main Branches**
- `main`: The stable, production-ready branch.
- `develop`: The integration branch where features are merged before release.

### 2️⃣ **Feature Branches**
- Use `feature/<feature-name>` for new features.
- Example: `feature/add-user-authentication`
- Rebase onto `develop` before merging.
- Merge into `develop` using a fast-forward or Pull Request.

### 3️⃣ **Bug Fixes**
- Use `bugfix/<bug-description>` for fixing bugs in `develop`.
- Example: `bugfix/fix-login-error`
- Rebase onto `develop` and merge into `develop`.

### 4️⃣ **Release Branches**
- Use `release/<version>` for preparing a new release.
- Example: `release/v1.2.0`
- Merge into both `main` and `develop`.

### 5️⃣ **Hotfixes (Critical Production Fixes)**
- Use `hotfix/<description>` for urgent fixes on `main`.
- Example: `hotfix/security-patch`
- Merge into both `main` and `develop`.

### **Branching Workflow Example**
```bash
# Create a new feature branch
git checkout -b feature/add-payment-gateway

# Work on the feature, commit changes
git add .
git commit -m "feat(payment): integrate new payment gateway"

# Rebase onto latest develop to keep history clean
git fetch origin
git rebase origin/develop

# Push rebased branch
git push origin feature/add-payment-gateway

# Merge into develop (fast-forward preferred)
git checkout develop
git merge feature/add-payment-gateway

git push origin develop
```

🔁 **Alternatively, you can open a Pull Request (PR)** into `develop` after pushing the rebased branch.

---

## 🔄 **Commit Workflow**

### 1️⃣ **Staging Changes**
Add files before committing:
```bash
git add .
```

### 2️⃣ **Making a Commit**
```bash
git commit -m "feat(auth): add JWT authentication"
```

OR use an editor for detailed messages:
```bash
git commit
```
(This will open a text editor where you can write a structured commit message.)

### 3️⃣ **Pushing Changes**
```bash
git push origin <branch-name>
```

---

## ⚡ **Best Practices**
✔️ Use **imperative tense** (`fix` instead of `fixed` or `fixes`).  
✔️ Keep the subject line **short (~50 characters max)**.  
✔️ Limit the body lines to **~72 characters per line**.  
✔️ Reference issues when relevant (`Closes #123`).  
✔️ Use `--amend` to fix the last commit if needed:
```bash
git commit --amend
```

---

## 🛠️ **Fixing and Adjusting Mistakes in Git**

A collection of useful workflows for handling common mistakes and cleanup in your Git history.

### 🧩 Handling Mistaken Changes on the Wrong Branch

Sometimes you might accidentally make changes on a feature branch that belong on the base branch (e.g., `main` or `develop`). You may even have **multiple files**, where:
- Some files should move entirely
- Some files need only partial changes moved
- Other changes should remain in your current feature branch

This section helps you cleanly transfer only the changes you want — and leave the rest untouched.

#### ✅ Goal
- Move specific full and partial changes to the base branch
- Leave unrelated or unfinished changes safely on the feature branch

#### 🛠 Steps

1. **Stage the exact changes to move:**
   - Stage full files:
     ```bash
     git add path/to/fileA.py
     ```
   - Stage part of a file interactively:
     ```bash
     git add -p path/to/fileB.py
     ```

2. **Commit those staged changes temporarily:**
   ```bash
   git commit -m "TEMP: move to base branch"
   ```

3. **(Optional but safe) Stash remaining changes:**
   ```bash
   git stash -m "WIP: keep remaining feature work"
   ```

4. **Switch to the base branch:**
   ```bash
   git checkout develop
   ```

5. **Cherry-pick the temp commit:**
   ```bash
   git cherry-pick <commit-hash>
   ```

   Get the commit hash via:
   ```bash
   git log --oneline
   ```

6. **Reword the commit message:**
   ```bash
   git commit --amend -m "feat(x): move changes from feature branch"
   ```

7. **Return to your feature branch:**
   ```bash
   git checkout feature/your-branch
   ```

8. **Remove TEMP commit from feature branch:**
   ```bash
   git reset --hard HEAD~1
   ```

9. **(If stashed) Restore your remaining work:**
   ```bash
   git stash pop
   ```

✅ You’ve now surgically moved only the intended changes to the correct branch — without losing or polluting your in-progress work.


---


### 🔀 Moving Last N Commits to a Different Branch

Sometimes you make commits on the wrong branch by accident. This guide explains how to move the last N commits from your current branch to another one (e.g., `develop`) and remove them from the current branch cleanly.

#### ✅ Steps to Move the Last 2 Commits to Another Branch

1. **Check the last two commits:**
   ```bash
   git log --oneline -n 2
   ```
   Copy the commit hashes of the last two commits (e.g., `abc1234`, `def5678`).

2. **Switch to the target branch (e.g., `develop`):**
   ```bash
   git checkout develop
   ```

3. **Cherry-pick the commits onto the target branch:**
   ```bash
   git cherry-pick abc1234 def5678
   ```

4. **Return to your original branch:**
   ```bash
   git checkout feature/your-branch
   ```

5. **Remove the last 2 commits from the current branch:**
   ```bash
   git reset --hard HEAD~2
   ```

✅ The commits are now part of the correct branch and removed from the original one.

---

### ✍️ Editing Past Commits

#### ✅ Edit last commit (not pushed):
```bash
git commit --amend
```

#### ✅ Edit older commits:
```bash
git rebase -i HEAD~N  # Replace N with number of commits back
```
Then change `pick` to `reword`, save, and update messages.
This command opens an interactive rebase menu where you can modify multiple previous commits. Each commit will be listed with the word `pick` next to it. To edit a commit message, change `pick` to `reword`, then save and close the editor. Git will then prompt you to edit the commit message for each `reword` entry.

### **Example Usage:**
If you want to edit the last 3 commits:
```bash
git rebase -i HEAD~3
```
This will open a list like this:
```
pick 1234567 feat: add login feature
pick 89abcde fix: correct typo in docs
pick 456789a chore: update dependencies
```
Change it to:
```
reword 1234567 feat: add login feature
pick 89abcde fix: correct typo in docs
pick 456789a chore: update dependencies
```
After saving, Git will open the commit message editor for the first commit (`1234567`), allowing you to edit it.

⚠️ **If you've already pushed, use `git push --force` carefully!**

---

### 🧱 Attaching New Changes to a Previous Commit

Sometimes you realize that a new change belongs in a previous commit — not the last one — but you already have unrelated work in progress that you don't want to lose or mix.

This section explains how to isolate and attach your change to a past commit safely, even when your working directory contains other edits.

#### ✅ Goal
- Attach a new change to a specific older commit (e.g., 2 commits ago)
- Leave unrelated in-progress changes untouched

#### 🛠 Steps

1. **Stage only the file (or chunk) you want to attach:**
   ```bash
   git add <file>
   ```
   Or, to selectively stage parts:
   ```bash
   git add -p <file>
   ```

2. **Temporarily commit the staged change:**
   ```bash
   git commit -m "TEMP: will be squashed into earlier commit"
   ```

3. **Stash all unrelated, unstaged changes:**
   ```bash
   git stash push -m "temp: unrelated work"
   ```

4. **Start an interactive rebase, going far enough back to include the target commit and your TEMP commit:**
   ```bash
   git rebase -i HEAD~N  # e.g., HEAD~3
   ```

5. **Reorder and change the rebase lines:**
   Move the `TEMP` commit below the commit it should be merged into, and change `pick` to `fixup` (or `squash` if you want to edit the message).

   Example:
   ```
   pick abc1234 feat: add login endpoint
   fixup def5678 TEMP: will be squashed into earlier commit
   pick 7890abc feat: add get-tier logic
   ```

6. **Let Git apply the rebase and squash the commits.**

7. **Restore your stashed unrelated changes:**
   ```bash
   git stash pop
   ```

> ⚠️ If you've already pushed the branch, don't forget to force-push after rebase:
> ```bash
> git push --force-with-lease
> ```

✅ You’ve now cleanly inserted your change into the correct commit — without touching or losing any unrelated work!

---

### 🔁 Renaming a Branch

If you realize the branch name is incorrect or unclear:

#### ✅ Rename current branch:
```bash
git branch -m new-branch-name
```

#### ✅ Rename another branch:
```bash
git branch -m old-name new-name
```

#### ✅ Push renamed branch to remote:
```bash
git push origin new-branch-name
```

#### ✅ Delete old branch from remote (optional):
```bash
git push origin --delete old-name
```

Use this if you've already pushed the old name and want to remove it.

---

## 🎯 **Final Notes**
By following this guide, your commit history will be clean, structured, and easy to understand. This helps with debugging, collaboration, and automation (e.g., changelogs, versioning).

🚀 **Happy coding!**


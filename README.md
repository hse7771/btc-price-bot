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

Sometimes you might accidentally make changes on a feature branch that belong on the base branch (e.g., `develop`). For example, you updated `README.md` while working on a feature, but now want to commit that change to `develop` instead.

#### ✅ Goal
- Move only `README.md` changes to the base branch
- Keep other in-progress changes on the current feature branch

#### 🛠 Steps
```bash
# 1. Stage only the file to move
git add README.md

# 2. Stash only the staged part
git stash push -m "Move README to develop" --staged

# 3. Switch to base branch
git checkout develop

# 4. Apply the stash
git stash pop

# 5. Commit on base branch
git add README.md
git commit -m "docs(readme): update commit and branching guide"
git push origin develop

# 6. Return to feature branch
git checkout feature/your-branch
```

For partial changes in the same file (e.g., `main.py`), use patch mode:
```bash
git add -p main.py
```
This allows you to select only the relevant changes.

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


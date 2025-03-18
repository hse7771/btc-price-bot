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
- Merge into `develop` when complete.

### 3️⃣ **Bug Fixes**
- Use `bugfix/<bug-description>` for fixing bugs in `develop`.
- Example: `bugfix/fix-login-error`
- Merge into `develop`.

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

# Push to remote
git push origin feature/add-payment-gateway

# After completing, merge into develop
git checkout develop
git merge feature/add-payment-gateway
git push origin develop
```

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

## 🚀 **Editing Past Commits**
If you need to edit an earlier commit message:

✅ **Last commit (not pushed yet):**
```bash
git commit --amend
```

✅ **Older commits:**
```bash
git rebase -i HEAD~N  # Replace N with the number of commits back you want to edit
```
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

## 🎯 **Final Notes**
By following this guide, your commit history will be clean, structured, and easy to understand. This helps with debugging, collaboration, and automation (e.g., changelogs, versioning).

🚀 **Happy coding!**


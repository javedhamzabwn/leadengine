#!/bin/bash
set -e

title() {
    echo -e "\n\n=== $(echo $1 | tr '[:lower:]' '[:upper:]') ===\n"
}

echo "GitHub Repository Setup for LeadEngine"
echo "======================================"
echo

# 1. Check if GitHub CLI is available
if ! command -v gh &> /dev/null; then
    echo "ERROR: GitHub CLI (gh) not found. Please install it from https://cli.github.com/manual/installation"
    exit 1
fi

title "Git Configuration"
read -p "Enter your GitHub username: " github_username
read -p "Enter your GitHub email: " github_email

git config --global user.name "$github_username"
git config --global user.email "$github_email"
git config --global credential.helper store

# 2. Configure GitHub token (for authentication)
echo -n "Enter your GitHub Personal Access Token: "
read -s github_token

echo

echo "$github_token" | gh auth login --with-token
echo "✅ Authenticated with GitHub"

# 3. Check current git status
title "Current Repository Status"
if [ -d ".git" ]; then
    echo "✅ Git repository already exists"
    git status --short
else
    echo "📁 Creating new Git repository..."
    git init
    echo "✅ Git repository initialized"
fi

# 4. Add project files to git
# Add all important project files
title "Adding Project Files"
git add .

# 5. Commit the initial project
echo "Enter commit message (default: 'Initial LeadEngine project'):"
read -p "Commit message: " commit_msg

if [ -z "$commit_msg" ]; then
    commit_msg="Initial LeadEngine project"
fi

git commit -m "$commit_msg"
echo "✅ Code committed"

# 6. Create remote repository
echo ""
title "GitHub Repository Setup"
echo "You now need to create the repository on GitHub.com"
echo "Go to https://github.com/new"
echo ""
read -p "Enter your GitHub repository name (e.g., leadengine): " repo_name
read -p "Is the repository public? (y/n) [y]: " is_public

if [ -z "$is_public" ] || [[ "$is_public" =~ ^[Yy]$ ]]; then
    visibility="public"
else
    visibility="private"
fi

echo

echo "Creating repository '$repo_name' on GitHub..."
gh repo create "$repo_name" --$visibility --source=. --remote=origin

echo "✅ Remote repository created"
echo "Repository URL: $(gh repo view --json url --jq '.url')"

# 7. Push to remote
echo ""
title "Pushing to Remote"
echo "Pushing to origin..."
git push -u origin main
echo "✅ Code pushed to remote"

# 8. Setup git credentials
>&2 echo "\n=== Git Configuration Check ==="
gh auth status >&2
echo "  You can use 'gh repo view' for repo info"
echo "  You can use 'gh issue create' to manage issues"
echo "  You can use 'gh pr create' to create pull requests"

echo "\n✅ Setup complete!"
echo "Your repository is ready at: $(gh repo view --json url --jq '.url')"

echo "\n=== Next Steps ==="
echo "1. Visit your repository on GitHub"
echo "2. Configure CI/CD (if needed)"
echo "3. Create branches for development"
echo "4. Set up issues and pull requests"
echo "5. Deploy to hosting if needed"
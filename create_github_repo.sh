#!/bin/bash
set -e

title() {
    echo -e "\n\n=== $(echo $1 | tr '[:lower:]' '[:upper:]') ===\n"
}

# Check if GitHub CLI is available
if ! command -v gh &> /dev/null; then
    echo "ERROR: GitHub CLI (gh) not found. Please install it from https://cli.github.com/manual/installation"
    exit 1
fi

title "Authentication"
echo "Please authenticate with GitHub:"
echo "  Run: gh auth login"
echo "  Choose the option for creating a new token if prompted"
echo "  Select the appropriate scope (all would work)"
echo

echo "After authentication, run this script again."
echo "Make sure you are in the project directory (/d/wsl-data)"
echo

# Check current git setup
if ! git config --global user.name > /dev/null 2>&1; then
    echo "WARNING: Git user.name not set"
    read -p "Enter your GitHub username: " github_username
    git config --global user.name "$github_username"
fi

if ! git config --global user.email > /dev/null 2>&1; then
    echo "WARNING: Git user.email not set"
    read -p "Enter your GitHub email: " github_email
    git config --global user.email "$github_email"
fi

title "Current Repository Status"
if [ -d ".git" ]; then
    echo "✅ Git repository exists"
    git log --oneline --decorate -5
else
    echo "📁 No Git repository found"
    echo "Initialize first: git init"
fi

title "Create Repository on GitHub"
echo "Please visit: https://github.com/new"
echo "Create a repository named: leadengine"
echo "Then copy the HTTPS or SSH clone URL"
echo

read -p "Enter the clone URL: " remote_url

if [ -z "$remote_url" ]; then
    echo "ERROR: No remote URL provided"
    echo "Please provide a valid GitHub repository URL"
    exit 1
fi

# Add remote and push
title "Push to GitHub"
git remote add origin "$remote_url"
git branch -M main
echo "Pushing to remote..."
git push -u origin main
echo "✅ Successfully pushed to GitHub!"
echo "Repository: $remote_url"

echo "\n=== Repository Links ==="
echo "View on GitHub: $remote_url"
echo "Git clone command: git clone \"$remote_url\""
echo

echo "=== Repository Management ==="
echo "View issues: gh issue list"
echo "Create issue: gh issue create"
echo "View PRs: gh pr list"
echo "Create PR: gh pr create"
echo "View branches: gh branch list"
echo "Set up Actions: Check .github/workflows/"

echo "\n=== Next Steps ==="
echo "1. Visit your GitHub repository"
echo "2. Add .gitignore if needed"
echo "3. Configure CI/CD (if needed)"
echo "4. Set up releases, tags"
echo "5. Invite collaborators"
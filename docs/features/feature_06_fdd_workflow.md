# Feature 06: Feature-Driven Development (FDD) Workflow

Agentic OS was not only built with strict architectural rules, but it also mandates strict development workflow constraints for all AI agents contributing to its codebase.

## 1. GitHub CLI & Issue Tracking
Agents are strictly prohibited from writing arbitrary code without direction. 
**Rule 1: NEVER write code without an active, assigned GitHub Issue.**
Before implementing *any* feature, bug fix, or documentation, the agent must execute `gh issue create` to officially track the scope of the work in the repository.

## 2. Strict Branch Management
Direct commits to the `main` branch are disabled. The workflow enforces the following exact cycle:
1. Create a tracking issue.
2. Checkout a dedicated feature branch (`git checkout -b feat/issue-<number>-<desc>`).
3. Formulate an Implementation Plan and request user approval.
4. Execute code changes and commit.
5. Create a GitHub Pull Request (`gh pr create`).
6. Merge the PR and instantly delete the feature branch (`gh pr merge --merge --delete-branch`).

This paradigm guarantees that the OS's repository history is completely immutable, traceable, and rollback-ready in the event of a catastrophic AI hallucination.

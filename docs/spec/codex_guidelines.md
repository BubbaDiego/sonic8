# Codex Instruction Guidelines

These guidelines describe how to write instructions that will be consumed by both GPT and Codex, with a special focus on the **Codex block** format.

---

## 1. General Principles

- Each response may contain:
  - Normal prose intended for a human (you).
  - A **single Codex block** intended for Codex.

- Only instructions meant for Codex should go **inside** the Codex block.  
  Notes about verification, caveats, or commentary for the human should live **outside** the block.

- Assume Codex is *dumb but obedient*:
  - Be explicit about scope and size of changes.
  - Different runs with the same Codex block should produce similar results.
  - If one run makes tiny edits and another rewrites the whole project, the instructions were too vague.

---

## 2. Codex Block Format

A Codex block is delimited with the following exact markers:

- **Begin marker**

  ```text
  💎 BEGIN CODEX BLOCK 💎


End marker

🎯END CODEX BLOCK 🎯


Rules:

There must be exactly one Codex block per GPT instruction response.

Do not open multiple blocks for separate files; describe all changes for all files inside the single block.

Any extra notes for GPT (or for a human reviewer) must go before or after the Codex block, not inside it.

3. Template for a Codex Block

Inside the Codex block, follow this structure:

3.1 Overview

Describe, in 1–3 sentences:

What problem we are solving, or

What new feature or behavior we are adding.

This gives Codex context for why the changes exist.

3.2 Files Impacted

List all files that will be added, modified, or deleted.

Requirements:

Always use full, exact paths from the project root.
Example:

backend/core/xcom_core/xcom_bridge.py
docs/spec/codex_guidelines.md


Do not assume Codex knows the working directory.

3.3 Changes per File

For each file listed above, describe the changes in enough detail that Codex can implement them deterministically. Examples of what to specify:

New functions, classes, or components and their responsibilities.

Edits to existing functions (what to add/remove/modify).

Any new configuration keys, constants, or environment variables.

Expected inputs/outputs for new behaviors.

Avoid vague instructions like “clean this up” or “refactor as needed”.

3.4 Resulting Behavior

Describe how the system should behave after the changes, in a way that allows Codex (and humans) to sanity‑check the design:

What new capabilities exist?

What should no longer happen?

How can a developer verify the behavior manually (e.g., which command to run, which UI to open)?

4. Codex-Specific Guidelines

These rules are about how Codex should modify the codebase when following a block.

Do not introduce new files unless explicitly instructed.
Codex’s job is to integrate with the existing architecture, not to invent a new one.

Stay within the declared scope.
Only touch the files listed in “Files Impacted”, unless the instructions explicitly allow additional files.

Prefer minimal, targeted changes.
Only perform larger refactors when the block clearly authorizes them.

Fail loudly instead of guessing.
If Codex cannot confidently complete the tasks based on the instructions:

It should stop, report what is unclear, and avoid speculative changes.

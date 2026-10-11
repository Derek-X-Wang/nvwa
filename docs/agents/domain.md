# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

This repo uses a single-context layout:

- `GLOSSARY.md` at the repo root holds the domain vocabulary.
- `docs/adr/` holds Architecture Decision Records (ADRs), which record significant design decisions.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root.
- **`docs/adr/`**: read ADRs that touch the area you are about to work in.

If any of these files do not exist, **proceed silently**. Do not flag their absence or suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions get resolved.

## File structure

```text
/
├── GLOSSARY.md
└── docs/adr/
    └── 0001-<decision>.md
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, or a test name), use the term as defined in `GLOSSARY.md`. Do not drift to synonyms the glossary explicitly avoids.

If the concept you need is not in the glossary yet, either you are inventing language the project does not use (reconsider), or there is a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding it:

> Contradicts ADR-0007 (event-sourced orders), but worth reopening because…

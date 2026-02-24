# Claude Code Context: {Project Name}

## Project Overview

**Purpose**: {One sentence. What this project does and for whom.}

**Phase**: {Current phase of work}

**Constitution**: `specs/constitution.md` — Read before any work. Governs all process, TDD, and quality requirements.

## Technology Stack

- **Language**: {e.g., Python 3.12+}
- **Key Libraries**: {e.g., Polars, FastAPI, pytest + hypothesis + mutmut}
- **Storage**: {e.g., Parquet with zstd compression}
- **Package Management**: {e.g., UV. No pip install without UV wrapper.}

## Environment

{Minimal instructions for running code — venv activation, run commands. Keep to 5 lines or fewer.}

## Architecture

{Structural overview of key directories and their single responsibilities. Not a full tree — just enough for the agent to navigate.}

## Domain Context

{For low-familiarity projects only. What domain this project operates in, what makes it unusual, and where the agent should expect its intuitions to be unreliable. Reference Constitution Principle V.}

## Learned Rules

{Project-specific rules discovered during development. Accumulated from retrospectives and debugging sessions. Each rule should be one line.}

## DO NOT

{Short, sharp prohibitions specific to this project.}

## Current Focus

{What the agent should expect to be working on. Updated when features change.}

## Navigation

{Pointers to key spec and documentation files.}
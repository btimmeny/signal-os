# Plan: Dashboard GPT Training Fix

## Objective

Strengthen the GPT training instructions in the OpenAPI spec to enforce the grouped dashboard format and explicitly prohibit flat numbered lists. This is an instruction-only update with no code changes.

## Prerequisites

- Access to the Signal OS repository
- Feature 009 (Task Dashboard) already merged

## Steps

### 1. Analyze the Problem

1. Review GPT output showing flat numbered list instead of grouped sections
2. Identify that OpenAPI spec instructions are not strong enough to override GPT default behavior

### 2. Strengthen Top-Level Instructions

1. Open `openapi.yaml`
2. Update the top-level API description with an explicit output template
3. Add clear statement that flat numbered list is WRONG
4. Include example showing the exact grouped format

### 3. Strengthen Endpoint Description

1. Update `/commitments/dashboard` endpoint description
2. Add detailed formatting rules with example output
3. Emphasize NEVER flattening to a numbered list

### 4. Add Redirect Warnings

1. Update `/commitments/open` endpoint description — tell GPT to use dashboard instead
2. Update `/commitments/priorities` endpoint description — same redirect

### 5. Update Route Docstring

1. Open `app/main.py`
2. Update `/commitments/dashboard` route docstring with grouped format example

### 6. Verify

1. Run `pytest -v` — all existing tests must still pass (no functional changes)
2. Commit, push, create PR

### 7. Note

This fix was not sufficient — GPT continued to flatten JSON responses. Feature 011 (plain text endpoint) was the definitive solution.

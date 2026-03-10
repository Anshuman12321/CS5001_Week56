"""
Improver - critiques and improves existing issues/PRs.
"""
import json
from agent.llm import LLMClient


class ContentImprover:
    """Improves existing issues and PRs."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def improve_issue(self, title: str, body: str | None) -> dict:
        """Improve an issue - returns critique and improved version."""
        prompt = self._build_issue_prompt(title, body)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        return self._normalize_result(parsed)

    def improve_pr(self, title: str, body: str | None) -> dict:
        """Improve a PR - returns critique and improved version."""
        prompt = self._build_pr_prompt(title, body)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        return self._normalize_result(parsed)

    def _build_issue_prompt(self, title: str, body: str | None) -> str:
        """Build prompt for improving issue."""
        return f"""
Improve this GitHub Issue.

Original:
Title: {title}
Body:
{body or "(empty)"}

Do two things:
1. Critique: Find problems (unclear info, vague language, weak criteria)
2. Improve: Suggest better version

Improved version must have:
  ## Problem Description
  ## Evidence
  ## Acceptance Criteria
  (bullet list)
  ## Risk Level
  (low, medium, or high)

Rules:
- Don't invent repo facts
- If evidence missing, say confirmation needed
- Make criteria testable
- Stay grounded in original

Return JSON:
{{
  "critique": ["specific problem"],
  "suggested_acceptance_criteria": ["testable criterion"],
  "improved_title": "better title",
  "improved_body": "## Problem Description\\n...\\n\\n## Evidence\\n...\\n\\n## Acceptance Criteria\\n- ...\\n\\n## Risk Level\\nlow|medium|high"
}}
""".strip()

    def _build_pr_prompt(self, title: str, body: str | None) -> str:
        """Build prompt for improving PR."""
        return f"""
Improve this GitHub PR.

Original:
Title: {title}
Body:
{body or "(empty)"}

Do two things:
1. Critique: Find problems (unclear info, vague language, weak criteria, missing tests)
2. Improve: Suggest better version

Improved version must have:
  ## Summary
  ## Files Affected
  ## Behavior Change
  ## Test Plan
  ## Acceptance Criteria
  (bullet list)
  ## Risk Level
  (low, medium, or high)

Rules:
- Don't invent repo facts
- If files/tests unknown, say confirmation needed
- Make criteria testable
- Stay grounded in original

Return JSON:
{{
  "critique": ["specific problem"],
  "suggested_acceptance_criteria": ["testable criterion"],
  "improved_title": "better title",
  "improved_body": "## Summary\\n...\\n\\n## Files Affected\\n...\\n\\n## Behavior Change\\n...\\n\\n## Test Plan\\n...\\n\\n## Acceptance Criteria\\n- ...\\n\\n## Risk Level\\nlow|medium|high"
}}
""".strip()

    def _parse_response(self, text: str) -> dict:
        """Parse JSON from response."""
        cleaned = text.strip()
        
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        
        if start == -1 or end == -1:
            raise ValueError("No JSON found in improver response")
        
        return json.loads(cleaned[start:end+1])

    def _normalize_result(self, parsed: dict) -> dict:
        """Normalize and validate improvement result."""
        critique = parsed.get("critique", [])
        criteria = parsed.get("suggested_acceptance_criteria", [])
        new_title = str(parsed.get("improved_title", "")).strip()
        new_body = str(parsed.get("improved_body", "")).strip()

        if not isinstance(critique, list):
            critique = [critique]
        if not isinstance(criteria, list):
            criteria = [criteria]

        critique_clean = [str(c).strip() for c in critique if str(c).strip()]
        criteria_clean = [str(c).strip() for c in criteria if str(c).strip()]

        if not critique_clean:
            critique_clean = ["Original needs clearer structure and detail"]

        if not new_title:
            raise ValueError("Improved title cannot be empty")
        if not new_body:
            raise ValueError("Improved body cannot be empty")

        return {
            "critique": critique_clean,
            "suggested_acceptance_criteria": criteria_clean,
            "improved_title": new_title,
            "improved_body": new_body,
        }

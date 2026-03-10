"""
Writer - generates issue and PR drafts.
"""
import json
from agent.llm import LLMClient
from agent.models import CodeReview, ActionPlan, DraftContent


class DraftWriter:
    """Generates drafts for issues and PRs."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def write_from_review(
        self, review: CodeReview, plan: ActionPlan
    ) -> DraftContent:
        """Write draft based on review and plan."""
        if plan.action == "Create Issue":
            return self._write_issue_from_review(review, plan)
        elif plan.action == "Create PR":
            return self._write_pr_from_review(review, plan)
        elif plan.action == "No action required":
            raise ValueError("Cannot write draft when no action is required")
        else:
            raise ValueError(f"Unknown action: {plan.action}")

    def write_issue_from_instruction(self, instruction: str) -> DraftContent:
        """Write issue draft from user instruction."""
        prompt = self._build_issue_instruction_prompt(instruction)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        return self._build_draft(parsed)

    def write_pr_from_instruction(self, instruction: str) -> DraftContent:
        """Write PR draft from user instruction."""
        prompt = self._build_pr_instruction_prompt(instruction)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        return self._build_draft(parsed)

    def _write_issue_from_review(
        self, review: CodeReview, plan: ActionPlan
    ) -> DraftContent:
        """Write issue draft from review."""
        context = self._format_context(review, plan)
        prompt = self._build_issue_review_prompt(context)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        return self._build_draft(parsed)

    def _write_pr_from_review(
        self, review: CodeReview, plan: ActionPlan
    ) -> DraftContent:
        """Write PR draft from review."""
        context = self._format_context(review, plan)
        prompt = self._build_pr_review_prompt(context)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        return self._build_draft(parsed)

    def _format_context(self, review: CodeReview, plan: ActionPlan) -> str:
        """Format review and plan into context string."""
        lines = [
            f"Type: {review.change_type}",
            f"Risk: {review.risk_level}",
            "",
            "Observations:",
        ]
        if review.observations:
            lines.extend(f"  • {o}" for o in review.observations)
        else:
            lines.append("  • None")
        
        lines.extend([
            "",
            "Facts:",
        ])
        if review.supporting_facts:
            lines.extend(f"  • {f}" for f in review.supporting_facts)
        else:
            lines.append("  • None")
        
        lines.extend([
            "",
            f"Decision: {plan.action}",
            f"Reasoning: {plan.reasoning}",
        ])
        
        return "\n".join(lines)

    def _build_issue_review_prompt(self, context: str) -> str:
        """Build prompt for issue from review."""
        return f"""
Create a GitHub Issue from this code review.

Context:
{context}

Requirements:
- Title: Short, specific, actionable
- Body sections:
  ## Problem Description
  (What's the problem?)

  ## Evidence
  (What supports this? Use only info from context.)

  ## Acceptance Criteria
  (Bullet list of testable conditions)

  ## Risk Level
  (low, medium, or high)

Rules:
- Be concrete, not vague
- Don't invent repo facts
- If info missing, say so
- Return JSON only

Format:
{{
  "title": "Brief title",
  "description": "## Problem Description\\n...\\n\\n## Evidence\\n...\\n\\n## Acceptance Criteria\\n- ...\\n\\n## Risk Level\\nlow|medium|high"
}}
""".strip()

    def _build_pr_review_prompt(self, context: str) -> str:
        """Build prompt for PR from review."""
        return f"""
Create a GitHub PR from this code review.

Context:
{context}

Requirements:
- Title: Short, specific, actionable
- Body sections:
  ## Summary
  (What does this PR do?)

  ## Files Affected
  (Which files changed? If unknown, say confirmation needed.)

  ## Behavior Change
  (How does behavior change?)

  ## Test Plan
  (How to test? If tests missing, say what should be tested.)

  ## Risk Level
  (low, medium, or high)

Rules:
- Be concrete, not vague
- Don't invent repo facts
- If info missing, say so
- Return JSON only

Format:
{{
  "title": "Brief title",
  "description": "## Summary\\n...\\n\\n## Files Affected\\n...\\n\\n## Behavior Change\\n...\\n\\n## Test Plan\\n...\\n\\n## Risk Level\\nlow|medium|high"
}}
""".strip()

    def _build_issue_instruction_prompt(self, instruction: str) -> str:
        """Build prompt for issue from instruction."""
        return f"""
Create a GitHub Issue from this instruction.

Instruction: {instruction}

Requirements:
- Title: Short, specific, actionable
- Body sections:
  ## Problem Description
  ## Evidence
  (Note if confirmation needed)
  ## Acceptance Criteria
  (Bullet list)
  ## Risk Level
  (low, medium, or high)

Rules:
- Don't invent repo facts
- If info missing, say so
- Return JSON only

Format:
{{
  "title": "Brief title",
  "description": "## Problem Description\\n...\\n\\n## Evidence\\n...\\n\\n## Acceptance Criteria\\n- ...\\n\\n## Risk Level\\nlow|medium|high"
}}
""".strip()

    def _build_pr_instruction_prompt(self, instruction: str) -> str:
        """Build prompt for PR from instruction."""
        return f"""
Create a GitHub PR from this instruction.

Instruction: {instruction}

Requirements:
- Title: Short, specific, actionable
- Body sections:
  ## Summary
  ## Files Affected
  (Say if confirmation needed)
  ## Behavior Change
  ## Test Plan
  (Say what should be tested if unknown)
  ## Risk Level
  (low, medium, or high)

Rules:
- Don't invent repo facts
- If info missing, say so
- Return JSON only

Format:
{{
  "title": "Brief title",
  "description": "## Summary\\n...\\n\\n## Files Affected\\n...\\n\\n## Behavior Change\\n...\\n\\n## Test Plan\\n...\\n\\n## Risk Level\\nlow|medium|high"
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
            raise ValueError("No JSON found in writer response")
        
        return json.loads(cleaned[start:end+1])

    def _build_draft(self, parsed: dict) -> DraftContent:
        """Build DraftContent from parsed data."""
        title = str(parsed.get("title", "")).strip()
        description = str(parsed.get("description", "")).strip()

        if not title:
            raise ValueError("Writer returned empty title")
        if not description:
            raise ValueError("Writer returned empty description")

        return DraftContent(title=title, description=description)

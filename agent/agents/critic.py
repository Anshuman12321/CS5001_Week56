"""
Critic - validates drafts before approval.
"""
import json
from agent.llm import LLMClient
from agent.models import DraftContent, CodeReview, ActionPlan, ValidationReport


class DraftCritic:
    """Validates drafts for quality and correctness."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def validate_from_review(
        self,
        draft: DraftContent,
        review: CodeReview,
        plan: ActionPlan,
    ) -> ValidationReport:
        """Validate draft created from review."""
        prompt = self._build_review_validation_prompt(draft, review, plan)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        return self._build_report(parsed)

    def validate_from_instruction(
        self,
        draft: DraftContent,
        instruction: str,
        target_type: str,
    ) -> ValidationReport:
        """Validate draft created from instruction."""
        prompt = self._build_instruction_validation_prompt(draft, instruction, target_type)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        return self._build_report(parsed)

    def _build_review_validation_prompt(
        self,
        draft: DraftContent,
        review: CodeReview,
        plan: ActionPlan,
    ) -> str:
        """Build validation prompt for review-based draft."""
        obs_text = "\n".join(f"  • {o}" for o in review.observations) if review.observations else "  • None"
        facts_text = "\n".join(f"  • {f}" for f in review.supporting_facts) if review.supporting_facts else "  • None"

        return f"""
Validate this draft. Check for:
1. Unsupported claims (not in review)
2. Missing required sections
3. Conflicts with plan decision
4. Missing test plans (for PRs)
5. Made-up repo details

Source Review:
- Type: {review.change_type}
- Risk: {review.risk_level}
- Observations:
{obs_text}
- Facts:
{facts_text}

Plan: {plan.action}
Reasoning: {plan.reasoning}

Draft:
Title: {draft.title}
Body:
{draft.description}

Rules:
- Unsupported claims → FAIL
- Missing sections → FAIL
- Conflicts with review/plan → FAIL
- Well-grounded → PASS
- Notes should be specific

Return JSON:
{{
  "passed": true or false,
  "feedback": ["specific note"]
}}
""".strip()

    def _build_instruction_validation_prompt(
        self,
        draft: DraftContent,
        instruction: str,
        target_type: str,
    ) -> str:
        """Build validation prompt for instruction-based draft."""
        target_lower = target_type.strip().lower()
        
        if target_lower == "issue":
            sections = "Problem Description, Evidence, Acceptance Criteria, Risk Level"
        elif target_lower == "pr":
            sections = "Summary, Files Affected, Behavior Change, Test Plan, Risk Level"
        else:
            raise ValueError(f"Invalid target type: {target_type}")

        return f"""
Validate this {target_type.upper()} draft.

Check:
1. Does it follow the instruction?
2. Are sections present? ({sections})
3. Any made-up repo facts?
4. Missing test plans (for PRs)?
5. Too vague?

Instruction: {instruction}

Draft:
Title: {draft.title}
Body:
{draft.description}

Rules:
- Invented facts → FAIL
- Missing sections → FAIL
- Doesn't follow instruction → FAIL
- Follows instruction, stays cautious → PASS
- Notes should be specific

Return JSON:
{{
  "passed": true or false,
  "feedback": ["specific note"]
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
            raise ValueError("No JSON found in critic response")
        
        return json.loads(cleaned[start:end+1])

    def _build_report(self, parsed: dict) -> ValidationReport:
        """Build ValidationReport from parsed data."""
        passed = bool(parsed.get("passed", False))
        feedback_raw = parsed.get("feedback", [])

        if not isinstance(feedback_raw, list):
            feedback_raw = [feedback_raw]

        feedback = [str(f).strip() for f in feedback_raw if str(f).strip()]

        return ValidationReport(passed=passed, feedback=feedback)

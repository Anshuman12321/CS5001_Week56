"""
Planner - decides what action to take based on review.
"""
import json
from agent.llm import LLMClient
from agent.models import CodeReview, ActionPlan


class ActionPlanner:
    """Decides what action to take after a review."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def decide(self, review: CodeReview) -> ActionPlan:
        """Decide on action and generate reasoning."""
        # Make decision using rules
        action = self._choose_action(review)
        
        # Get LLM to write reasoning
        prompt = self._build_reasoning_prompt(action, review)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        
        return self._build_plan(parsed, action)

    def _choose_action(self, review: CodeReview) -> str:
        """Choose action based on review using simple rules."""
        has_observations = bool(review.observations)
        risk = review.risk_level.lower()
        change_type = review.change_type.lower()

        # High risk → issue for tracking
        if risk == "high":
            return "Create Issue"

        # Features with observations → PR ready
        if change_type == "feature" and has_observations:
            return "Create PR"

        # Other changes with observations → issue for discussion
        if has_observations:
            return "Create Issue"

        # Nothing to do
        return "No action required"

    def _build_reasoning_prompt(self, action: str, review: CodeReview) -> str:
        """Build prompt for LLM to write reasoning."""
        obs_text = "\n".join(f"- {o}" for o in review.observations) if review.observations else "- (none)"
        facts_text = "\n".join(f"- {f}" for f in review.supporting_facts) if review.supporting_facts else "- (none)"

        return f"""
Write a brief justification for this decision.

Decision: {action}

Review:
- Type: {review.change_type}
- Risk: {review.risk_level}
- Observations:
{obs_text}
- Facts:
{facts_text}

Write 1-2 sentences explaining why this decision makes sense.
Reference specific observations or facts.

Return JSON:
{{
  "action": "{action}",
  "reasoning": "Brief explanation citing specific details"
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
            raise ValueError("No JSON found in planner response")
        
        return json.loads(cleaned[start:end+1])

    def _build_plan(self, parsed: dict, fallback_action: str) -> ActionPlan:
        """Build ActionPlan from parsed data."""
        valid_actions = {"Create Issue", "Create PR", "No action required"}
        
        action = parsed.get("action", fallback_action).strip()
        if action not in valid_actions:
            action = fallback_action

        reasoning = parsed.get("reasoning", "").strip()
        if not reasoning:
            reasoning = f"Rule-based decision: {fallback_action}"

        return ActionPlan(action=action, reasoning=reasoning)

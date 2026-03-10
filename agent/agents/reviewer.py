"""
Code reviewer - analyzes diffs and classifies changes.
"""
import json
from agent.llm import LLMClient
from agent.models import CodeReview


class CodeReviewer:
    """Analyzes code changes and produces structured reviews."""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def analyze(self, diff: str, files: list[str]) -> CodeReview:
        """Analyze a diff and return structured review."""
        # Gather basic facts first
        facts = self._extract_facts(diff, files)
        
        # Get LLM to classify and find patterns
        prompt = self._build_analysis_prompt(diff, files, facts)
        response = self.llm.call(prompt)
        parsed = self._parse_response(response)
        
        # Combine facts with LLM analysis
        return self._build_review(parsed, facts)

    def _extract_facts(self, diff: str, files: list[str]) -> list[str]:
        """Extract deterministic facts from diff and files."""
        facts = []
        
        if files:
            facts.append(f"Changed {len(files)} file(s)")
            for f in files:
                facts.append(f"File: {f}")
        else:
            facts.append("No files changed")

        diff_lower = (diff or "").lower()
        
        # Check for tests
        has_tests = any("test" in f.lower() for f in files) or "test" in diff_lower
        facts.append("Contains test changes" if has_tests else "No test changes")

        # Risk indicators
        risk_patterns = {
            "auth": "Authentication code modified",
            "login": "Login functionality changed",
            "payment": "Payment logic affected",
            "security": "Security-sensitive code changed",
            "schema": "Database schema modified",
            "migration": "Migration scripts changed",
            "config": "Configuration files modified",
            "api": "API endpoints modified",
        }

        for keyword, label in risk_patterns.items():
            if keyword in diff_lower or any(keyword in f.lower() for f in files):
                facts.append(label)

        return facts

    def _build_analysis_prompt(self, diff: str, files: list[str], facts: list[str]) -> str:
        """Build prompt for LLM analysis."""
        files_list = "\n".join(f"- {f}" for f in files) if files else "- (none)"
        facts_list = "\n".join(f"- {f}" for f in facts)
        diff_preview = (diff or "")[:6000] or "[empty]"

        return f"""
Analyze this code change and classify it.

Files changed:
{files_list}

Known facts:
{facts_list}

Diff:
{diff_preview}

Provide:
1. Category: feature, bugfix, refactor, docs, test, or chore
2. Risk: low, medium, or high
3. Observations: brief notes about what changed
4. Evidence: specific references to files or code

Rules:
- Only use info from the diff/files above
- Don't invent anything
- Small changes → usually refactor/chore
- Auth/security/payments → higher risk
- Be specific in observations

Return JSON only:
{{
  "change_type": "feature",
  "risk_level": "medium",
  "observations": ["brief note"],
  "evidence": ["specific reference"]
}}
""".strip()

    def _parse_response(self, text: str) -> dict:
        """Parse JSON from LLM response."""
        cleaned = text.strip()
        
        # Remove markdown fences
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
            raise ValueError("No JSON found in reviewer response")
        
        return json.loads(cleaned[start:end+1])

    def _build_review(self, parsed: dict, facts: list[str]) -> CodeReview:
        """Build CodeReview from parsed data and facts."""
        valid_types = {"feature", "bugfix", "refactor", "docs", "test", "chore"}
        valid_risks = {"low", "medium", "high"}

        change_type = parsed.get("change_type", "refactor").strip().lower()
        if change_type not in valid_types:
            change_type = "refactor"

        risk_level = parsed.get("risk_level", "medium").strip().lower()
        if risk_level not in valid_risks:
            risk_level = "medium"

        observations = parsed.get("observations", [])
        if not isinstance(observations, list):
            observations = [observations]
        observations = [str(o).strip() for o in observations if str(o).strip()]

        evidence = parsed.get("evidence", [])
        if not isinstance(evidence, list):
            evidence = [evidence]
        evidence = [str(e).strip() for e in evidence if str(e).strip()]

        # Merge facts with evidence
        all_evidence = list(facts)
        for item in evidence:
            if item not in all_evidence:
                all_evidence.append(item)

        return CodeReview(
            change_type=change_type,
            risk_level=risk_level,
            observations=observations,
            supporting_facts=all_evidence,
        )

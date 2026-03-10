"""
Data structures used throughout the agent system.
"""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class CodeReview:
    """Results from analyzing a code change."""
    change_type: str  # feature, bugfix, refactor, docs, test, chore
    risk_level: str  # low, medium, high
    observations: list[str] = field(default_factory=list)
    supporting_facts: list[str] = field(default_factory=list)


@dataclass
class ActionPlan:
    """Decision on what to do next."""
    action: str  # Create Issue, Create PR, No action required
    reasoning: str


@dataclass
class DraftContent:
    """Draft content for an issue or PR."""
    title: str
    description: str


@dataclass
class ValidationReport:
    """Results from validating a draft."""
    passed: bool
    feedback: list[str] = field(default_factory=list)


@dataclass
class DraftRecord:
    """Complete record of a draft with all metadata."""
    draft_id: str
    draft_type: str  # issue or pr
    origin: str  # review or instruction
    title: str
    description: str
    state: str  # drafted, approved, rejected, created

    review_data: Optional[CodeReview] = None
    plan_data: Optional[ActionPlan] = None
    validation_data: Optional[ValidationReport] = None

    gh_issue_num: Optional[int] = None
    gh_url: Optional[str] = None
    gh_error_msg: Optional[str] = None

    def serialize(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return asdict(self)

    @classmethod
    def deserialize(cls, data: dict) -> "DraftRecord":
        """Reconstruct from dictionary."""
        review = data.get("review_data")
        if review:
            review = CodeReview(**review)

        plan = data.get("plan_data")
        if plan:
            plan = ActionPlan(**plan)

        validation = data.get("validation_data")
        if validation:
            validation = ValidationReport(**validation)

        return cls(
            draft_id=data["draft_id"],
            draft_type=data["draft_type"],
            origin=data["origin"],
            title=data["title"],
            description=data["description"],
            state=data["state"],
            review_data=review,
            plan_data=plan,
            validation_data=validation,
            gh_issue_num=data.get("gh_issue_num"),
            gh_url=data.get("gh_url"),
            gh_error_msg=data.get("gh_error_msg"),
        )


@dataclass
class ReviewRecord:
    """Complete record of a review with planning decision."""
    review_id: str
    change_type: str
    risk_level: str
    observations: list[str] = field(default_factory=list)
    supporting_facts: list[str] = field(default_factory=list)
    plan_data: Optional[ActionPlan] = None

    def serialize(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return asdict(self)

    @classmethod
    def deserialize(cls, data: dict) -> "ReviewRecord":
        """Reconstruct from dictionary."""
        plan = data.get("plan_data")
        if plan:
            plan = ActionPlan(**plan)

        return cls(
            review_id=data["review_id"],
            change_type=data["change_type"],
            risk_level=data["risk_level"],
            observations=data.get("observations", []),
            supporting_facts=data.get("supporting_facts", []),
            plan_data=plan,
        )

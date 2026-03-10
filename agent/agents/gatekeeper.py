"""
Gatekeeper - handles approval and GitHub creation.
"""
from agent.models import DraftRecord
from agent.tools.draft_store import DraftStorage
from agent.tools.github_tools import GitHubAPI


class ApprovalGatekeeper:
    """Manages draft approval and GitHub creation."""

    def __init__(
        self,
        storage: DraftStorage | None = None,
        github: GitHubAPI | None = None,
    ):
        self.storage = storage or DraftStorage()
        self.github = github

    def process_approval(
        self,
        draft_id: str,
        approved: bool,
        pr_head: str | None = None,
        pr_base: str | None = None,
    ) -> DraftRecord:
        """Process approval or rejection of a draft."""
        draft = self.storage.load(draft_id)
        self._check_can_approve(draft)

        if not approved:
            draft.state = "rejected"
            self.storage.update(draft)
            return draft

        draft.state = "approved"
        self.storage.update(draft)

        if self.github is None:
            return draft

        created = self._create_on_github(draft, pr_head, pr_base)
        self.storage.update(created)
        return created

    def _check_can_approve(self, draft: DraftRecord) -> None:
        """Verify draft can be approved."""
        if draft.state not in {"drafted", "approved"}:
            raise ValueError(
                f"Draft {draft.draft_id} in state '{draft.state}' cannot be approved"
            )

        if draft.validation_data is None:
            raise ValueError(
                f"Draft {draft.draft_id} has no validation - cannot approve"
            )

        if not draft.validation_data.passed:
            raise ValueError(
                f"Draft {draft.draft_id} failed validation - cannot approve"
            )

    def _create_on_github(
        self,
        draft: DraftRecord,
        pr_head: str | None,
        pr_base: str | None,
    ) -> DraftRecord:
        """Create issue or PR on GitHub."""
        if draft.draft_type == "issue":
            result = self.github.create_issue(
                title=draft.title,
                body=draft.description,
            )
        elif draft.draft_type == "pr":
            if not pr_head or not pr_base:
                raise ValueError("PR requires both head and base branches")
            
            result = self.github.create_pull_request(
                title=draft.title,
                body=draft.description,
                head=pr_head,
                base=pr_base,
            )
        else:
            raise ValueError(f"Unknown draft type: {draft.draft_type}")

        draft.state = "created"
        draft.gh_issue_num = result["number"]
        draft.gh_url = result["url"]
        draft.gh_error_msg = None

        return draft

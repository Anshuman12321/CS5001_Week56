"""
CLI interface for the GitHub repository agent.
"""
import typer
from dotenv import load_dotenv

load_dotenv()

from agent.tools.git_tools import GitOperations
from agent.tools.github_tools import GitHubAPI
from agent.agents.reviewer import CodeReviewer
from agent.agents.planner import ActionPlanner
from agent.agents.writer import DraftWriter
from agent.agents.critic import DraftCritic
from agent.agents.gatekeeper import ApprovalGatekeeper
from agent.agents.improver import ContentImprover
from agent.tools.draft_store import DraftStorage
from agent.tools.review_store import ReviewStorage
from agent.models import ReviewRecord, DraftRecord


app = typer.Typer(help="GitHub Repository Agent - Review, draft, and improve Issues and PRs")


@app.command()
def review(
    base: str = typer.Option(None, "--base", help="Base branch to compare against"),
    range_: str = typer.Option(None, "--range", help="Commit range to review"),
):
    """Review code changes and decide on action."""
    if (not base and not range_) or (base and range_):
        typer.echo("Provide exactly one of --base or --range")
        raise typer.Exit(code=1)

    git = GitOperations()
    reviewer = CodeReviewer()
    planner = ActionPlanner()
    storage = ReviewStorage()

    diff = git.fetch_diff(base, range_)
    files = git.fetch_changed_files(base, range_)

    review_result = reviewer.analyze(diff, files)
    plan = planner.decide(review_result)

    record = ReviewRecord(
        review_id=storage.generate_id(),
        change_type=review_result.change_type,
        risk_level=review_result.risk_level,
        observations=review_result.observations,
        supporting_facts=review_result.supporting_facts,
        plan_data=plan,
    )

    storage.save(record)

    typer.echo("[Reviewer] Analysis Complete")
    typer.echo(f"Review ID: {record.review_id}")
    typer.echo(f"Category: {record.change_type}")
    typer.echo(f"Risk: {record.risk_level}")

    if record.observations:
        typer.echo("Observations:")
        for obs in record.observations:
            typer.echo(f"- {obs}")

    typer.echo("Evidence:")
    for fact in record.supporting_facts:
        typer.echo(f"- {fact}")

    typer.echo("\n[Planner] Plan Complete")
    typer.echo(f"Decision: {record.plan_data.action}")
    typer.echo(f"Reasoning: {record.plan_data.reasoning}")


@app.command()
def draft(
    target: str = typer.Argument(...),
    instruction: str = typer.Option(None, "--instruction"),
    base: str = typer.Option(None, "--base"),
    range_: str = typer.Option(None, "--range"),
):
    """Draft an issue or PR."""
    target = target.lower().strip()

    if target not in {"issue", "pr"}:
        typer.echo("Target must be 'issue' or 'pr'")
        raise typer.Exit(code=1)

    writer = DraftWriter()
    critic = DraftCritic()
    storage = DraftStorage()

    if instruction:
        # Draft from instruction
        if target == "issue":
            draft_content = writer.write_issue_from_instruction(instruction)
        else:
            draft_content = writer.write_pr_from_instruction(instruction)

        validation = critic.validate_from_instruction(
            draft=draft_content,
            instruction=instruction,
            target_type=target,
        )

        record = DraftRecord(
            draft_id=DraftStorage.generate_id(),
            draft_type=target,
            origin="instruction",
            title=draft_content.title,
            description=draft_content.description,
            state="drafted",
            review_data=None,
            plan_data=None,
            validation_data=validation,
        )

        storage.save(record)

        typer.echo(f"Draft ID: {record.draft_id}")
        typer.echo(record.title)
        typer.echo(record.description)

        typer.echo("\n[Critic] Reflection Complete")
        typer.echo(f"Verdict: {'PASS' if validation.passed else 'FAIL'}")
        if validation.feedback:
            typer.echo("Notes:")
            for note in validation.feedback:
                typer.echo(f"- {note}")
        return

    # Draft from review
    if (not base and not range_) or (base and range_):
        typer.echo("Provide one of --base or --range")
        raise typer.Exit(code=1)

    git = GitOperations()
    reviewer = CodeReviewer()
    planner = ActionPlanner()

    diff = git.fetch_diff(base, range_)
    files = git.fetch_changed_files(base, range_)

    review_result = reviewer.analyze(diff, files)
    plan = planner.decide(review_result)

    draft_content = writer.write_from_review(review_result, plan)

    validation = critic.validate_from_review(
        draft=draft_content,
        review=review_result,
        plan=plan,
    )

    record = DraftRecord(
        draft_id=DraftStorage.generate_id(),
        draft_type=target,
        origin="review",
        title=draft_content.title,
        description=draft_content.description,
        state="drafted",
        review_data=review_result,
        plan_data=plan,
        validation_data=validation,
    )

    storage.save(record)

    typer.echo(f"Draft ID: {record.draft_id}")
    typer.echo(record.title)
    typer.echo(record.description)

    typer.echo("\n[Critic] Reflection Complete")
    typer.echo(f"Verdict: {'PASS' if validation.passed else 'FAIL'}")
    if validation.feedback:
        typer.echo("Notes:")
        for note in validation.feedback:
            typer.echo(f"- {note}")


@app.command()
def improve(
    target: str = typer.Argument(...),
    number: int = typer.Option(..., "--number"),
    repo: str = typer.Option(None, "--repo"),
):
    """Improve an existing issue or PR."""
    target = target.lower().strip()

    if target not in {"issue", "pr"}:
        typer.echo("Target must be 'issue' or 'pr'")
        raise typer.Exit(code=1)

    github = GitHubAPI(repo=repo)
    improver = ContentImprover()

    if target == "issue":
        issue_data = github.fetch_issue(number)
        result = improver.improve_issue(
            title=issue_data.get("title", ""),
            body=issue_data.get("body", ""),
        )
    else:
        pr_data = github.fetch_pr(number)
        result = improver.improve_pr(
            title=pr_data.get("title", ""),
            body=pr_data.get("body", ""),
        )

    typer.echo("[Improver] Critique")
    for item in result["critique"]:
        typer.echo(f"- {item}")

    typer.echo("\n[Improver] Suggested Acceptance Criteria")
    if result["suggested_acceptance_criteria"]:
        for item in result["suggested_acceptance_criteria"]:
            typer.echo(f"- {item}")
    else:
        typer.echo("- None provided")

    typer.echo("\n[Writer] Proposed Improved Version")
    typer.echo(result["improved_title"])
    typer.echo(result["improved_body"])


@app.command()
def drafts():
    """List all stored drafts."""
    storage = DraftStorage()

    for record in storage.list_all():
        verdict = "N/A"
        if record.validation_data:
            verdict = "PASS" if record.validation_data.passed else "FAIL"

        typer.echo(
            f"{record.draft_id} | {record.draft_type} | {record.state} | {verdict} | {record.title}"
        )


@app.command()
def show_draft(draft_id: str):
    """Show details of a specific draft."""
    storage = DraftStorage()
    record = storage.load(draft_id)

    typer.echo(record.draft_id)
    typer.echo(record.title)
    typer.echo(record.description)

    if record.validation_data:
        typer.echo("\n[Critic] Reflection")
        typer.echo(f"Verdict: {'PASS' if record.validation_data.passed else 'FAIL'}")
        if record.validation_data.feedback:
            typer.echo("Notes:")
            for note in record.validation_data.feedback:
                typer.echo(f"- {note}")


@app.command()
def approve(
    draft_id: str = typer.Option(..., "--id"),
    yes: bool = typer.Option(False, "--yes"),
    no: bool = typer.Option(False, "--no"),
    repo: str = typer.Option(None, "--repo"),
    head: str = typer.Option(None, "--head"),
    base: str = typer.Option(None, "--base"),
):
    """Approve or reject a draft."""
    if yes == no:
        typer.echo("Provide exactly one of --yes or --no")
        raise typer.Exit(code=1)

    storage = DraftStorage()

    if no:
        gatekeeper = ApprovalGatekeeper(storage=storage)
        updated = gatekeeper.process_approval(draft_id=draft_id, approved=False)
        typer.echo(f"Status: {updated.state}")
        return

    github = GitHubAPI(repo=repo)
    gatekeeper = ApprovalGatekeeper(storage=storage, github=github)

    updated = gatekeeper.process_approval(
        draft_id=draft_id,
        approved=True,
        pr_head=head,
        pr_base=base,
    )

    typer.echo(f"Status: {updated.state}")

    if updated.gh_url:
        typer.echo(updated.gh_url)


if __name__ == "__main__":
    app()

# GitHub Repository Agent

CLI tool for reviewing code changes, drafting GitHub Issues/PRs, and improving existing content.

## Installation

1. Install Python 3.8 or higher

2. Install dependencies:
   ```powershell
   pip install -e .
   ```

3. Set up Ollama (for code analysis):
   - Download from https://ollama.ai
   - Run: `ollama pull devstral-small-2:24b-cloud`
   - Start server: `ollama serve`


## Usage

Run commands using:
```powershell
python -m agent.cli [COMMAND]
```

### Commands

**Review code changes:**
```powershell
python -m agent.cli review --base main
python -m agent.cli review --range HEAD~3..HEAD
```

**Draft an issue or PR:**
```powershell
# From code review
python -m agent.cli draft issue --base main
python -m agent.cli draft pr --base main

# From instruction
python -m agent.cli draft issue --instruction "Add input validation"
python -m agent.cli draft pr --instruction "Refactor pricing logic"
```

**List and view drafts:**
```powershell
python -m agent.cli drafts
python -m agent.cli show-draft draft-abc12345
```

**Approve or reject drafts:**
```powershell
python -m agent.cli approve --id draft-abc12345 --yes --repo owner/repo
python -m agent.cli approve --id draft-abc12345 --no
```

**Improve existing issues/PRs:**
```powershell
python -m agent.cli improve issue --number 42 --repo owner/repo
python -m agent.cli improve pr --number 17 --repo owner/repo
```

## Project Structure

```
agent/
├── agents/          # Core agent classes
├── tools/           # Git, GitHub, storage utilities
├── cli.py          # Command-line interface
├── llm.py          # LLM client
└── models.py       # Data models

data/               # Local storage (auto-created)
├── drafts/         # Draft records
└── reviews/        # Review records
```

## Requirements

- Python 3.8+
- Ollama (for code analysis)
- Git (for review commands)
- GitHub token (optional, for creating issues/PRs)

## Troubleshooting

**Command not found:**
- Use `python -m agent.cli` instead of `agent`

**LLM errors:**
- Ensure Ollama is running: `ollama serve`
- Check model is installed: `ollama list`

**GitHub errors:**
- Verify `.env` file has correct `GITHUB_REPOSITORY` and `GITHUB_TOKEN`
- Or use `--repo` flag: `--repo owner/repo`

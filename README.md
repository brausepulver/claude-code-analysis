# claude-code-analysis

This repository collects and visualizes GitHub activity for various AI assistants (Claude, Cursor, Copilot, Jules, Codex) by analyzing commits, co-authored commits, and repository mentions.

## Installation
```bash
uv sync
```

## Setup
Create a `.env` file in the root directory with your GitHub token for access to the GH API:
   ```
   GITHUB_TOKEN=your_github_token_here
   ```

## Data Collection

```bash
python main.py
```

This will:
- Search GitHub for commits, co-authored commits, and repository mentions
- Collect weekly growth data starting from Feb 24, 2025
- Save results to `data/ai_assistant_github_analysis.json`

## Plotting

```bash
python plot.py
```

This will create the plots in the `plots/` directory.

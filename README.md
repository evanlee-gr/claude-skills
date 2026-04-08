# claude-skills

Personal Claude Code skills synced across all machines.

## Skills

| Skill | Description |
|-------|-------------|
| `design-taste-frontend` | Senior UI/UX engineer - overrides generic AI aesthetics |
| `web-design-guidelines` | Audits UI code against 100+ Vercel web interface guidelines |
| `ad-creative` | Generates ad copy at scale across Google, Meta, LinkedIn, TikTok |
| `copywriting` | Conversion copywriting for landing pages, homepages, pricing |
| `email-sequence` | Designs welcome, nurture, and re-engagement email sequences |
| `cold-email` | Writes B2B cold outreach emails and follow-up sequences |
| `remotion-best-practices` | Remotion (React video) domain knowledge and best practices |

## Setup on a new machine

### Windows (PowerShell)
```powershell
git clone https://github.com/evanlee-gr/claude-skills.git
cd claude-skills
./setup.ps1
```

### macOS / Linux
```bash
git clone https://github.com/evanlee-gr/claude-skills.git
cd claude-skills
bash setup.sh
```

## Adding new skills

1. Create `.claude/skills/your-skill-name/SKILL.md`
2. Add YAML frontmatter with `name:` and `description:`
3. Commit and push
4. Re-run setup script on other machines
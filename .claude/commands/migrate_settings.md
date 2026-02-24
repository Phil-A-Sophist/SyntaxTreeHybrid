# Migrate Settings

Run the settings migration script to sync all Claude Code configuration from master files.

Use this when:
- You've updated a master settings file and want to apply it immediately
- Something seems wrong with `.claude/settings.json`
- You want to verify settings are correct after changing machines

```bash
python claude_docs/bootstrap/migrate_settings.py
```

After running, report:
1. What files were written
2. The settings audit summary
3. Any errors encountered

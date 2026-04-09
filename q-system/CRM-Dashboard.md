# CRM Dashboard

> Obsidian Dataview-powered views of your contacts, pipeline, and actions. Install the Dataview plugin to see live tables.

## All Contacts

```dataview
TABLE WITHOUT ID
  file.name AS "Source",
  regexreplace(L.text, ".*\*\*Type:\*\*\s*", "") AS "Type",
  regexreplace(S.text, ".*\*\*Status:\*\*\s*", "") AS "Status",
  regexreplace(X.text, ".*\*\*Last interaction:\*\*\s*", "") AS "Last Interaction",
  regexreplace(N.text, ".*\*\*Next step:\*\*\s*", "") AS "Next Step"
FROM "my-project/relationships"
FLATTEN file.lists AS L
WHERE L.text AND contains(L.text, "**Type:**")
FLATTEN file.lists AS S
WHERE S.text AND contains(S.text, "**Status:**")
FLATTEN file.lists AS X
WHERE X.text AND contains(X.text, "**Last interaction:**")
FLATTEN file.lists AS N
WHERE N.text AND contains(N.text, "**Next step:**")
```

> **Note:** Dataview works best with YAML frontmatter. The queries above parse the bullet-point format in relationships.md. For richer queries, consider adding frontmatter to individual contact files in the future.

## Simple Contact List

If the table above doesn't render cleanly, use this simpler view:

```dataview
LIST
FROM "my-project"
WHERE contains(file.name, "relationships")
```

## Open Actions

Tasks marked with `- [ ]` across all files:

```dataview
TASK
FROM "my-project" OR "canonical"
WHERE !completed
SORT file.mtime DESC
```

## Recent Changes

Files modified in the last 7 days:

```dataview
TABLE file.mtime AS "Modified"
FROM "my-project" OR "canonical" OR "marketing"
WHERE date(now) - file.mtime <= dur(7 days)
SORT file.mtime DESC
```

## How This Works

- Claude Code writes your contacts, actions, and pipeline to markdown files
- Obsidian's Dataview plugin reads those files and renders them as tables
- No sync, no API, no database. Same files, visual view.
- To update a contact, run `/q-debrief` after a conversation. The dashboard updates automatically.

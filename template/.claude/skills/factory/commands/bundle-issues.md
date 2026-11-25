Part of the factory skill: SKILL.md's rules apply here too. Moved out of SKILL.md unchanged, so it is read only when needed; a **Section** is one of SKILL.md.

### Bundle issues
The owner can group small modular issues under a **bundle issue**: an issue with the label
`factory:bundle` whose description lists its members as a checklist, one per line, same
project: `- [ ] #123` (or `- [x] #123`; `*`/`+` bullets and text after the number are fine).
Members are also taken from the forge when it ties issues to the bundle: GitHub sub-issues
(`gh api repos/{owner}/{repo}/issues/<nr>/sub_issues`) and GitLab issue links
(`glab api projects/:id/issues/<iid>/links`, any link type such as `relates_to`). `triage prepare`
reads those itself (forge CLI logged in; otherwise a NOTE says only the checklist counts). Only a
bundle issue by an allowed author counts. Each member passes the same filter as any issue (open,
allowed author, skip labels, no job/PR/commit); left out with a `NOTE: bundle #N: #M left out: …`
line: closed or unknown members, untrusted authors, other projects, nested bundles and
`factory:solo` members (those stay their own candidates). Members are `SKIPPED: … in bundle #N`
as single issues. A bundle is always **one job** with `"issues": [bundle, members…]`: never split
or mixed with other issues, effort = the highest of the triage and the labels of the bundle and its
members (the floor rules still apply), not capped by `bundle_max` (a NOTE warns above it), and
started even when the triage agent would skip it. Delivery and closing treat it like any bundle: the
PR/MR body gets `<issues.link> #<nr>` for the bundle issue and every member, and `close_on_merge`
closes them all. A bundle without open members is skipped (close it).

# QA Intelligence Hub — Documentation Governance

This document governs how reusable project knowledge is classified, verified, and recorded in the correct existing document. Its purpose is to prevent stale guidance and competing sources of truth—not to duplicate the detailed rules owned by other documents.

## 1. Governing principles

1. **Inspect before writing.** Search the existing Markdown and relevant implementation/configuration before adding information. Determine whether it is already documented, whether it has changed, and which document owns it.
2. **One logical owner per reusable fact, rule, procedure, or decision.** Put the authoritative detail in that owner's document. Other documents may include a short summary or cross-reference when useful, but should not reproduce the full rule.
3. **Evidence before assertion.** Documentation describes verified repository behavior, not aspirations. Confirm implementation, configuration, tests, deployment evidence, or an approved decision as appropriate. Label plans and unresolved findings as such; never present them as current behavior.
4. **Owner first, references second.** For a cross-cutting discovery, update the authoritative owner first, then update concise references that would otherwise mislead readers. Search for stale or contradictory copies and resolve them within the authorized scope.
5. **Keep ownership stable.** Do not move a document's responsibility or create another authoritative document without a clear, reviewed reason. Do not create a new Markdown file when an existing owner is appropriate.
6. **Respect higher-level contracts.** Agent behavior and engineering constraints must remain consistent with [`AGENTS.md`](AGENTS.md); quality and validation requirements must remain consistent with [`QUALITY_GATE.md`](QUALITY_GATE.md). When sources conflict, do not silently choose or propagate one: identify the conflict and follow applicable higher-level instructions while obtaining a decision if necessary.
7. **Small, reviewable edits.** Preserve unrelated content and user changes. Do not silently delete or rewrite existing guidance. Record why a material change was made and what evidence supports it.

## 2. Document ownership map

Use this map to route new knowledge. The named owner contains the authoritative detail; any secondary reference should link to it rather than become another full copy.

| Knowledge type | Authoritative owner | Other documents' role |
|---|---|---|
| Agent behavior, repository-wide engineering instructions, coding constraints, tool/context rules | [`AGENTS.md`](AGENTS.md) | Link to it; do not redefine agent obligations elsewhere. |
| Quality gates, validation, failure/root-cause handling, security gates, deployment gates, completion criteria, evidence requirements | [`QUALITY_GATE.md`](QUALITY_GATE.md) | Task checklists and workflows may point to the gate and state their local application; they must not establish conflicting thresholds or exceptions. |
| Project overview, capabilities, user-facing setup, high-level current status, portfolio presentation | [`README.md`](README.md) | Keep summaries audience-appropriate and link to detailed owner documents. |
| Architecture, components, boundaries, data flow, integration design, architectural decisions | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | A high-level README diagram or summary may link here; do not create a second architecture authority. |
| Environments, deployment configuration, hosting, migrations, operational procedures, production configuration | [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | README may provide a current high-level deployment summary and link to the runbook. |
| Domain-pack architecture, adding domains, domain-specific factories/capabilities, extension contracts | [`docs/domain-extension-guide.md`](docs/domain-extension-guide.md) | Architecture documentation may describe the platform boundary and link to extension instructions. |
| Milestones, planned capabilities, progression, future work | [`docs/ROADMAP.md`](docs/ROADMAP.md) | README may summarize verified current status; do not maintain a second milestone checklist. |
| AI-assisted development, model/agent usage, AI development practices and validation workflow | [`docs/AI_WORKFLOW.md`](docs/AI_WORKFLOW.md) | Agent-wide mandatory behavior still belongs in `AGENTS.md`; quality thresholds and gates belong in `QUALITY_GATE.md`. Link rather than duplicate. |
| Task-level completion checklist, handoff, task completion evidence | [`docs/TASK_COMPLETION_CHECKLIST.md`](docs/TASK_COMPLETION_CHECKLIST.md) | It applies the gate to an individual task; it does not replace the quality gate or machine policy. |
| Machine-readable execution/checkpoint policy and current checkpoint state | [`.qa/task-checkpoint.json`](.qa/task-checkpoint.json) | Human-readable documents explain the process and link here; they must not claim state that disagrees with the file/evaluator. |
| Checkpoint implementation and validation behavior | [`qa-engine/task_checkpoint.py`](qa-engine/task_checkpoint.py) | Document behavior through the checklist/policy; code is authoritative for executable behavior. |
| Specialized reusable skill procedures | The corresponding skill file under [`.agents/skills/`](.agents/skills/) | Promote generally applicable repository rules to the appropriate owner above; skills may reference those rules, not redefine them. |
| Component-local usage or contributor notes not covered above | The existing component README or nearest appropriate owner | Keep narrowly scoped; link to the project-level owner for cross-cutting policy. |

If a discovery appears to fit multiple categories, separate its distinct parts and assign each one owner (for example, an architecture decision to `docs/ARCHITECTURE.md` and its required validation gate to `QUALITY_GATE.md`). Do not force one document to own unrelated details merely because they were discovered together.

## 3. Classification and propagation workflow

After a meaningful implementation, investigation, release, or other discovery, decide whether it created reusable knowledge. If so:

1. **Classify it** as one or more of: `agent_rule`, `quality_rule`, `architecture`, `deployment`, `domain_extension`, `roadmap`, `AI_workflow`, `task_process`, `project_overview`, or `checkpoint_state`. A material finding may have separate classifications for separate statements.
2. **Establish evidence and status.** Identify the source (implementation, tests, configuration, verified deployment, or approved decision) and distinguish confirmed fact, decision, proposal, historical result, and unresolved issue. Include dates/revisions when needed to keep time-sensitive evidence clear.
3. **Inspect the owner.** Read the relevant section and nearby links. Search Markdown for the key rule/term and inspect affected code/configuration so the change does not create a duplicate or describe behavior that is not implemented.
4. **Update the authoritative owner first** if the discovery changes, corrects, or adds information that belongs there. Keep the edit limited to supported facts and preserve the owner's intended audience and scope.
5. **Update references only where needed.** Add a concise cross-link or correct an affected summary, command, status, or navigation entry. Do not replicate the full policy or procedure.
6. **Search for contradictions and stale copies.** Check the owner and likely references for conflicting wording, old commands, environment variable names, URLs, topology, test counts, deployment behavior, and security behavior. Correct only within scope and authorization; otherwise record the conflict and report it for resolution.
7. **Validate and record.** Apply Section 5. For a material change, leave a concise evidence note in the task's appropriate record/report or change description: what changed, owner updated, evidence checked, references corrected, and validation performed. Do not mutate machine checkpoint state merely to record prose.

Agents should apply this workflow automatically when evidence is clear and the change is authorized. Do not wait for the user to name the right file. A change is not permission to modify unrelated owner documents; if scope forbids such edits, report the required follow-up rather than violating scope.

## 4. Routing examples

- A **new security invariant** is owned by `QUALITY_GATE.md`; update `AGENTS.md` only if it also establishes repository-wide agent behavior or a coding constraint. Link between them where useful; do not reproduce the gate.
- An **architecture change** is recorded in `docs/ARCHITECTURE.md`; update the README's high-level description only if it is now inaccurate, and link to the architecture owner.
- A **deployment configuration or production finding** is recorded in `docs/DEPLOYMENT.md` after verification. Update the README's deployment summary only when affected. Record an unresolved live finding as a dated, clearly labeled finding—not as an implemented safeguard.
- A **new domain-extension pattern** is recorded in `docs/domain-extension-guide.md`; change architecture documentation only if the platform boundary/design itself changed.
- A **new milestone or future capability** belongs in `docs/ROADMAP.md`; update high-level README status only when supported by completed work.
- A **new AI-agent development practice** belongs in `docs/AI_WORKFLOW.md`; a universally mandatory agent behavior belongs in `AGENTS.md`, while required quality evaluation belongs in `QUALITY_GATE.md`.
- A **task handoff/completion checklist change** belongs in `docs/TASK_COMPLETION_CHECKLIST.md`; executable policy/state changes belong in `.qa/task-checkpoint.json` or `qa-engine/task_checkpoint.py` according to which actually changed.
- A **specialized skill technique** stays in the relevant `.agents/skills/<skill>/SKILL.md`. Promote only its reusable project-wide rule to the appropriate owner and link back when helpful.

These examples route knowledge; they do not assert that a proposed behavior is already implemented.

## 5. Documentation validation

After a documentation update:

1. **Owner check:** Confirm each new or changed reusable claim is in its designated owner; secondary copies are only concise summaries or links.
2. **Implementation alignment:** Verify behavior against source, tests, configuration, or reliable operational evidence. Label unverified findings, proposals, and planned work accurately.
3. **Consistency check:** Search for contradictory or stale versions, including old commands, environment names, URLs, architecture descriptions, material test counts, deployment details, and security behavior. Resolve or explicitly report conflicts.
4. **Reference check:** Verify relative Markdown links and anchors point to existing, intended files/sections. Confirm any changed navigation remains useful.
5. **Structure and clarity:** Check headings, lists, tables, code fences, spelling, terminology, and audience. Keep content specific and avoid redundant prose.
6. **Diff and scope:** Review the complete diff for unintended edits, deletions, generated files, secrets, and unrelated changes. Run `git diff --check` and report its actual result.
7. **Final state:** Inspect `git status` and distinguish task changes from pre-existing user changes. Do not discard or stage unrelated files as part of validation.

For documentation-only work, run documentation checks rather than unrelated application suites. Run applicable tests and the required quality checks when documentation changes executable examples, policies, commands, acceptance criteria, or when the governing quality gate otherwise requires them. A validation command is not verified merely because it appears in another document: inspect current configuration and actual behavior when accuracy matters.

## 6. Human decision and prohibited actions

Ask for a human decision when:

- Two documents plausibly claim ownership and repository evidence does not resolve it.
- The discovery implies materially different architecture choices or conflicts with an authoritative rule.
- A required behavior or requirement is undefined and cannot safely be inferred.
- A proposed documentation statement has material product or security implications that are not supported by evidence or authorization.
- Correct propagation requires edits outside the task's permitted scope.

Do not:

- Blindly duplicate information or create competing authoritative sources.
- Invent project facts, mark unverified behavior as implemented, or turn a proposal into current-state documentation.
- Silently delete existing documentation, overwrite authoritative rules without review, or change document ownership without a clear reason.
- Change application code to make documentation appear true; report the mismatch and route code work separately.
- Commit, push, deploy, or alter checkpoint state as part of documentation governance unless the task explicitly authorizes that action and all applicable project gates allow it.

When work is blocked, preserve the existing owner, state the evidence and unresolved conflict, and identify the decision or verification needed. Do not propagate uncertain claims across documents.
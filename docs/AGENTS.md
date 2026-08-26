# The agent team

Six agents, each with one job and a narrow remit. The `interior-design` skill orchestrates them.
Splitting the work this way is deliberate: a single agent doing everything tends to design before
it has surveyed, and to justify a decision it has already made.

| Agent | Runs | Produces | Tools |
|---|---|---|---|
| `design-intake` | first, and whenever the brief changes | `project.yml` | Read, Write, Edit, Bash, Glob, AskUserQuestion |
| `design-surveyor` | after intake | `room:` block, `brief/site-survey.md`, shell drawings | Read, Write, Edit, Bash, Glob, Grep |
| `design-strategist` | after `room-model` | `brief/direction-set.md` | Read, Write, Bash, Glob, Grep |
| `design-author` | once per direction | `directions/NN-slug.json` | Read, Write, Edit, Bash, Glob, Grep |
| `design-critic` | after every pack | a defect report with root causes | Read, Bash, Glob, Grep (read-only by design) |
| `design-reporter` | at the end | `report/report.pdf` | Read, Write, Edit, Bash, Glob |

## Why each exists

**Intake** exists because clients cannot answer "what style do you want?" but can choose between
two described rooms. It asks in small batches with concrete options. Its most important question is
*is there anything in this room that cannot leave it?* — the most under-asked question in interior
design, and the one that most often invalidates finished work.

**Surveyor** exists because geometry errors are catastrophic and cheap to prevent. It reads every
photograph properly and **states the opening count out loud** before writing anything, because an
opening you never modelled is invisible to every downstream check until a render looks wrong.

**Strategist** exists because the natural failure of a design set is five variations of one idea.
It enforces the four-of-seven-axes rule and spreads the set across budget tiers, so a client with a
small budget has real options.

**Author** exists to write one direction at a time, with every change carrying a specification, a
reason and a validation against the room's actual constraints.

**Critic** is deliberately **read-only**. It cannot fix anything, which forces it to report the
*root cause* — the room model, the prompt builder, the camera config — rather than patching one
image. A fix that does not carry forward recurs in every remaining direction.

**Reporter** exists because a report is not done when it is generated. It rasterises pages and
reads them back, since layout errors are invisible in source and obvious on the page.

## Handoffs

```
intake ──project.yml──> surveyor ──room model──> strategist ──direction set──> author
                                                                                 │
                                        report <── reporter <── critic <── pack ──┘
```

Each arrow crosses an approval gate except author→pack. Nobody proceeds on an assumption; the tool
refuses rather than asking twice.

## Customising

Agents are plain markdown in `.claude/agents/`. Edit the body to change how one behaves.

- Change the **standards** — edit the rules in that agent's file.
- Add a **stage** — write a new `.claude/agents/design-<x>.md` and add it to the skill's pipeline.
- Change the **register or house style** — that belongs in `project.yml` (`brief.register`,
  `style.richness`), not in an agent. Agents are generic; projects are specific.

Keep the critic read-only. The moment it can edit, it starts fixing symptoms.

"""
Retrieval-grounded AI suggestions, per the Phase 0 roadmap's "grounded in
everything documented here via retrieval rather than free generation."

No vector DB: the seeded dataset (resources, grading levers, sub-skills,
proformas, worked-example activity blocks) is small enough that plain
DB-filtered queries are sufficient, and — importantly — they structurally
prevent the model from inventing resources that don't exist in the
library (the "resource specificity" rule baked into this whole project).

Both entry points return plain Python data; they never write to the
database themselves. The views decide what to do with the suggestion,
and nothing is saved until the therapist reviews and explicitly saves it.
"""

import anthropic
from django.conf import settings

from .models import ActivityBlock, ProformaDomainImplication

MODEL = "claude-sonnet-5"


class AIGenerationError(Exception):
    """Raised when a suggestion can't be produced (missing key, API error, bad response)."""


def _client():
    if not settings.ANTHROPIC_API_KEY:
        raise AIGenerationError(
            "No ANTHROPIC_API_KEY configured. Add one to your .env file to enable AI suggestions."
        )
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _call_tool(client, system, user_content, tool):
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user_content}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
        )
    except anthropic.APIError as exc:
        raise AIGenerationError(f"Anthropic API error: {exc}") from exc

    for block in response.content:
        if block.type == "tool_use" and block.name == tool["name"]:
            return block.input

    raise AIGenerationError("Model did not return the expected structured output.")


def _child_context_lines(child):
    lines = [
        f"Age: {child.age_years};{child.age_months}",
        f"Default environment: {child.get_default_environment_display()}",
        f"Current presentation: {child.current_presentation}",
    ]
    if child.masking_note:
        lines.append(f"Masking note: {child.masking_note}")
    if child.family_cultural_context:
        lines.append(f"Family/cultural context: {child.family_cultural_context}")
    interests = ", ".join(i.name for i in child.interests.all())
    if interests:
        lines.append(f"Interests: {interests}")
    return lines


# ---------------------------------------------------------------------------
# Goal refinement (Screen 2)
# ---------------------------------------------------------------------------

GOAL_REFINEMENT_TOOL = {
    "name": "suggest_goal_refinement",
    "description": "Suggest an interim (process) SMART goal and an outcome SMART goal.",
    "input_schema": {
        "type": "object",
        "properties": {
            "interim_goal_text": {
                "type": "string",
                "description": "A nearer-term, measurable process/interim SMART goal. Empty string if the goal doesn't need one.",
            },
            "outcome_goal_text": {
                "type": "string",
                "description": "The longer-term, measurable outcome SMART goal.",
            },
        },
        "required": ["interim_goal_text", "outcome_goal_text"],
    },
}


def suggest_goal_refinement(goal):
    """Return {"interim_goal_text": ..., "outcome_goal_text": ...} for a Goal."""
    child = goal.child
    lines = [
        f"Domain: {goal.domain.name}",
        f"Goal as given by the therapist: {goal.raw_goal_text}",
        *_child_context_lines(child),
    ]
    system = (
        "You are assisting a paediatric occupational therapist. Refine a "
        "general goal into SMART goals (Specific, Measurable, Achievable, "
        "Relevant, Time-bound), using [date] as a placeholder for any date. "
        "Where the goal involves avoidance, fear, or a multi-step skill "
        "needing graded progression, split it into a nearer-term interim/"
        "process goal plus a longer-term outcome goal. If no interim goal "
        "is genuinely needed, return an empty string for it rather than "
        "inventing one. Ground every claim in the child's presentation "
        "given below — do not assume anything not stated."
    )
    result = _call_tool(_client(), system, "\n".join(lines), GOAL_REFINEMENT_TOOL)
    return {
        "interim_goal_text": result.get("interim_goal_text", ""),
        "outcome_goal_text": result.get("outcome_goal_text", ""),
    }


# ---------------------------------------------------------------------------
# Activity block generation (Screen 4)
# ---------------------------------------------------------------------------

def _activity_blocks_tool(resource_names):
    return {
        "name": "suggest_activity_blocks",
        "description": "Suggest a sequence of activity blocks for a therapy session plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "blocks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "block_type": {
                                "type": "string",
                                "enum": [c[0] for c in ActivityBlock.BlockType.choices],
                            },
                            "duration_minutes": {"type": "integer"},
                            "title": {"type": "string"},
                            "activity_description": {
                                "type": "string",
                                "description": (
                                    "Complete enough to run as written: setup, "
                                    "step-by-step sequence, and a genuine payoff/"
                                    "goal-state, per the functional-play-narrative rule."
                                ),
                            },
                            "clinical_reasoning": {"type": "string"},
                            "resource_names": {
                                "type": "array",
                                "items": {"type": "string", "enum": resource_names} if resource_names else {"type": "string"},
                                "description": "Only names from the provided resource list — never invent a resource.",
                            },
                            "grade_up_note": {"type": "string"},
                            "grade_down_note": {"type": "string"},
                        },
                        "required": [
                            "block_type", "duration_minutes", "title",
                            "activity_description", "clinical_reasoning",
                            "resource_names", "grade_up_note", "grade_down_note",
                        ],
                    },
                },
            },
            "required": ["blocks"],
        },
    }


def _domain_context_lines(domain):
    lines = [f"Domain: {domain.name}"]

    sub_skills = list(domain.sub_skills.all())
    if sub_skills:
        lines.append("Foundational sub-skills: " + "; ".join(s.name for s in sub_skills))

    levers = list(domain.grading_levers.all())
    if levers:
        lines.append("Established grading levers for this domain:")
        for lever in levers:
            lines.append(
                f"  - {lever.name}: easier = {lever.grade_down_description}; "
                f"harder = {lever.grade_up_description}"
            )

    return lines


def _resource_context_lines(domain):
    resources = list(domain.resources.order_by("name"))
    names = [r.name for r in resources]
    lines = ["Available resources in this domain (use ONLY these by exact name):"]
    for r in resources:
        age = ""
        if r.age_min_months or r.age_max_months:
            age = f", age {r.age_min_months or '?'}-{r.age_max_months or '?'} months"
        lines.append(f"  - {r.name} ({r.get_resource_type_display()}{age})")
    return names, lines


def _proforma_context_lines(child, domain):
    implications = ProformaDomainImplication.objects.filter(
        proforma__in=child.proformas.all(), domain=domain,
    ).select_related("proforma")
    if not implications:
        return []
    lines = ["Diagnosis-specific guidance for this domain (apply alongside, never override, the child's actual documented presentation):"]
    for imp in implications:
        lines.append(
            f"  - {imp.proforma.name}: {imp.how_it_shows_up} -> {imp.design_implication}"
        )
        lines.append(f"    Individual variability caution: {imp.proforma.individual_variability_caution}")
    return lines


def _few_shot_examples(domain, exclude_plan):
    examples = (
        ActivityBlock.objects
        .filter(session_plan__goal__domain=domain)
        .exclude(session_plan=exclude_plan)
        .select_related("session_plan")
        .order_by("?")[:2]
    )
    if not examples:
        return []
    lines = ["Example activity blocks from other cases in this domain, for tone/format reference only (do not copy content):"]
    for block in examples:
        lines.append(
            f"  - [{block.get_block_type_display()}] {block.title}: {block.activity_description[:300]}"
        )
    return lines


def suggest_activity_blocks(plan):
    """Return a list of block dicts (with resolved `resources` Resource queryset) for a SessionPlan."""
    goal = plan.goal
    child = goal.child
    domain = goal.domain

    resource_names, resource_lines = _resource_context_lines(domain)

    lines = [
        f"Session length: {plan.session_length_minutes} minutes",
        f"Environment: {plan.get_environment_display()}",
        f"Domain: {domain.name}",
        f"Goal as given: {goal.raw_goal_text}",
    ]
    if goal.interim_goal_text:
        lines.append(f"Interim goal: {goal.interim_goal_text}")
    if goal.outcome_goal_text:
        lines.append(f"Outcome goal: {goal.outcome_goal_text}")
    for op in goal.option_points.all():
        if op.selected_option:
            lines.append(f"Already decided: {op.question_text} -> {op.selected_option}")
    lines += _child_context_lines(child)
    lines += _domain_context_lines(domain)
    lines += resource_lines
    lines += _proforma_context_lines(child, domain)
    lines += _few_shot_examples(domain, exclude_plan=plan)

    existing_blocks = list(plan.blocks.all())
    if existing_blocks:
        lines.append(
            f"This plan already has {len(existing_blocks)} block(s); suggest ones "
            "to fill out the rest of the session length, not a full duplicate plan."
        )

    system = (
        "You are assisting a paediatric occupational therapist in building a "
        "session plan. Suggest a sequence of activity blocks (warm-up, main, "
        "movement resets as needed, warm-down) that together roughly fill the "
        "stated session length. Every activity must be complete enough to run "
        "as written (setup, steps, and a genuine payoff/goal-state) and every "
        "clinical_reasoning must explain which component skill gap the "
        "activity targets, per the child's actual documented presentation. "
        "Use only resources from the provided list, by exact name. Ground "
        "grade-up/grade-down notes in the domain's established grading "
        "levers where relevant."
    )

    result = _call_tool(_client(), system, "\n".join(lines), _activity_blocks_tool(resource_names))

    from .models import Resource

    blocks = []
    for i, block in enumerate(result.get("blocks", [])):
        resources = Resource.objects.filter(name__in=block.get("resource_names", []))
        blocks.append({
            "block_type": block["block_type"],
            "duration_minutes": block["duration_minutes"],
            "title": block["title"],
            "activity_description": block["activity_description"],
            "clinical_reasoning": block["clinical_reasoning"],
            "resources": resources,
            "grade_up_note": block.get("grade_up_note", ""),
            "grade_down_note": block.get("grade_down_note", ""),
        })
    return blocks

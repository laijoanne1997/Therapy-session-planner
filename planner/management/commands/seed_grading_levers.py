"""
Seeds the CANONICAL per-domain GradingLever rows -- the actual grade
up/grade down tables from each Phase 0 domain reference doc (e.g.
fine-motor-handwriting-developmental-sequence-v1.md, Section 4) -- and
re-links every Resource to whichever of those canonical levers its own
shorthand "Grading levers:" tag clearly matches.

Run this AFTER seed_resources (it looks resources up by name).

This replaces the placeholder GradingLever rows that seed_resources used
to invent per-resource (same text duplicated in both up/down fields).
Those placeholders are deleted here and replaced with real, doc-sourced
up/down splits.

Not every resource-level tag maps cleanly onto a domain's canonical
levers -- many are more granular than the domain doc's short official
list (e.g. "bead hole size," "path width," "game difficulty setting").
Those are left unlinked rather than force-mapped or invented; the
original wording is still preserved in the resource's own record (name,
notes, etc.) even where it isn't reflected in a GradingLever link.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from planner.management.commands.seed_resources import (
    DOMAIN_SLUGS,
    RESOURCES,
    split_top_level_commas,
)
from planner.models import Domain, GradingLever, Resource


# (name, grade_down_description, grade_up_description) -- transcribed verbatim
# from each domain reference doc's "Grading levers" table.
CANONICAL_LEVERS = {
    "fine": [
        ("Tool size/grip", "Thicker pencil/crayon, built-up grip", "Standard pencil, no grip aid"),
        ("Surface angle", "Vertical surface (easel/wall) — supports wrist extension", "Flat table — requires more independent wrist control"),
        ("Resistance", "Soft surface (playdough, sand tray)", "Firm surface, resistive tools (tweezers, clothespins)"),
        ("Visual support", "High-contrast lines, dot-to-dot guides, stencils", "No guides, freehand"),
        ("Movement scale", "Large scale (whole arm, whiteboard)", "Small scale (fine detail, small paper)"),
        ("Bilateral demand", "One-handed task", "Requires stabilizing hand + working hand together"),
        ("In-hand manipulation", "Object pre-positioned in hand", "Child must reposition object within hand mid-task (e.g. shift, rotate, translate)"),
        ("Cognitive load", "Single-step, no time pressure", "Multi-step sequence, timed, or combined with a distraction/dual task"),
        ("Sensory input", "Calming/predictable input first (e.g. weighted tool, proprioceptive warmup)", "Task performed with typical/variable sensory input"),
    ],
    "self_care": [
        ("Garment/tool choice", "Elastic waist, velcro shoes, larger buttons", "Zippers, laces, small buttons, standard cutlery"),
        ("Sequencing support", "Backward chaining (therapist does most steps, child does the last) or visual step-by-step cards", "No visual supports; full sequence independently"),
        ("Physical setup", "Garment pre-oriented/positioned for the child", "Child retrieves and orients the garment themselves"),
        ("Prompting level", "Hand-over-hand or full physical assist", "Verbal cue only, or fully independent"),
        ("Environment", "Quiet, low-distraction space; familiar setting", "Busier/noisier real-world setting (e.g. shared bathroom, time pressure of getting ready for school)"),
        ("Time pressure", "No time constraint", 'Real-world time pressure (e.g. "get dressed before the bell")'),
        ("Sensory tolerance", "Preferred textures/temperatures", "Introduce non-preferred textures gradually, only once tolerance allows"),
    ],
    "gross": [
        ("Base of support", "Wide stance, seated", "Narrow stance, single-leg"),
        ("Surface stability", "Firm, flat ground", "Uneven surface, foam, balance beam"),
        ("Speed", "Slow, self-paced", "Fast, timed"),
        ("Distance/height", "Short distance, low obstacles", "Longer distance, higher obstacles"),
        ("External support", "Holding a rail/adult hand", "Independent"),
        ("Predictability", "Static target (a stationary ball to kick)", "Reactive/moving target (a rolling or thrown ball)"),
        ("Movement complexity", "Single movement pattern", "Combined/dual-task (running while catching, or following changing verbal instructions while moving)"),
        ("Sensory pairing", "Eyes open, quiet environment", "Eyes closed briefly (balance challenge), busier/louder environment"),
    ],
    "sensory": [
        ("Input intensity", "Light, gentle", "Firm/deep pressure or more intense input, depending on the child's actual sensory profile — more intense isn't inherently \"harder,\" it depends on what regulates vs. dysregulates this specific child"),
        ("Predictability", "Expected, self-initiated input", "Novel or externally introduced input"),
        ("Duration", "Brief exposure", "Sustained exposure"),
        ("Prompting level", "Full physical guidance to use a strategy", "Independent self-initiation"),
        ("Context complexity", "Calm, 1:1, low-stimulation setting", "Busier, higher-demand real-world setting"),
        ("Choice structure", "One offered strategy", "A menu of options the child selects from"),
        ("Control", "Adult-directed input", "Self-directed — child controls what, how much, and when"),
    ],
    "visual": [
        ("Field complexity", "Plain background", "Busy/cluttered background with distractors"),
        ("Target size", "Larger relative to the field", "Smaller relative to the field"),
        ("Number of distractors", "Few or none", "Many, and/or visually similar to the target"),
        ("Time constraint", "Untimed", "Timed"),
        ("Format", "3D/physical (blocks, real objects)", "2D/abstract (paper, screen) — 3D is generally the easier starting format"),
        ("Visual cueing", "Highlighted/color-coded cues provided", "No cues"),
        ("Stimulus familiarity", "Familiar, personally meaningful images/objects", "Novel, unfamiliar stimuli"),
    ],
    "emotional": [
        ("Vocabulary complexity", "Basic categories (mad/sad/happy)", "Nuanced/blended feelings (frustrated, disappointed, embarrassed)"),
        ("Prompting level", "Adult names the feeling for the child", "Child identifies independently"),
        ("Scenario familiarity", "Scripted, hypothetical, or story-based scenario", "Novel, real, in-the-moment situation"),
        ("Abstractness", "Concrete visual supports (feelings cards, a scale)", "Verbal-only discussion"),
        ("Social complexity", "1:1 practice", "Group/peer context"),
        ("Stakes", "Low-stakes hypothetical or a deliberately low-investment practice scenario", "A real, personally significant situation"),
        ("Strategy menu", "One strategy offered", "Several options to choose from"),
    ],
    "play": [
        ("Number of peers", "1:1 with an adult", "1:1 with a peer → small group → larger group"),
        ("Structure", "Highly structured/scripted game", "Open-ended free play"),
        ("Familiarity", "Familiar sibling/friend", "Less familiar peer"),
        ("Predictability", "Repeated, familiar play scenario", "Novel or flexible scenario"),
        ("Adult scaffolding", "Adult fully models and prompts each turn", "Independent initiation and turn-taking"),
        ("Play complexity", "Single-step functional play", "Multi-step symbolic/sociodramatic play with roles"),
        ("Environmental demand", "Quiet, controlled space", "Busier social environment (e.g. playground)"),
        ("Duration", "Short, defined engagement window", "Sustained, open-ended engagement"),
    ],
}

# Map a resource's domain key onto the canonical-lever set it should draw from.
CANONICAL_DOMAIN_FOR = {
    "fine": "fine",
    "dressing": "self_care",
    "grooming": "self_care",
    "feeding": "self_care",
    "toileting": "self_care",
    "gross": "gross",
    "sensory": "sensory",
    "visual": "visual",
    "emotional": "emotional",
    "play": "play",
}

# (substring to look for in the lever's short name/text, canonical lever name)
# checked in order, first match wins, per canonical domain.
KEYWORD_RULES = {
    "fine": [
        ("resistance", "Resistance"),
        ("visual support", "Visual support"),
        ("guide", "Visual support"),
        ("cue", "Visual support"),
        ("highlighting", "Visual support"),
        ("cognitive load", "Cognitive load"),
        ("tool size", "Tool size/grip"),
        ("grip", "Tool size/grip"),
        ("bilateral", "Bilateral demand"),
        ("in-hand manipulation", "In-hand manipulation"),
        ("movement scale", "Movement scale"),
        ("sensory input", "Sensory input"),
        ("incline", "Surface angle"),
        ("surface angle", "Surface angle"),
    ],
    "self_care": [
        ("fastener", "Garment/tool choice"),
        ("garment", "Garment/tool choice"),
        ("sequenc", "Sequencing support"),
        ("steps shown", "Sequencing support"),
        ("visual step", "Sequencing support"),
        ("picture card", "Sequencing support"),
        ("pre-oriented", "Physical setup"),
        ("physical setup", "Physical setup"),
        ("prompting", "Prompting level"),
        ("hand-over-hand", "Prompting level"),
        ("verbal cue", "Prompting level"),
        ("environment", "Environment"),
        ("noisy", "Environment"),
        ("quiet", "Environment"),
        ("time pressure", "Time pressure"),
        ("countdown", "Time pressure"),
        ("interval", "Time pressure"),
        ("texture", "Sensory tolerance"),
        ("sensory tolerance", "Sensory tolerance"),
    ],
    "gross": [
        ("stance", "Base of support"),
        ("base of support", "Base of support"),
        ("surface", "Surface stability"),
        ("speed", "Speed"),
        ("distance", "Distance/height"),
        ("height", "Distance/height"),
        ("level of support", "External support"),
        ("rail", "External support"),
        ("target", "Predictability"),
        ("dual-task", "Movement complexity"),
        ("movement pattern complexity", "Movement complexity"),
        ("eyes", "Sensory pairing"),
    ],
    "sensory": [
        ("weight", "Input intensity"),
        ("resistance/texture intensity", "Input intensity"),
        ("firmness", "Input intensity"),
        ("degree of noise reduction", "Input intensity"),
        ("glitter density", "Input intensity"),
        ("duration", "Duration"),
        ("number of options", "Choice structure"),
        ("enclosure size", "Context complexity"),
        ("lighting", "Context complexity"),
    ],
    "visual": [
        ("field complexity", "Field complexity"),
        ("image complexity", "Field complexity"),
        ("scene busyness", "Field complexity"),
        ("target size", "Target size"),
        ("similarity", "Number of distractors"),
        ("distractors", "Number of distractors"),
        ("2d card vs. 3d model", "Format"),
        ("familiarity of the sequence", "Stimulus familiarity"),
    ],
    "emotional": [
        ("number of feelings shown", "Vocabulary complexity"),
        ("number of emotions in play", "Vocabulary complexity"),
        ("number of strategy options", "Strategy menu"),
        ("number of example scenarios", "Scenario familiarity"),
        ("game length/stakes", "Stakes"),
        ("abstractness of the reframe", "Abstractness"),
    ],
    "play": [
        ("number of players", "Number of peers"),
        ("structured role vs. open-ended", "Structure"),
        ("structured vs. open-ended", "Structure"),
        ("familiar vs. novel", "Familiarity"),
        ("independent vs. shared/collaborative", "Adult scaffolding"),
    ],
}


class Command(BaseCommand):
    help = "Seed canonical per-domain GradingLever tables and re-link resources to them"

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            domains = {key: Domain.objects.get(slug=slug) for key, slug in DOMAIN_SLUGS.items()
                       if key in CANONICAL_LEVERS or key == "self_care"}
        except Domain.DoesNotExist as exc:
            raise CommandError(
                "Domains not found — run `manage.py seed_resources` first."
            ) from exc

        # Clean slate: drop the old ad-hoc/placeholder levers seed_resources made.
        GradingLever.objects.all().delete()

        canonical_objs = {}
        for domain_key, levers in CANONICAL_LEVERS.items():
            domain = domains[domain_key]
            for name, down, up in levers:
                lever = GradingLever.objects.create(
                    domain=domain, name=name,
                    grade_down_description=down, grade_up_description=up,
                )
                canonical_objs[(domain_key, name)] = lever

        linked = 0
        unmatched_segments = []
        for (name, rtype, domain_keys, sub_skill_names, age_range, cost_type,
             cost_amount, extra) in RESOURCES:
            grading_levers_text = extra.get("grading_levers_text")
            if not grading_levers_text:
                continue

            resource = Resource.objects.get(name=name)
            candidate_domains = list(dict.fromkeys(
                CANONICAL_DOMAIN_FOR[k] for k in domain_keys if k in CANONICAL_DOMAIN_FOR
            ))

            matched = []
            for segment in split_top_level_commas(grading_levers_text):
                lever_name = segment.split("(", 1)[0].strip().lower()
                found = None
                for domain_key in candidate_domains:
                    for keyword, canonical_name in KEYWORD_RULES.get(domain_key, []):
                        if keyword in lever_name or keyword in segment.lower():
                            found = canonical_objs[(domain_key, canonical_name)]
                            break
                    if found:
                        break
                if found:
                    if found not in matched:
                        matched.append(found)
                else:
                    unmatched_segments.append(f"{name}: {segment}")

            resource.grading_levers.set(matched)
            linked += len(matched)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {sum(len(v) for v in CANONICAL_LEVERS.values())} canonical grading levers "
            f"across {len(CANONICAL_LEVERS)} domains; created {linked} resource<->lever links."
        ))
        self.stdout.write(
            f"{len(unmatched_segments)} resource-level grading-lever tags didn't map to a "
            f"canonical lever (too granular/product-specific to fit the domain's official list "
            f"— left unlinked rather than guessed). Run with -v 2 to list them."
        )
        if options["verbosity"] >= 2:
            for line in unmatched_segments:
                self.stdout.write(f"  - {line}")

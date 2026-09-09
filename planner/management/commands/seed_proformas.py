"""
Seeds the diagnosis/disability proforma layer (Phase 0's
diagnosis-proforma-schema-v1.md and the 5 proforma docs: CVI, autism,
Down syndrome, cerebral palsy, ADHD).

Idempotent: matched by Proforma.name (unique), safe to re-run.

Known gap: a few "Cross-domain implications" table rows reference
domains outside the project's 7-domain OT taxonomy -- "Communication/AAC",
"Communication/social", "Communication/play" (explicitly SLP's territory
per the scope-of-practice principle) and CVI's "Any domain, generally"
row (genuinely cross-cutting, not one domain). ProformaDomainImplication
requires a real Domain FK, so those rows are skipped rather than forced
onto a domain they don't belong to -- their guidance is still readable in
the source proforma docs, just not represented as a structured row here.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from planner.models import Domain, Proforma, ProformaDomainImplication


PROFORMAS = [
    {
        "name": "Cortical/Cerebral Visual Impairment (CVI)",
        "brief_description": (
            "CVI is visual dysfunction caused by damage or injury to the brain's visual "
            "processing pathways, rather than a problem with the eyes themselves — the "
            "leading cause of pediatric visual impairment in developed countries. "
            "Presentation and severity vary widely and are typically described along a "
            "range/phase system (Roman-Lantzy's CVI Range) from significant impairment "
            "(Phase I) toward substantially resolved functional vision (Phase III), "
            "though CVI is lifelong even when functional vision improves markedly."
        ),
        "presentation_characteristics": (
            "Ten characteristics are commonly described in the CVI literature "
            "(Roman-Lantzy): color preference, need for movement, visual latency "
            "(needing extra processing time), visual field preferences, difficulty with "
            "visual complexity, light-gazing or nonpurposeful gaze, absence of visually "
            "guided reach, difficulty with distance viewing, atypical visual reflexes, "
            "and an \"antinovelty\" response (preferring familiar visual targets over "
            "new ones). Not every characteristic is present in every child, and the "
            "degree of each varies by where the child sits on the CVI Range."
        ),
        "general_adaptations": (
            "Use the child's known preferred color as a cue/highlight across materials "
            "in any domain, not just vision-specific tasks. Favor objects with movement "
            "or light-reflecting properties over static ones when trying to draw visual "
            "attention. Keep backgrounds plain and uncluttered during any task requiring "
            "visual engagement. Allow generous latency — pause and wait for a visual "
            "response rather than moving on quickly, especially with anything novel. "
            "Favor familiar, repeated objects over introducing novel ones for engagement "
            "— this cuts against the usual instinct to vary materials. Never require "
            "reach/grasp and visual attention simultaneously without confirming the "
            "child can actually do both at once."
        ),
        "scope_collaboration_notes": (
            "A Teacher of the Visually Impaired (TVI) or CVI specialist is standard "
            "alongside OT for CVI cases — this is specialized enough that OT working in "
            "isolation, without that collaboration, would be unusual. "
            "Ophthalmology/neurology involvement is typically already established via "
            "diagnosis, but worth confirming it's current if presentation is changing."
        ),
        "evidence_base_note": (
            "Roman-Lantzy, C. Cortical Visual Impairment: An Approach to Assessment and "
            "Intervention (source for the CVI Range, the 10 characteristics, and "
            "Phase-based intervention principles referenced above)."
        ),
        "individual_variability_caution": (
            "CVI variability is unusually wide even by the standards of this caution "
            "generally — presentation differs enormously depending on where a child sits "
            "on the CVI Range, and two children with the same diagnosis label can look "
            "completely different functionally. The Phase/Range assumed in any specific "
            "case should always be treated as a hypothesis pending confirmation from "
            "whoever has actually assessed the child's CVI Range, not asserted by the "
            "app or by general pattern-matching."
        ),
        "domain_implications": [
            ("visual",
             "Core domain affected — difficulty with figure-ground, visual complexity, novel visual stimuli",
             "Standard visual perception grading levers (busier field = harder) may not apply the same way — complexity itself, not just clutter, is the barrier"),
            ("fine",
             "Absence of visually guided reach means looking and reaching may not yet happen together",
             "Don't require visual attention and motor grasp simultaneously in early-stage activities — isolate them, the way the real CVI case did"),
            ("self_care",
             "Visual complexity of an environment (e.g. a busy bathroom, a patterned garment) may reduce visual engagement with the task",
             "Simplify visual field during self-care tasks — plain backgrounds, preferred-color cues on key items (e.g. the shoe-bin example from CVI literature)"),
        ],
        "related": [],
    },
    {
        "name": "Autism",
        "brief_description": (
            "Autism is a neurodevelopmental difference characterized by differences in "
            "social communication and interaction, alongside restricted or focused "
            "interests and variable sensory processing differences. It is a spectrum in "
            "the fullest sense — presentation, communication mode, and support needs "
            "vary enormously between individuals sharing the diagnosis."
        ),
        "presentation_characteristics": (
            "Social communication differences (which may include reduced eye contact, "
            "differences in reciprocal conversation, and a communication mode ranging "
            "from strong verbal skills to non-verbal/minimally verbal with AAC use); "
            "restricted or intensely focused interests, often with deep topic knowledge, "
            "which can function as strong motivators rather than only a challenge to "
            "manage; sensory processing differences that are typically modality-specific "
            "rather than uniform (over- or under-responsive in different channels); a "
            "preference for routine and predictability, with difficulty around "
            "unexpected transitions or change; repetitive movements/self-stimulatory "
            "behavior (stimming), which is often genuinely self-regulatory rather than "
            "something to eliminate; masking/camouflaging, which is common (especially "
            "with age and in certain social contexts) and can obscure a child's actual "
            "internal state; and frequent co-occurrence with ADHD, anxiety, intellectual "
            "disability, epilepsy, or GI differences — all variable, not universal."
        ),
        "general_adaptations": (
            "Leverage special interests as motivators across any domain, not just "
            "play-based ones — this has been the single most consistent pattern across "
            "every worked example in this project. Build in predictability and visual "
            "supports around transitions. Don't assume masking indicates a child's true "
            "internal state; build in proactive regulation checkpoints rather than "
            "reactive ones. Confirm communication mode and preferences before assuming a "
            "typical verbal exchange is the right medium. Avoid assuming a specific "
            "sensory profile — confirm it individually, since sensitivities are "
            "modality-specific and vary widely. When teaching social skills, favor "
            "concrete/explicit strategies over approaches that rely on intuiting "
            "unstated social cues."
        ),
        "scope_collaboration_notes": (
            "SLP (communication/pragmatics) and psychology (behavior support, "
            "co-occurring anxiety) are common partners. Some families use additional "
            "behavioral therapy approaches (e.g. ABA) and others deliberately avoid them "
            "— this is a genuine area of differing views within the autism community and "
            "among families, and should be treated as a family/care-team decision to "
            "respect, not something OT assumes a position on. Developmental pediatrics "
            "often coordinates overall care."
        ),
        "evidence_base_note": (
            "General pediatric OT literature on autism and neurodiversity-informed "
            "practice; patterns reflected here are broad and well-established rather "
            "than drawn from a single source."
        ),
        "individual_variability_caution": (
            "Autism is defined as a spectrum precisely because presentation varies "
            "enormously — communication mode, sensory profile, support needs, and "
            "co-occurring conditions differ dramatically between individuals sharing "
            "this diagnosis. Never assume a specific characteristic applies without "
            "confirming it in the individual child's actual documented presentation."
        ),
        "domain_implications": [
            ("fine",
             "Motor planning/praxis differences sometimes present",
             "Confirm rather than assume; special interests remain a strong motivator regardless"),
            ("gross",
             "Novel movement sequences may be harder than familiar/routine ones",
             "Favor predictable, repeated movement patterns when introducing new gross motor skills"),
            ("self_care",
             "Sensory sensitivities commonly affect tolerance for specific textures/tasks (clothing, food, hygiene)",
             "Confirm the child's specific sensory profile rather than assuming a generic aversion pattern"),
            ("sensory",
             "Core relevant domain — processing differences are common but individual, not uniform",
             "Individually assess; don't assume a stereotyped sensory profile"),
            ("emotional",
             "Alexithymia (difficulty identifying/describing own emotions) sometimes present; masking can hide distress",
             "Build in proactive, non-optional regulation checkpoints rather than relying on self-report — the masking-aware principle applies especially directly here"),
            ("visual",
             "Variable; not a uniform or defining feature",
             "Confirm individually rather than assuming a pattern"),
            ("play",
             "Differences in reciprocal play/joint attention common; special interests can dominate conversation and play",
             "Favor concrete, explicit strategies (e.g. turn-taking tools) over relying on implicit social-cue reading — directly reflected in the real worked example built earlier in this project"),
        ],
        "related": [],
    },
    {
        "name": "Down Syndrome",
        "brief_description": (
            "Down syndrome is a genetic condition (trisomy 21) commonly associated with "
            "hypotonia (low muscle tone), joint hypermobility, some degree of "
            "intellectual disability (variable in extent), and an increased likelihood "
            "of certain co-occurring health conditions."
        ),
        "presentation_characteristics": (
            "Hypotonia is very commonly present and affects motor development broadly — "
            "delayed gross and fine motor milestones, and joint hypermobility/"
            "ligamentous laxity. A specific safety-relevant consideration: atlantoaxial "
            "instability (a laxity at the top of the spine) occurs at higher rates and "
            "is relevant to any activity involving significant neck flexion or "
            "high-impact movement — this needs medical clearance before certain gross "
            "motor activities, not an assumption either way. Motor milestones are "
            "typically delayed but often follow a similar developmental sequence at a "
            "slower pace, rather than a fundamentally different pattern. Expressive "
            "language is frequently more delayed than receptive understanding/"
            "comprehension — a gap worth remembering so comprehension isn't "
            "underestimated based on limited expressive output. Oral motor differences "
            "are common and relevant to feeding. Intellectual disability is common but "
            "variable in degree — not universal or uniform in severity. Common "
            "co-occurring conditions include congenital heart defects, hearing and "
            "vision differences, thyroid conditions, and sleep apnea, all of which can "
            "affect overall endurance and presentation."
        ),
        "general_adaptations": (
            "Build in extra processing and response time given the common "
            "expressive-receptive language gap. Confirm any movement/positioning "
            "precautions (particularly atlantoaxial instability) with the medical/PT "
            "team before higher-risk gross motor activities. Grade motor tasks with "
            "awareness that hypotonia commonly affects endurance — the session-length "
            "block-scaling principle applies directly. Confirm current vision and "
            "hearing status given the increased likelihood of co-occurring "
            "sensory-organ differences, rather than assuming a visual-perceptual or "
            "auditory-processing explanation when uncorrected vision or hearing could "
            "be the actual factor."
        ),
        "scope_collaboration_notes": (
            "PT is a core partner given the motor/postural focus. SLP for "
            "speech/language and oral motor/feeding. Audiology and optometry given the "
            "increased likelihood of sensory-organ differences. Cardiology/pediatrics "
            "where a congenital heart condition is present and relevant to activity "
            "tolerance."
        ),
        "evidence_base_note": (
            "General pediatric Down syndrome OT/PT literature; atlantoaxial instability "
            "guidance is well-established in pediatric orthopedic and Down syndrome "
            "medical literature specifically."
        ),
        "individual_variability_caution": (
            "Motor and cognitive presentation varies significantly — not every child "
            "has every characteristic listed here (not all have significant "
            "intellectual disability; not all have a congenital heart defect). Confirm "
            "actual current medical history and status rather than assuming "
            "co-occurring conditions are present just because they're common in the "
            "broader population with this diagnosis."
        ),
        "domain_implications": [
            ("fine",
             "Hypotonia and joint laxity affect grasp development and precision",
             "May need more time at each grasp developmental stage; confirm rather than rush the sequence"),
            ("gross",
             "Motor milestones typically delayed; hypotonia affects postural control and endurance",
             "The postural/endurance patterns already built into this project's gross motor work apply directly; confirm atlantoaxial instability status before higher-risk neck-flexion activities"),
            ("self_care",
             "Motor components may take longer but often follow a similar sequence; oral motor differences relevant to feeding specifically",
             "Allow more time within the same developmental sequence rather than assuming a different one"),
            ("sensory",
             "Not a defining/core feature the way it is in autism",
             "Assess individually rather than assuming a pattern"),
            ("visual",
             "Increased likelihood of vision differences (refractive errors more common)",
             "Confirm current vision correction/status before assuming a visual-perceptual (rather than uncorrected visual) cause for a difficulty"),
        ],
        "related": [],
    },
    {
        "name": "Cerebral Palsy",
        "brief_description": (
            "Cerebral palsy (CP) is a group of permanent movement and posture disorders "
            "caused by a non-progressive disturbance in the developing brain — though "
            "the resulting movement presentation itself can change as the child grows. "
            "Classified by movement type (spastic, dyskinetic, ataxic, or mixed) and by "
            "distribution (e.g. hemiplegia, diplegia, quadriplegia), and functionally "
            "via the Gross Motor Function Classification System (GMFCS, Levels I–V) and "
            "Manual Ability Classification System (MACS) for hand function."
        ),
        "presentation_characteristics": (
            "Muscle tone differences (increased/spastic, decreased/hypotonic, or "
            "fluctuating/dyskinetic — type varies significantly and must be confirmed, "
            "not assumed). Motor control and coordination differences affecting "
            "voluntary movement. Distribution varies (one side, both legs, all four "
            "limbs), which meaningfully changes functional presentation. Common "
            "co-occurring factors: communication differences (some children are "
            "non-verbal and use AAC), visual differences including a meaningfully "
            "higher rate of CVI (since both CP and CVI can share the same "
            "early-brain-injury origin), variable intellectual differences (not "
            "universal), epilepsy, and feeding/swallowing (oral motor) differences. "
            "Functional mobility and hand function both vary enormously — far more by "
            "GMFCS/MACS level than by the CP diagnosis label alone."
        ),
        "general_adaptations": (
            "Always confirm GMFCS and MACS level (or general current functional status "
            "if formal classification isn't available) before planning activities — "
            "this is the single most important thing to establish, more so than for "
            "almost any other proforma in this library, since functional presentation "
            "varies so much within the diagnosis. Confirm communication mode. Confirm "
            "whether CVI or other visual differences co-occur, and if so, apply the CVI "
            "proforma alongside this one rather than treating either in isolation. "
            "Adaptive equipment and positioning needs should be confirmed with the "
            "current PT/seating team rather than assumed or designed independently by "
            "OT alone."
        ),
        "scope_collaboration_notes": (
            "PT is a core partner given the shared motor focus. SLP for communication "
            "and feeding/oral motor. Orthotics and seating specialists for positioning "
            "equipment. Ophthalmology/TVI where CVI is present. Neurology, particularly "
            "where epilepsy co-occurs."
        ),
        "evidence_base_note": (
            "General pediatric CP literature; GMFCS and MACS are well-established, "
            "widely used standardized classification systems in this field "
            "specifically."
        ),
        "individual_variability_caution": (
            "CP presentation varies more by functional classification (GMFCS/MACS) and "
            "by CP type/distribution than by the diagnosis label itself — two children "
            "both labeled \"cerebral palsy\" can have almost entirely different "
            "functional presentations, from independent ambulation to full physical "
            "assistance, and from typical hand function to very limited manual "
            "ability. Never infer functional level from the diagnosis alone; always "
            "confirm current classification and functional status directly."
        ),
        "domain_implications": [
            ("fine",
             "Hand function significantly variable depending on MACS level and CP type/distribution",
             "Confirm MACS level or current functional hand use rather than assuming from age; adapted grips/tools often relevant"),
            ("gross",
             "Core domain affected",
             "GMFCS level should inform realistic starting points far more than chronological age"),
            ("self_care",
             "Physical assistance needs vary by GMFCS/MACS level",
             "Adaptive equipment is often relevant — apply the same garment/tool-adaptation grading levers already built into the self-care domain doc"),
            ("sensory",
             "CVI co-occurs at meaningfully higher rates given the shared early-brain-injury origin",
             "Confirm CVI status specifically — if present, apply the CVI proforma alongside this one rather than either proforma alone"),
            ("visual",
             "CVI co-occurs at meaningfully higher rates given the shared early-brain-injury origin",
             "Confirm CVI status specifically — if present, apply the CVI proforma alongside this one rather than either proforma alone"),
        ],
        "related": ["Cortical/Cerebral Visual Impairment (CVI)"],
    },
    {
        "name": "ADHD",
        "brief_description": (
            "ADHD (attention-deficit/hyperactivity disorder) is a neurodevelopmental "
            "condition characterized by patterns of inattention, hyperactivity, and/or "
            "impulsivity that affect functioning. It presents across three recognized "
            "subtypes — predominantly inattentive, predominantly hyperactive-impulsive, "
            "and combined — which can look very different from one another "
            "functionally."
        ),
        "presentation_characteristics": (
            "Presentation type significantly changes what support looks like: the "
            "inattentive presentation may appear \"quiet\" or underengaged rather than "
            "disruptive, and is frequently under-identified, especially in girls. "
            "Difficulty sustaining attention on non-preferred tasks is common, but this "
            "is often paired with strong, even intense sustained attention (hyperfocus) "
            "on highly preferred or interesting tasks — an important nuance, since the "
            "pattern is task-dependent rather than a uniform inability to focus. "
            "Impulsivity can affect turn-taking, waiting, and motor impulse control. "
            "Motor restlessness/fidgeting is common and often serves a genuine "
            "regulatory or attention-supporting function rather than being purely "
            "disruptive behavior. Executive function differences (planning, "
            "organization, working memory, task initiation) frequently extend beyond "
            "attention itself. Common co-occurrences include anxiety, learning "
            "differences, autism, and emotional regulation differences such as "
            "heightened rejection sensitivity or intense reactions."
        ),
        "general_adaptations": (
            "Distinguish \"can't sustain attention\" from \"hasn't been sufficiently "
            "motivated or interested\" — leveraging genuine interests as strong "
            "motivators is the same pattern used successfully throughout every domain "
            "in this project, and applies directly here. Build in movement breaks "
            "proactively rather than only once attention has already broken down. Keep "
            "instructions concrete and short given common working memory "
            "considerations. Recognize fidgeting and movement as often supportive of "
            "attention rather than purely a behavior to suppress or redirect away from."
        ),
        "scope_collaboration_notes": (
            "Pediatrics/psychiatry where medication is part of the picture — this is "
            "entirely a family/medical decision, not something OT weighs in on. "
            "Psychology for behavior support and co-occurring anxiety. School-based "
            "teams for classroom accommodations, since a significant part of ADHD "
            "support often happens in the educational environment rather than the "
            "therapy room alone."
        ),
        "evidence_base_note": (
            "General pediatric ADHD and OT literature; the three-presentation subtype "
            "framework reflects the standard diagnostic classification (DSM-5)."
        ),
        "individual_variability_caution": (
            "Presentation type (inattentive, hyperactive-impulsive, or combined) "
            "significantly changes what support looks like — an inattentive-"
            "presentation child may look nothing like the stereotyped hyperactive image "
            "and is easily under-identified as a result. Confirm the child's actual "
            "presentation rather than assuming the more commonly recognized stereotype "
            "applies."
        ),
        "domain_implications": [
            ("fine",
             "Attention/impulsivity can affect written output quality or completion more than the underlying motor skill itself",
             "Distinguish \"can't\" from \"hasn't sustained attention to\" as the actual component gap — the same reasoning pattern used throughout this project"),
            ("gross",
             "Movement breaks are often genuinely regulatory and support subsequent attention, not just a reward",
             "Build movement breaks proactively into session structure, applying the session-length block-scaling principle to attentional endurance specifically"),
            ("sensory",
             "Fidget tools and movement-based regulation are often particularly effective",
             "Favor these over asking a child to simply \"sit still and focus\""),
            ("emotional",
             "Emotional reactivity and rejection sensitivity are common",
             "May need more explicit, concrete regulation supports, similar to patterns already built for other domains"),
            ("play",
             "Impulsivity can affect turn-taking and reciprocal play; strong engagement/hyperfocus can appear within highly preferred play specifically",
             "Don't read inconsistent engagement across activities as motivation alone — it may reflect genuine attentional variability by task"),
        ],
        "related": [],
    },
]


class Command(BaseCommand):
    help = "Seed the diagnosis/disability proforma layer"

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            domains = {
                "fine": Domain.objects.get(slug="fine-motor-handwriting"),
                "self_care": Domain.objects.get(slug="self-care-adls"),
                "gross": Domain.objects.get(slug="gross-motor"),
                "sensory": Domain.objects.get(slug="sensory-regulation"),
                "visual": Domain.objects.get(slug="visual-perception-visual-motor"),
                "emotional": Domain.objects.get(slug="emotional-regulation"),
                "play": Domain.objects.get(slug="play-leisure-social"),
            }
        except Domain.DoesNotExist as exc:
            raise CommandError(
                "Domains not found — run `manage.py seed_resources` first."
            ) from exc

        proforma_objs = {}
        skipped_relations = []
        for entry in PROFORMAS:
            defaults = {
                "brief_description": entry["brief_description"],
                "presentation_characteristics": entry["presentation_characteristics"],
                "general_adaptations": entry["general_adaptations"],
                "scope_collaboration_notes": entry["scope_collaboration_notes"],
                "evidence_base_note": entry["evidence_base_note"],
                "individual_variability_caution": entry["individual_variability_caution"],
                "status": Proforma.Status.DRAFT,
            }
            proforma, _ = Proforma.objects.update_or_create(
                name=entry["name"], defaults=defaults,
            )
            proforma_objs[entry["name"]] = proforma

            ProformaDomainImplication.objects.filter(proforma=proforma).delete()
            for domain_key, how_it_shows_up, design_implication in entry["domain_implications"]:
                ProformaDomainImplication.objects.create(
                    proforma=proforma,
                    domain=domains[domain_key],
                    how_it_shows_up=how_it_shows_up,
                    design_implication=design_implication,
                )

        for entry in PROFORMAS:
            proforma = proforma_objs[entry["name"]]
            related = []
            for related_name in entry["related"]:
                if related_name in proforma_objs:
                    related.append(proforma_objs[related_name])
                else:
                    skipped_relations.append((entry["name"], related_name))
            if related:
                proforma.related_proformas.add(*related)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(proforma_objs)} proformas with "
            f"{sum(len(e['domain_implications']) for e in PROFORMAS)} domain implications."
        ))
        if skipped_relations:
            self.stdout.write(self.style.WARNING(f"Skipped relations: {skipped_relations}"))

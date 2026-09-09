"""
Django models for the paediatric therapy session planner.

Maps directly onto the Phase 0 documents:
  - resource-tagging-schema-v1.md          -> Resource
  - diagnosis-proforma-schema-v1.md        -> Proforma, ProformaDomainImplication
  - each domain's grading-levers table     -> GradingLever
  - each domain's foundational-skills list -> SubSkill
  - the 5-screen paper prototype           -> Child, Goal, OptionPoint, SessionPlan, ActivityBlock, HomeProgram

This is a single file for readability while you're learning the shape of it —
in a real Django project you'd likely split this into a few apps
(e.g. `clinical_content` for Domain/Resource/Proforma, `clients` for Child,
`plans` for Goal/SessionPlan/ActivityBlock/HomeProgram). Not required for
Phase 1 to work; just a note for when the file starts feeling too big.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# ---------------------------------------------------------------------------
# Reference / taxonomy models
# ---------------------------------------------------------------------------

class Domain(models.Model):
    """The seven domains from the Phase 0 reference docs."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    # e.g. "self-care/dressing" as a sub-domain of "self-care" — optional,
    # only self-care currently needs this per the Phase 0 docs.
    parent_domain = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="sub_domains",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SubSkill(models.Model):
    """Foundational skills underneath a domain (Section 1 of each domain doc)."""
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="sub_skills")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.domain.name})"


class GradingLever(models.Model):
    """A grading lever row from a domain's grading-levers table."""
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, related_name="grading_levers")
    name = models.CharField(max_length=150)
    grade_down_description = models.TextField(help_text="How to make it easier")
    grade_up_description = models.TextField(help_text="How to make it harder")

    def __str__(self):
        return f"{self.name} ({self.domain.name})"


class Interest(models.Model):
    """Simple tag for a child's interests, used for interest-matching activities."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Diagnosis proforma layer (diagnosis-proforma-schema-v1.md)
# ---------------------------------------------------------------------------

class Proforma(models.Model):
    """A diagnosis/disability proforma — cuts across domains, not tied to one."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        REVIEWED = "reviewed", "Reviewed"

    name = models.CharField(max_length=150, unique=True)
    brief_description = models.TextField()
    presentation_characteristics = models.TextField()
    general_adaptations = models.TextField()
    scope_collaboration_notes = models.TextField(
        help_text="Which other professionals commonly need to be involved"
    )
    evidence_base_note = models.TextField(blank=True)
    individual_variability_caution = models.TextField(
        help_text="Mandatory per the schema — never optional, even if brief"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Proformas can reference each other where they co-occur
    # (e.g. cerebral-palsy-proforma-v1.md pointing to cvi-proforma-v1.md).
    related_proformas = models.ManyToManyField("self", blank=True)

    def __str__(self):
        return self.name


class ProformaDomainImplication(models.Model):
    """One row of a proforma's 'cross-domain implications' table."""
    proforma = models.ForeignKey(Proforma, on_delete=models.CASCADE, related_name="domain_implications")
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    how_it_shows_up = models.TextField()
    design_implication = models.TextField()

    class Meta:
        unique_together = ("proforma", "domain")


# ---------------------------------------------------------------------------
# Resource library (resource-tagging-schema-v1.md)
# ---------------------------------------------------------------------------

class Resource(models.Model):
    """A single tagged resource. Every field maps to the schema doc directly."""

    class ResourceType(models.TextChoices):
        APP_DIGITAL = "app_digital", "App/digital"
        PHYSICAL_PRODUCT = "physical_product", "Physical product"
        HOUSEHOLD_ITEM = "household_item", "Household item"
        PRINTABLE = "printable", "Printable/worksheet"
        ENVIRONMENTAL_SETUP = "environmental_setup", "Environmental setup"

    class CostType(models.TextChoices):
        FREE = "free", "Free"
        ONE_TIME = "one_time", "One-time purchase"
        SUBSCRIPTION = "subscription", "Subscription"

    class ReviewStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        VERIFIED = "verified", "Verified"

    # --- Required fields ---
    name = models.CharField(
        max_length=200, unique=True,
        help_text="Must be specific and named — never a category (see resource specificity rule)",
    )
    resource_type = models.CharField(max_length=30, choices=ResourceType.choices)
    domains = models.ManyToManyField(Domain, related_name="resources")
    sub_skills = models.ManyToManyField(SubSkill, blank=True, related_name="resources")
    age_min_months = models.PositiveIntegerField(null=True, blank=True)
    age_max_months = models.PositiveIntegerField(null=True, blank=True)
    grading_levers = models.ManyToManyField(GradingLever, blank=True, related_name="resources")
    cost_type = models.CharField(max_length=20, choices=CostType.choices)
    cost_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # --- Conditional fields ---
    platform = models.CharField(max_length=100, blank=True, help_text="Digital resources only")
    grading_settings_note = models.TextField(
        blank=True, help_text="In-product settings that map to grading, for digital resources"
    )
    safety_flags = models.TextField(blank=True)
    sensory_profile = models.TextField(blank=True)

    # --- Optional fields ---
    interests = models.ManyToManyField(Interest, blank=True, related_name="resources")
    environment_suitability = models.CharField(max_length=200, blank=True)
    example_functional_play_framings = models.TextField(blank=True)
    cross_discipline_note = models.TextField(blank=True)
    family_cultural_note = models.TextField(blank=True)

    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Client profile
# ---------------------------------------------------------------------------

class Child(models.Model):
    """A client's profile — the intake screen from the paper prototype."""

    class Environment(models.TextChoices):
        CLINIC = "clinic", "Clinic"
        HOME = "home", "Home"
        SCHOOL = "school", "School"
        TELETHERAPY = "teletherapy", "Teletherapy"

    initial_or_name = models.CharField(max_length=100)
    age_years = models.PositiveIntegerField(validators=[MaxValueValidator(18)])
    age_months = models.PositiveIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(11)]
    )
    default_environment = models.CharField(max_length=20, choices=Environment.choices)
    interests = models.ManyToManyField(Interest, blank=True, related_name="children")
    proformas = models.ManyToManyField(
        Proforma, blank=True, related_name="children",
        help_text="Diagnoses noted for this child, if any",
    )
    current_presentation = models.TextField(
        help_text="Free text — grasp stage, endurance, sensory notes, sequencing ability, etc."
    )
    # Deliberately a free-text note, not a boolean — per the masking-aware
    # principle, this is a reminder for the therapist to consider and note
    # in their own words, not a field the app presumes to detect or decide.
    masking_note = models.TextField(
        blank=True,
        help_text="Therapist's own note on whether this child tends to mask distress, if relevant",
    )
    family_cultural_context = models.TextField(
        blank=True, help_text="Optional — only fill in if genuinely relevant"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.initial_or_name


# ---------------------------------------------------------------------------
# Goals, option points, session plans
# ---------------------------------------------------------------------------

class Goal(models.Model):
    """A goal for a child, refined into interim + outcome SMART goals."""
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="goals")
    domain = models.ForeignKey(Domain, on_delete=models.PROTECT, related_name="goals")
    raw_goal_text = models.TextField(help_text="The goal as the therapist first entered it")
    interim_goal_text = models.TextField(blank=True)
    outcome_goal_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.child} — {self.raw_goal_text[:50]}"


class OptionPoint(models.Model):
    """A judgment-dependent decision surfaced to the therapist, and their choice."""
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="option_points")
    question_text = models.TextField()
    options_json = models.JSONField(
        help_text='List of option strings, e.g. ["Isolation first", "Embedded in full routine"]'
    )
    selected_option = models.CharField(max_length=300, blank=True)
    rationale_note = models.TextField(
        blank=True, help_text="Why this depends on the therapist's/family's judgment, not a default"
    )

    def __str__(self):
        return self.question_text[:60]


class SessionPlan(models.Model):
    """A generated session plan for a goal."""
    goal = models.ForeignKey(Goal, on_delete=models.CASCADE, related_name="session_plans")
    session_length_minutes = models.PositiveIntegerField(default=45)
    environment = models.CharField(max_length=20, choices=Child.Environment.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Plan for {self.goal.child} ({self.session_length_minutes} min)"


class ActivityBlock(models.Model):
    """One block within a session plan — warm-up, main, warm-down, or a movement reset."""

    class BlockType(models.TextChoices):
        WARM_UP = "warm_up", "Warm-up"
        MAIN = "main", "Main"
        MOVEMENT_RESET = "movement_reset", "Movement reset"
        WARM_DOWN = "warm_down", "Warm-down"

    session_plan = models.ForeignKey(SessionPlan, on_delete=models.CASCADE, related_name="blocks")
    block_type = models.CharField(max_length=20, choices=BlockType.choices)
    order = models.PositiveIntegerField(help_text="Sequence within the session")
    duration_minutes = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    # Full setup + step-by-step sequence + payoff — per the functional-play
    # narrative principle, this must be complete enough to run as written.
    activity_description = models.TextField()
    clinical_reasoning = models.TextField()
    resources = models.ManyToManyField(Resource, blank=True, related_name="activity_blocks")
    grade_up_note = models.TextField(blank=True)
    grade_down_note = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.get_block_type_display()}: {self.title}"


# ---------------------------------------------------------------------------
# Home program (home-program-template-v1.md)
# ---------------------------------------------------------------------------

class HomeProgram(models.Model):
    """
    A derived output from a session plan — NOT the same object as a
    simplified export. Resources and content here are deliberately
    re-selected/rewritten for the home context, per the home program
    template's rules.
    """
    session_plan = models.OneToOneField(
        SessionPlan, on_delete=models.CASCADE, related_name="home_program"
    )
    goal_plain_language = models.TextField()
    why_this_helps = models.TextField(help_text="1-2 sentences, no clinical terminology")
    activity_description = models.TextField()
    home_resources = models.ManyToManyField(
        Resource, blank=True, related_name="home_programs",
        help_text="Should generally be filtered to free/household_item resource_type",
    )
    frequency = models.CharField(max_length=200, help_text='e.g. "3-4 times a week, 5 minutes"')
    grade_up_tip_plain = models.TextField(blank=True)
    grade_down_tip_plain = models.TextField(blank=True)
    safety_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Home program for {self.session_plan}"

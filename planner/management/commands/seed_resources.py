"""
Seeds the Resource library from the Phase 0 resource-library-batch1..11 docs
(resource-tagging-schema-v1.md defines the field meanings).

Idempotent: re-running updates existing rows (matched by Resource.name,
which is unique) rather than duplicating them, so it's safe to run again
after editing this file to correct/extend an entry.

Known gap: the source batches record "Grading levers" as a compact tag
per resource (e.g. "Resistance (soft <-> firm)") rather than as separate
grade-up/grade-down text. The domain reference docs (not yet loaded into
this project) are where that split properly lives. Until those are seeded,
each GradingLever created here carries the same unsplit tag text in both
grade_up_description and grade_down_description, clearly prefixed as
provisional -- refine once the domain docs are in.

Also note: the Phase 0 summary's own resource count ("100 resources") and
the sum of the 11 actual batch files (110 entries: 20 fine motor + 10 each
across dressing/grooming/feeding/toileting/gross motor/sensory/visual/
emotional/play) don't reconcile -- that mismatch is in the source docs
themselves. This command seeds all 110 entries that actually appear in
the batch files.
"""

import re

from django.core.management.base import BaseCommand
from django.db import transaction

from planner.models import Domain, GradingLever, Resource, SubSkill


DOMAIN_SLUGS = {
    "fine": "fine-motor-handwriting",
    "self_care": "self-care-adls",
    "dressing": "self-care-dressing",
    "grooming": "self-care-grooming",
    "feeding": "self-care-feeding",
    "toileting": "self-care-toileting",
    "gross": "gross-motor",
    "sensory": "sensory-regulation",
    "visual": "visual-perception-visual-motor",
    "emotional": "emotional-regulation",
    "play": "play-leisure-social",
}

DOMAIN_NAMES = {
    "fine": "Fine motor / handwriting",
    "self_care": "Self-care / ADLs",
    "dressing": "Self-care / Dressing",
    "grooming": "Self-care / Grooming",
    "feeding": "Self-care / Feeding",
    "toileting": "Self-care / Toileting",
    "gross": "Gross motor",
    "sensory": "Sensory regulation",
    "visual": "Visual perception / visual-motor",
    "emotional": "Emotional regulation",
    "play": "Play / leisure / social skills",
}

SELF_CARE_SUBDOMAINS = ["dressing", "grooming", "feeding", "toileting"]

FREE, ONE_TIME, SUBSCRIPTION = "free", "one_time", "subscription"
APP, PHYSICAL, HOUSEHOLD, PRINTABLE = (
    "app_digital",
    "physical_product",
    "household_item",
    "printable",
)


# Each entry: (name, type, [domain_keys], [sub_skill names], (age_min_months, age_max_months),
#              cost_type, cost_amount, extra dict of optional fields)
RESOURCES = [
    # --- Batch 1: Fine motor / handwriting ---
    ("Writing Wizard (app)", APP, ["fine"],
     ["Letter formation", "Name/word tracing", "Visual-motor integration"],
     (48, 84), ONE_TIME, 7.99,
     {"platform": "iPad, iOS",
      "grading_settings_note": "Trace-guide visibility, font (Zaner-Bloser/D'Nealian/HWT), letter size, free-play vs. 5-star mode",
      "grading_levers_text": "Visual support (trace-guide on/off), cognitive load (free-play vs. 5-star mode)"}),
    ("iTrace (app)", APP, ["fine"],
     ["Letter/word tracing", "Visual-motor integration"],
     (48, 96), ONE_TIME, None,
     {"platform": "iPad, iOS",
      "grading_settings_note": "Left/right-handed mode, font standard selection (matches school curriculum)",
      "grading_levers_text": "Visual support, handedness accommodation"}),
    ("Wet-Dry-Try (Learning Without Tears app)", APP, ["fine"],
     ["Letter formation", "Multisensory encoding"],
     (48, 84), ONE_TIME, None,
     {"platform": "iPad, iOS",
      "grading_settings_note": "HWT teaching order vs. ABC order, capitals/lowercase/numbers selection",
      "grading_levers_text": "Cueing level (verbal coaching on/off), letter sequence order"}),
    ("STABILO EASYgraph pencil", PHYSICAL, ["fine"],
     ["Grasp stage support (static/dynamic tripod)", "Pencil pressure regulation"],
     (60, None), ONE_TIME, None,
     {"sensory_profile": "Standard pencil weight/texture, triangular grip shape",
      "grading_levers_text": "Tool size/grip (built-in ergonomic grip moulds)"}),
    ("Roll-A-Dough Letters (Learning Without Tears)", PHYSICAL, ["fine"],
     ["Hand/finger strength", "Letter formation", "Motor planning"],
     (36, 72), ONE_TIME, None,
     {"sensory_profile": "Standard therapy dough texture — check specific product for scent/texture before use with texture-sensitive children",
      "example_functional_play_framings": 'Roll, pinch, and press dough "snakes" into letter shapes — pairs well with any interest theme (e.g. building letter-shaped roads for toy cars)',
      "grading_levers_text": "Resistance (dough firmness), letter complexity"}),
    ("Therapy putty, medium resistance", PHYSICAL, ["fine"],
     ["Hand/grip strength", "Bilateral coordination"],
     (36, None), ONE_TIME, None,
     {"sensory_profile": "Smooth, non-sticky, minimal scent — generally well tolerated by texture-sensitive children",
      "grading_levers_text": "Resistance (soft <-> firm), movement scale"}),
    ("Child-safe tweezers or large clothespins", HOUSEHOLD, ["fine"],
     ["Pincer grasp", "Isolated finger movement", "In-hand manipulation precursor"],
     (36, None), ONE_TIME, None,
     {"grading_levers_text": "Object size (larger = easier), tool type (clothespin = more resistance than tweezers)"}),
    ("Wooden lacing/threading beads", PHYSICAL, ["fine"],
     ["Bilateral coordination", "In-hand manipulation", "Visual-motor integration"],
     (36, None), ONE_TIME, None,
     {"grading_levers_text": "Bead hole size, lace stiffness, pattern complexity"}),
    ("Melissa & Doug Basic Skills Board", PHYSICAL, ["fine", "dressing"],
     ["Bilateral coordination", "Pincer grasp", "In-hand manipulation (via button panel)"],
     (36, None), ONE_TIME, 30,
     {"sensory_profile": "Wooden, smooth pieces — no notable sensory concerns",
      "grading_levers_text": "Fastener type, isolated practice before real fabric"}),
    ("Slant board (or a 3-ring binder as a low-cost substitute)", PHYSICAL, ["fine"],
     ["Wrist positioning", "Postural support for writing"],
     (48, None), FREE, None,
     {"grading_levers_text": "Incline angle, surface size"}),

    # --- Batch 2: Fine motor, printable ---
    ("Pre-writing shape tracing worksheet set", PRINTABLE, ["fine"],
     ["Pre-writing shape mastery"], (30, 60), FREE, None,
     {"grading_levers_text": "Visual support (full guide vs. faded dots vs. blank), shape complexity"}),
    ("Numbered stroke-order letter tracing sheets", PRINTABLE, ["fine"],
     ["Letter formation", "Motor planning sequencing"], (48, 72), FREE, None,
     {"grading_levers_text": "Guide fade level, letter set size"}),
    ("Pencil-control mazes (graded path width)", PRINTABLE, ["fine"],
     ["Visual-motor integration", "Pencil control", "Sustained attention to a fine motor task"],
     (48, 84), FREE, None,
     {"grading_levers_text": "Path width (wide = easier, narrow = harder), maze length"}),
    ("Scissor skills cutting strips (straight/wavy/zigzag/shapes)", PRINTABLE, ["fine"],
     ["Bilateral coordination", "Hand strength"], (36, 72), FREE, None,
     {"safety_flags": "Scissor supervision required per standard classroom/clinic safety practice",
      "grading_levers_text": "Line complexity (straight -> wavy -> zigzag -> shapes), paper stock weight"}),
    ("Personalized name-tracing sheet", PRINTABLE, ["fine"],
     ["Letter formation", "Name recognition"], (36, 72), FREE, None,
     {"grading_levers_text": "Guide visibility, letter size"}),
    ("Letter formation directionality arrow sheets", PRINTABLE, ["fine"],
     ["Motor planning", "Correct stroke sequencing"], (48, 72), FREE, None,
     {"grading_levers_text": "Number of directional arrow cues shown vs. faded"}),
    ("Printable playdough letter mats", PRINTABLE, ["fine"],
     ["Hand strength", "Letter formation", "Motor planning"], (36, 72), FREE, None,
     {"sensory_profile": "Depends on dough used — check family's tolerance before selecting a specific brand/texture",
      "grading_levers_text": "Letter complexity, dough resistance (via whichever dough is used)"}),
    ("Highlighted/raised-line handwriting paper", PRINTABLE, ["fine"],
     ["Letter sizing and baseline awareness"], (60, 96), FREE, None,
     {"grading_levers_text": "Line highlighting intensity, spacing width"}),
    ("Sticker fill-in-the-line precision sheets", PRINTABLE, ["fine"],
     ["Pincer grasp precision", "Visual-motor accuracy"], (36, 60), FREE, None,
     {"grading_levers_text": "Target size (larger dots = easier), pattern density"}),
    ('"Find and trace" hidden picture / visual perception worksheets', PRINTABLE, ["fine", "visual"],
     ["Visual scanning", "Sustained visual attention paired with pencil control"],
     (48, 84), FREE, None,
     {"grading_levers_text": "Image complexity/busyness, number of targets to find"}),

    # --- Batch 3: Self-care / Dressing ---
    ("DIY fabric button-practice board", HOUSEHOLD, ["dressing"],
     ["Buttoning motor plan", "Visual-spatial alignment"], (36, None), FREE, None,
     {"grading_levers_text": "Button size (progressively smaller buttons), fabric stiffness"}),
    ("Family's own elastic-waist clothing", HOUSEHOLD, ["dressing"],
     ["Balance during standing dressing", "Pull-up/down motor pattern"], (24, None), FREE, None,
     {"grading_levers_text": "Garment choice (isolates balance/motor demand from fastener complexity)"}),
    ("Zipper pull loop (keyring or ribbon on an existing zipper tab)", HOUSEHOLD, ["dressing"],
     ["Pincer grasp precision", "Grip on a small fastener tab"], (36, None), FREE, None,
     {"grading_levers_text": "Loop size (larger = easier grip), fade to standard tab once mastered"}),
    ("Printable visual dressing sequence cards", PRINTABLE, ["dressing"],
     ["Sequencing memory", "Independent initiation of multi-step routine"], (36, 84), FREE, None,
     {"grading_levers_text": "Number of steps shown (full sequence vs. faded)"}),
    ("Front/back orientation marker (fabric tag or iron-on label)", HOUSEHOLD, ["dressing"],
     ["Visual perception (orientation/matching)"], (36, None), FREE, None,
     {"grading_levers_text": "Marker prominence (bold/large -> fades smaller/subtler)"}),
    ("Dressing practice on a doll or stuffed toy with fastened clothing", HOUSEHOLD, ["dressing"],
     ["Motor planning and fastener practice in a lower-stakes context"], (30, 60), FREE, None,
     {"grading_levers_text": "Fastener type on the doll's clothing (buttons, zips, snaps)"}),
    ("Visual countdown timer", PRINTABLE, ["dressing"],
     ["Transition tolerance", "Predictability support"], (30, None), FREE, None,
     {"grading_levers_text": "Countdown length, visual vs. physical (sand timer) format"}),
    ("DIY cardboard lacing cards", HOUSEHOLD, ["dressing"],
     ["Bilateral coordination", "Precursor skill to shoe-tying"], (36, None), FREE, None,
     {"grading_levers_text": "Hole spacing (wider = easier), lace stiffness"}),
    ("Personalized printable visual dressing schedule", PRINTABLE, ["dressing"],
     ["Predictability/transition support", "Self-initiation"], (30, None), FREE, None,
     {"grading_levers_text": "Number of steps included, level of detail per picture card"}),
    ("Iron-on velcro fastener strips (temporary garment modification)", HOUSEHOLD, ["dressing"],
     ["Fastener independence via environmental modification"], (36, None), ONE_TIME, None,
     {"grading_levers_text": "Grade-down option — velcro over an existing button/zip temporarily, remove once ready to progress"}),

    # --- Batch 4: Self-care / Grooming ---
    ("Dr. Bob's Unflavored Toothpaste (or Jack N' Jill fluoride-free)", PHYSICAL, ["grooming"],
     ["Oral-sensory tolerance"], (24, None), ONE_TIME, 10,
     {"grading_levers_text": "Flavor intensity (unflavored -> mild fruit -> standard mint, as tolerance builds)"}),
    ("Soft silicone finger toothbrush", PHYSICAL, ["grooming"],
     ["Oral-sensory tolerance"], (12, None), ONE_TIME, None,
     {"grading_levers_text": "Entry point on the oral desensitization hierarchy — softer/more predictable than bristles"}),
    ("Clean silicone teether or popsicle stick (\"oral-motor wand\")", HOUSEHOLD, ["grooming"],
     ["Oral-sensory desensitization", "General oral tolerance building"], (24, None), FREE, None,
     {"grading_levers_text": "Texture (smooth vs. slightly textured), duration of use"}),
    ("Sand timer (2-minute)", PHYSICAL, ["grooming"],
     ["Pacing/duration support for toothbrushing"], (36, None), ONE_TIME, None,
     {"grading_levers_text": "Visual vs. auditory timer preference, duration"}),
    ("Printable hand-washing step sequence poster", PRINTABLE, ["grooming"],
     ["Sequencing memory for a multi-step routine"], (30, 72), FREE, None,
     {"grading_levers_text": "Number of steps shown, picture vs. picture+text"}),
    ("DIY leave-in detangling spray (water + conditioner)", HOUSEHOLD, ["grooming"],
     ["Reduces tactile/pain triggers during hair brushing"], (24, None), FREE, None,
     {"grading_levers_text": "Conditioner concentration, spray amount"}),
    ("Wide-tooth comb", PHYSICAL, ["grooming"],
     ["Reduces pulling/pain sensation during hair brushing"], (24, None), ONE_TIME, None,
     {"grading_levers_text": "Tooth spacing (wider = gentler)"}),
    ("Personalized printable visual grooming routine checklist", PRINTABLE, ["grooming"],
     ["Predictability/transition support", "Self-initiation"], (36, None), FREE, None,
     {"grading_levers_text": "Number of steps included, level of picture detail"}),
    ("Handheld mirror", HOUSEHOLD, ["grooming"],
     ["Visual feedback and motivation during grooming tasks"], (24, None), FREE, None,
     {"example_functional_play_framings": 'Used as the "unicorn shine" payoff moment in the grooming worked example — checking progress in the mirror as a natural reward'}),
    ("Printable 4-quadrant mouth map", PRINTABLE, ["grooming"],
     ["Systematic spatial coverage of all tooth surfaces"], (48, None), FREE, None,
     {"grading_levers_text": "Number of quadrants (start with 2 before left/right distinction)"}),

    # --- Batch 5: Self-care / Feeding ---
    ("Built-up spoon handle (foam pipe insulation wrap, or purpose-made)", HOUSEHOLD, ["feeding"],
     ["Grip control", "Utensil motor control"], (24, None), FREE, None,
     {"grading_levers_text": "Handle diameter (thicker = easier grip)"}),
    ("Non-slip placemat or suction bowl", PHYSICAL, ["feeding"],
     ["Removes bowl-sliding as a variable so practice targets utensil control"], (12, None), ONE_TIME, None, {}),
    ("ARK Therapeutic Bite Tube, Standard/softest level", PHYSICAL, ["feeding"],
     ["Oral motor strength/stability", "Safe chew practice"], (36, None), ONE_TIME, 12,
     {"safety_flags": "Standard chew-tool supervision guidance applies; not a substitute for addressing any actual swallowing safety concern",
      "grading_levers_text": "Firmness level (Standard -> XT -> XXT as jaw strength builds)"}),
    ("Divided plate", PHYSICAL, ["feeding"],
     ["Supports texture-averse eaters by separating foods/textures"], (12, None), ONE_TIME, None,
     {"grading_levers_text": "Number of compartments"}),
    ("Printable food texture ladder / food chaining visual chart", PRINTABLE, ["feeding"],
     ["Structures gradual texture exposure"], (24, None), FREE, None,
     {"grading_levers_text": "Number of rungs, step size between textures"}),
    ("Preferred smooth-food suggestion reference sheet", PRINTABLE, ["feeding"],
     ["Supports clinician-selects-from-options pattern"], (12, None), FREE, None, {}),
    ("DIY dry-filler scooping practice tray (rice/dry cereal + containers)", HOUSEHOLD, ["feeding"],
     ["Scooping motor pattern practiced outside the eating context"], (24, None), FREE, None,
     {"grading_levers_text": "Filler material size, container size/distance"}),
    ("Printable mealtime visual schedule", PRINTABLE, ["feeding"],
     ["Predictability/transition support around mealtimes"], (24, None), FREE, None,
     {"grading_levers_text": "Number of steps shown"}),
    ("Mini condiment/dixie cups for single-bite food exploration", HOUSEHOLD, ["feeding"],
     ["Low-pressure exposure to new foods in small quantities"], (12, None), FREE, None,
     {"grading_levers_text": "Portion size, number of cups/foods offered at once"}),
    ("Textured spoon (silicone-tipped, or DIY texture wrap)", PHYSICAL, ["feeding"],
     ["Additional sensory/tactile feedback during grip"], (12, None), FREE, None,
     {"grading_levers_text": "Texture intensity"}),

    # --- Batch 6: Self-care / Toileting ---
    ("Printable toileting routine visual sequence cards", PRINTABLE, ["toileting"],
     ["Sequencing memory", "Predictability support"], (30, 72), FREE, None,
     {"grading_levers_text": "Number of steps shown"}),
    ("Sticker reward chart", PRINTABLE, ["toileting"],
     ["Positive reinforcement for attempts/successes"], (30, None), FREE, None,
     {"grading_levers_text": "Reward frequency (every attempt vs. milestone-based)"}),
    ("Step stool", PHYSICAL, ["toileting"],
     ["Postural stability and secure footing while seated"], (24, None), ONE_TIME, None,
     {"grading_levers_text": "Height adjustment if available"}),
    ("Toilet seat reducer/insert (confirmed stable, non-wobbly)", PHYSICAL, ["toileting"],
     ["Secure positioning"], (24, None), ONE_TIME, None,
     {"safety_flags": "Stability must be explicitly checked before use — a single unstable seat experience can create lasting avoidance; this is a specific, demonstrated risk in this resource category, not a generic caution."}),
    ("Printable graded exposure ladder tracking sheet", PRINTABLE, ["toileting"],
     ["Cross-session progress tracking for avoidance-based toileting goals"], (None, None), FREE, None, {}),
    ("Basic kitchen timer", PHYSICAL, ["toileting"],
     ["Supports scheduled toilet-sit routines (habit training)"], (None, None), ONE_TIME, None,
     {"grading_levers_text": "Interval length"}),
    ("A book or toy reserved only for toilet time", HOUSEHOLD, ["toileting"],
     ["Novelty-based motivation to support willingness to sit"], (24, None), FREE, None, {}),
    ("Printable interoception body-signal check-in visual scale", PRINTABLE, ["toileting"],
     ["Interoceptive awareness"], (36, None), FREE, None,
     {"grading_levers_text": "Number of signal options shown, picture vs. text-based"}),
    ("Simple privacy visual barrier or door sign", HOUSEHOLD, ["toileting"],
     ["Reduces sensory/social input for children needing more privacy"], (36, None), FREE, None, {}),
    ("Bubble timer or liquid motion timer", PHYSICAL, ["toileting"],
     ["Visual wait-time support during elimination"], (30, None), ONE_TIME, None,
     {"grading_levers_text": "Timer duration (different lengths available)"}),

    # --- Batch 7: Gross motor ---
    ("Painter's tape balance path", HOUSEHOLD, ["gross"],
     ["Static/dynamic balance", "Motor planning"], (36, None), FREE, None,
     {"grading_levers_text": "Path width (wider = easier), straight vs. curved/zigzag, surface"}),
    ("Pillow/cushion obstacle course", HOUSEHOLD, ["gross"],
     ["Balance", "Motor planning", "Strength/endurance"], (30, None), FREE, None,
     {"grading_levers_text": "Obstacle height/instability, course length, added time challenge"}),
    ("Bean bags (DIY rice-filled socks, or low-cost store-bought)", HOUSEHOLD, ["gross"],
     ["Throwing/catching coordination", "Proprioceptive awareness"], (36, None), FREE, None,
     {"grading_levers_text": "Bag weight, target distance, target size"}),
    ("Sidewalk chalk hopscotch grid", PHYSICAL, ["gross"],
     ["Single-leg balance", "Jumping", "Motor planning/sequencing"], (48, None), ONE_TIME, None,
     {"grading_levers_text": "Grid complexity, square size, distance between squares"}),
    ("Printable animal walk cards", PRINTABLE, ["gross"],
     ["Bilateral coordination", "Strength", "Motor planning"], (30, None), FREE, None,
     {"grading_levers_text": "Number of cards/sequence length, movement pattern complexity"}),
    ("Jump rope", PHYSICAL, ["gross"],
     ["Bilateral coordination", "Timing", "Strength/endurance"], (60, None), ONE_TIME, None,
     {"grading_levers_text": "Rope length/speed, jumping alone vs. adult-turned rope"}),
    ("Balloon volleyball", HOUSEHOLD, ["gross"],
     ["Visual tracking paired with gross motor timing", "Reactive coordination"], (36, None), FREE, None,
     {"grading_levers_text": 'Balloon size, "net" height (string/tape line), distance between players'}),
    ("Wheelbarrow walk (no equipment)", HOUSEHOLD, ["gross"],
     ["Core/shoulder girdle strength", "Postural control"], (36, None), FREE, None,
     {"grading_levers_text": "Distance, level of support (hips vs. ankles), surface"}),
    ("Carpet squares or paper plates as a stepping-stone path", HOUSEHOLD, ["gross"],
     ["Dynamic balance", "Motor planning"], (36, None), FREE, None,
     {"grading_levers_text": 'Spacing between "stones," stone size, path complexity'}),
    ("Large therapy/exercise ball", PHYSICAL, ["gross"],
     ["Core stability", "Balance", "Vestibular/proprioceptive input"], (36, None), ONE_TIME, 20,
     {"safety_flags": "Adult supervision required — standard practice for any therapy ball use with young children",
      "grading_levers_text": "Ball size relative to child, seated vs. prone/supine positioning, level of support"}),

    # --- Batch 8: Sensory regulation ---
    ("DIY weighted lap pad (rice or dried bean-filled fabric pouch)", HOUSEHOLD, ["sensory"],
     ["Proprioceptive input for regulation"], (36, None), FREE, None,
     {"safety_flags": "Weight should be appropriate to child's size — roughly 5-10% of body weight; check current recommendations before finalizing",
      "grading_levers_text": "Weight, size, duration of use"}),
    ("Noise-reducing ear defenders", PHYSICAL, ["sensory"],
     ["Auditory sensory modulation"], (24, None), ONE_TIME, 22,
     {"grading_levers_text": "Degree of noise reduction, duration of use, self-directed on/off"}),
    ("Simple fidget tool (squeeze ball or textured fidget)", PHYSICAL, ["sensory"],
     ["Tactile/proprioceptive self-regulation", "Sustained attention support"], (36, None), ONE_TIME, None,
     {"grading_levers_text": "Resistance/texture intensity, size"}),
    ("Printable arousal/energy scale", PRINTABLE, ["sensory"],
     ["Arousal state awareness", "Interoception"], (36, None), FREE, None,
     {"grading_levers_text": "Number of scale points, picture-only vs. picture+text"}),
    ("Chewable pencil topper or simple chew tool", PHYSICAL, ["sensory"],
     ["Oral-proprioceptive self-regulation"], (48, None), ONE_TIME, None,
     {"safety_flags": "Standard chew-tool supervision guidance applies",
      "grading_levers_text": "Firmness/resistance level"}),
    ("Sand timer or basic kitchen timer", PHYSICAL, ["sensory"],
     ["Supports scheduled/timed regulation breaks"], (30, None), ONE_TIME, None,
     {"grading_levers_text": "Duration, visual vs. auditory alert"}),
    ("DIY sensory bottle (glitter and water in a sealed bottle)", HOUSEHOLD, ["sensory"],
     ["Visual calming input"], (24, None), FREE, None,
     {"grading_levers_text": "Glitter density/movement speed, bottle size"}),
    ("Printable regulation strategy choice board", PRINTABLE, ["sensory"],
     ["Strategy knowledge", "Self-initiation via structured choice"], (36, None), FREE, None,
     {"grading_levers_text": "Number of options shown"}),
    ('Blanket "calm cave" or small pop-up tent', HOUSEHOLD, ["sensory"],
     ["Environmental modification — reduced visual/auditory input"], (24, None), FREE, None,
     {"grading_levers_text": "Enclosure size, lighting inside"}),
    ("Weighted plush toy", PHYSICAL, ["sensory"],
     ["Proprioceptive/calming input"], (24, None), ONE_TIME, 20, {"grading_levers_text": "Weight, size"}),

    # --- Batch 9: Visual perception ---
    ('Printable "spot the difference" worksheets', PRINTABLE, ["visual"],
     ["Visual discrimination", "Visual memory"], (48, None), FREE, None,
     {"grading_levers_text": "Number of differences, image complexity",
      "cross_discipline_note": "Not appropriate as-is for CVI or similar diagnosis-specific visual presentations — use the CVI proforma's principles instead."}),
    ("Simple inset puzzles (4-6 piece)", PHYSICAL, ["visual"],
     ["Visual-spatial relationships", "Form constancy"], (24, 36), ONE_TIME, 7,
     {"grading_levers_text": "Piece count, image complexity"}),
    ("Memory/matching card game", PHYSICAL, ["visual"],
     ["Visual memory", "Visual discrimination"], (48, None), ONE_TIME, 7,
     {"grading_levers_text": "Number of card pairs in play, image similarity between pairs"}),
    ('Printable "find and circle" figure-ground worksheets', PRINTABLE, ["visual"],
     ["Figure-ground discrimination"], (48, 84), FREE, None,
     {"grading_levers_text": "Field complexity, number/similarity of distractors"}),
    ("Building blocks with pattern/design cards", PHYSICAL, ["visual"],
     ["Visual-spatial relationships", "Visual-motor integration", "2D-to-3D copying"], (48, None), ONE_TIME, 15,
     {"grading_levers_text": "Pattern complexity, 2D card vs. 3D model to copy"}),
    ('Printable "I Spy" style busy-scene picture', PRINTABLE, ["visual"],
     ["Figure-ground", "Sustained visual scanning"], (48, None), FREE, None,
     {"grading_levers_text": "Scene busyness, target size/count"}),
    ("Wooden shape sorter", PHYSICAL, ["visual"],
     ["Form constancy", "Visual-spatial relationships"], (18, 36), ONE_TIME, 12,
     {"grading_levers_text": "Number of shapes, shape similarity"}),
    ("Printable maze worksheets", PRINTABLE, ["visual"],
     ["Visual-spatial planning", "Sustained visual attention paired with motor control"], (48, 84), FREE, None,
     {"grading_levers_text": "Path width, maze length/complexity"}),
    ("Pegboard with pattern cards", PHYSICAL, ["visual"],
     ["Visual-motor integration", "Form constancy", "Visual-spatial copying"], (36, None), ONE_TIME, 15,
     {"grading_levers_text": "Peg count/pattern complexity"}),
    ("Printable sequencing cards (put pictures in order)", PRINTABLE, ["visual"],
     ["Visual sequential memory"], (48, None), FREE, None,
     {"grading_levers_text": "Number of steps/cards, familiarity of the sequence depicted"}),

    # --- Batch 10: Emotional regulation ---
    ("Printable expanded feelings wheel/chart", PRINTABLE, ["emotional"],
     ["Emotional vocabulary beyond basic categories"], (48, None), FREE, None,
     {"grading_levers_text": "Number of feelings shown, basic vs. blended/nuanced feelings"}),
    ("Emotion matching cards (facial expression photos/illustrations)", PRINTABLE, ["emotional"],
     ["Recognizing emotional expression in self and others"], (36, None), FREE, None,
     {"grading_levers_text": "Number of emotions in play, subtlety of expression shown"}),
    ('Printable "feelings thermometer" scale', PRINTABLE, ["emotional"],
     ["Arousal/intensity awareness for a named feeling"], (48, None), FREE, None,
     {"grading_levers_text": "Number of scale points"}),
    ("Printable calm-down choice board", PRINTABLE, ["emotional"],
     ["Flexible strategy selection"], (36, None), FREE, None,
     {"grading_levers_text": "Number of strategy options shown"}),
    ('"The Way I Feel" by Janan Cain (picture book)', PHYSICAL, ["emotional"],
     ["Emotional vocabulary building through narrative and illustration"], (24, None), ONE_TIME, 12, {}),
    ("Stress ball or squeeze toy", PHYSICAL, ["emotional"],
     ["Physical outlet/coping strategy for building frustration"], (36, None), ONE_TIME, None,
     {"grading_levers_text": "Resistance level"}),
    ('Printable "size of the problem" scale', PRINTABLE, ["emotional"],
     ["Cognitive appraisal — matching reaction size to the actual scale of a problem"], (60, None), FREE, None,
     {"grading_levers_text": "Number of example scenarios provided alongside the scale"}),
    ("Hand mirror", HOUSEHOLD, ["emotional"],
     ["Practicing and recognizing facial expressions of emotion"], (36, None), FREE, None, {}),
    ("Low-stakes turn-based game with a built-in win/lose outcome", PHYSICAL, ["emotional"],
     ["Practicing regulation around winning/losing in a low-investment context"], (48, None), ONE_TIME, 7,
     {"grading_levers_text": "Game length/stakes — pick something the child isn't deeply invested in"}),
    ('Printable "next time" reframe cards', PRINTABLE, ["emotional"],
     ["Cognitive reframing strategy"], (72, None), FREE, None,
     {"grading_levers_text": "Abstractness of the reframe language used"}),

    # --- Batch 11: Play / leisure / social skills ---
    ("Candy Land (or similar simple turn-based board game)", PHYSICAL, ["play"],
     ["Turn-taking", "Rule-following", "Tolerating win/lose outcomes"], (36, None), ONE_TIME, 12,
     {"grading_levers_text": "Game length, number of players"}),
    ("Printable turn-taking token/visual system", PRINTABLE, ["play"],
     ["Turn-taking", "Conversational reciprocity"], (48, None), FREE, None,
     {"grading_levers_text": "Number of turns/steps shown"}),
    ("Dress-up/pretend play box (household clothes, hats, accessories)", HOUSEHOLD, ["play"],
     ["Symbolic/pretend play", "Role play"], (30, None), FREE, None,
     {"grading_levers_text": "Number of props, structured role vs. open-ended play"}),
    ("Printable social story template", PRINTABLE, ["play"],
     ["Social communication", "Preparing for a specific social scenario"], (36, None), FREE, None,
     {"grading_levers_text": "Length/detail, picture-only vs. text-supported"}),
    ("Sock puppets (DIY or low-cost store-bought)", HOUSEHOLD, ["play"],
     ["Symbolic play", "Social communication practice at a lower-stakes remove"], (36, None), FREE, None,
     {"grading_levers_text": "Number of puppets/characters involved"}),
    ("Hoot Owl Hoot (or a similar cooperative board game)", PHYSICAL, ["play"],
     ["Cooperative play — shared goals rather than competition"], (48, None), ONE_TIME, 17,
     {"grading_levers_text": "Game difficulty setting"}),
    ("Printable conversation starter cards", PRINTABLE, ["play"],
     ["Initiating and maintaining social communication"], (60, None), FREE, None,
     {"grading_levers_text": "Question abstractness, familiar vs. novel conversation partner"}),
    ("Building blocks/Lego set", PHYSICAL, ["play", "fine"],
     ["Parallel and cooperative building play"], (36, None), ONE_TIME, 22,
     {"grading_levers_text": "Independent vs. shared/collaborative build, structured vs. open-ended"}),
    ("Printable turn-taking points/badge tracker", PRINTABLE, ["play"],
     ["Reinforces sustained turn-taking practice with a genuine goal state"], (48, None), FREE, None,
     {"grading_levers_text": "Number of points/rounds required"}),
    ("Simple ball for reciprocal rolling/throwing games", PHYSICAL, ["play", "gross"],
     ["Reciprocal play (rolling/throwing back and forth)"], (24, None), ONE_TIME, None,
     {"grading_levers_text": "Ball size, roll vs. throw, distance"}),
]


def split_top_level_commas(text):
    return [seg.strip() for seg in re.split(r",\s*(?![^(]*\))", text) if seg.strip()]


class Command(BaseCommand):
    help = "Seed the Resource library from the Phase 0 resource-library batch docs"

    @transaction.atomic
    def handle(self, *args, **options):
        self.domains = self._get_or_create_domains()

        created_count = 0
        updated_count = 0
        for (name, rtype, domain_keys, sub_skill_names, age_range, cost_type,
             cost_amount, extra) in RESOURCES:
            domains = [self.domains[key] for key in domain_keys]
            primary_domain = domains[0]

            defaults = {
                "resource_type": rtype,
                "cost_type": cost_type,
                "cost_amount": cost_amount,
                "age_min_months": age_range[0],
                "age_max_months": age_range[1],
                "platform": extra.get("platform", ""),
                "grading_settings_note": extra.get("grading_settings_note", ""),
                "safety_flags": extra.get("safety_flags", ""),
                "sensory_profile": extra.get("sensory_profile", ""),
                "example_functional_play_framings": extra.get("example_functional_play_framings", ""),
                "cross_discipline_note": extra.get("cross_discipline_note", ""),
            }
            resource, created = Resource.objects.update_or_create(
                name=name, defaults=defaults,
            )
            resource.domains.set(domains)

            sub_skills = [
                SubSkill.objects.get_or_create(domain=primary_domain, name=n)[0]
                for n in sub_skill_names
            ]
            resource.sub_skills.set(sub_skills)

            grading_levers_text = extra.get("grading_levers_text")
            if grading_levers_text:
                levers = []
                for segment in split_top_level_commas(grading_levers_text):
                    lever_name = segment.split("(", 1)[0].strip()
                    note = f"From resource tagging (not yet split into up/down): {segment}"
                    lever, _ = GradingLever.objects.get_or_create(
                        domain=primary_domain, name=lever_name,
                        defaults={"grade_down_description": note, "grade_up_description": note},
                    )
                    levers.append(lever)
                resource.grading_levers.set(levers)

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Resources: {created_count} created, {updated_count} updated "
            f"({created_count + updated_count} total)."
        ))

    def _get_or_create_domains(self):
        domains = {}
        top_level_keys = ["fine", "self_care", "gross", "sensory", "visual", "emotional", "play"]
        for key in top_level_keys:
            slug = DOMAIN_SLUGS[key]
            domain, _ = Domain.objects.get_or_create(
                slug=slug, defaults={"name": DOMAIN_NAMES[key]}
            )
            domains[key] = domain

        self_care = domains["self_care"]
        for key in SELF_CARE_SUBDOMAINS:
            slug = DOMAIN_SLUGS[key]
            domain, _ = Domain.objects.get_or_create(
                slug=slug,
                defaults={"name": DOMAIN_NAMES[key], "parent_domain": self_care},
            )
            if domain.parent_domain_id != self_care.id:
                domain.parent_domain = self_care
                domain.save(update_fields=["parent_domain"])
            domains[key] = domain

        return domains

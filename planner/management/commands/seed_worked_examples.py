"""
Seeds the 19 Phase 0 worked examples (9 synthetic, 10 real/de-identified)
and the 1 home-program worked example, from
~/Documents/Phase 0/Worked examples/*.md.

Unlike seed_resources/seed_proformas (reference/taxonomy data), these are
case records: Child -> Goal -> OptionPoint -> SessionPlan -> ActivityBlock
(-> HomeProgram for the one case that has one). Idempotent per case via a
"case_key" comment convention isn't enforced by a unique DB field (Child
has no natural unique key), so this command clears and re-creates
everything it created on a previous run, tracked by Child.initial_or_name
(unique enough within this seed set, even though the model itself doesn't
require it).

Known gaps / judgment calls, flagged rather than hidden:
- real-client-2 (spelling/word-spacing) never states the child's age
  anywhere in the source file. Seeded with age_years=7 as an explicit
  placeholder -- confirm and correct against the real record.
- Child.Environment has no "childcare" option; real-client-9
  (childcare transition meltdowns) is seeded as SCHOOL, the closest
  available choice.
- Several rich narrative sections in the source docs have no matching
  model field and are intentionally dropped rather than force-fit:
  "Flag for your review" questions (Phase-0-review artifacts, not case
  data), standalone scope-of-practice notes, and cross-session tracking
  notes. Each case's core clinical content -- presentation, component
  gap, goals, option points, and every activity block's reasoning and
  grading -- is preserved.
- ActivityBlock.resources is only linked where a block names a resource
  that's an exact/near-exact match to something already in the seeded
  Resource library (e.g. "Melissa & Doug Basic Skills Board"). Most
  activity items are one-off improvised materials (a "toy robot," "a
  block tower") that were never meant to be catalog resources, so most
  blocks correctly have none linked.
- A "Visual rest break" in the CVI case is filed as MOVEMENT_RESET
  (the closest existing BlockType) even though it's a visual, not
  physical, rest -- the model has no dedicated visual-break type.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from planner.models import (
    ActivityBlock,
    Child,
    Domain,
    Goal,
    HomeProgram,
    Interest,
    OptionPoint,
    Proforma,
    Resource,
    SessionPlan,
)


DOMAIN_SLUGS = {
    "fine": "fine-motor-handwriting",
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

WARM_UP, MAIN, MOVEMENT_RESET, WARM_DOWN = "warm_up", "main", "movement_reset", "warm_down"

# Exact/near-exact resource-name aliases -> the seeded Resource.name.
RESOURCE_ALIASES = {
    "Therapy putty": "Therapy putty, medium resistance",
    "Melissa & Doug Basic Skills Board": "Melissa & Doug Basic Skills Board",
    "Child-safe tweezers or large clothespins": "Child-safe tweezers or large clothespins",
    "Large clothespins or child-safe tweezers": "Child-safe tweezers or large clothespins",
    "Noise-cancelling headphones": "Noise-reducing ear defenders",
    "Weighted lap pad": "DIY weighted lap pad (rice or dried bean-filled fabric pouch)",
    "Gravity pad (weighted lap pad)": "DIY weighted lap pad (rice or dried bean-filled fabric pouch)",
    "Handheld mirror": "Handheld mirror",
    "Small hand mirror": "Handheld mirror",
    "Writing Wizard app": "Writing Wizard (app)",
    "Writing Wizard (iPad)": "Writing Wizard (app)",
    "iTrace": "iTrace (app)",
}


CASES = [
    # 1 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "R. (synthetic, fine motor)",
            "age_years": 5, "age_months": 6,
            "default_environment": "clinic",
            "interests": ["Dinosaurs", "Superheroes"],
            "proformas": [],
            "current_presentation": (
                "Grasp: static tripod (not yet dynamic). Pre-writing shapes mastered "
                "through square; inconsistent with triangle and X. Fatigues after ~5 "
                "minutes of tabletop fine motor work. Reduced hand/grip strength on "
                "informal handling. Mild tactile sensitivity — avoids grainy/sticky "
                "textures (e.g. textured playdough), tolerates smooth textures fine.\n\n"
                "Component gap identified: static tripod with mastery through "
                "square-level shapes suggests the limiting factor isn't shape-copying "
                "or visual-motor integration broadly — it's isolated finger movement "
                "(in-hand manipulation), the component skill separating static from "
                "dynamic tripod grasp. Fatigue after 5 minutes also flags hand/grip "
                "endurance as a secondary factor to manage across the session."
            ),
        },
        "goal": {
            "domain": "fine",
            "raw_goal_text": "Copy his name using a dynamic tripod grasp with legible letter formation.",
            "interim_goal_text": "",
            "outcome_goal_text": (
                "By [date], R. will copy his name (5 letters) using a dynamic tripod "
                "grasp with legible letter formation, independently, in 4/5 trials."
            ),
        },
        "option_point": None,
        "session_plan": {"session_length_minutes": 30, "environment": "clinic"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Dino stomp and squeeze",
                "activity_description": (
                    "Heavy-work animal walks (dinosaur stomps, bear crawls) from the "
                    "door to the table, ending with bilateral squeezing of "
                    "dinosaur-egg-shaped therapy putty (5-6 squeezes each hand)."
                ),
                "clinical_reasoning": (
                    "Proprioceptive/heavy work input first supports regulation and "
                    "sensory-motor readiness before fine motor demand is introduced "
                    "(Pyramid of Learning, base layer). The putty squeeze also "
                    "pre-loads hand/grip strength, addressing the fatigue noted in "
                    "current presentation before it becomes a barrier in the main "
                    "activity."
                ),
                "resources": ["Therapy putty"],
                "grade_up_note": "Increase putty resistance (firmer putty); add resistance path (crawling over cushions).",
                "grade_down_note": "Reduce crawl distance; use softer putty; reduce squeeze reps.",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 15,
                "title": "Dino egg rescue",
                "activity_description": (
                    "Small dinosaur counters hidden in a shallow tray of dried rice or "
                    "smooth beans (non-grainy alternative if sensitivity flares: dry "
                    "pasta shapes). R. searches with a whole-hand raking/digging motion "
                    "to locate dinosaurs, then picks each one up using thumb, index, "
                    "and middle finger and translates it into the palm to hold "
                    "securely while continuing to search — releasing collected "
                    "dinosaurs into a \"nest\" once several are held in-hand. Recovered "
                    "dinosaurs are then used to build his name using foam letter "
                    "stamps or tracing in a sensory tray."
                ),
                "clinical_reasoning": (
                    "Directly targets finger-to-palm translation — the specific "
                    "in-hand manipulation pattern involved in collecting and securely "
                    "holding several small objects while continuing to use the "
                    "fingertips, a precursor skill to the isolated finger control "
                    "needed for dynamic tripod grasp. The whole-hand search keeps the "
                    "retrieval step functional and natural, isolating the translation "
                    "demand to the pick-up-and-store action. Dinosaur-rescue framing "
                    "keeps engagement high given R.'s documented fatigue/attention "
                    "limit. Embedding name-letter work at the end links the practice "
                    "directly back to the stated goal."
                ),
                "resources": [],
                "grade_up_note": (
                    "Smaller dinosaur pieces; add a time challenge (\"rescue 5 before "
                    "the timer\"); require verbal counting while transferring (adds "
                    "cognitive load); remove the \"nest\" cue and require independent "
                    "sequencing."
                ),
                "grade_down_note": (
                    "Larger, easier-to-grip pieces; reduce to placing one dinosaur "
                    "straight in the nest at a time; practitioner models the "
                    "finger-to-palm translation hand-over-hand first; shorten to 3 "
                    "dinosaurs before moving to letter tracing."
                ),
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 5,
                "title": "Dino carry and roar breathing",
                "activity_description": (
                    "R. carries a weighted dinosaur toy across the room to place it in "
                    "its \"cave\" (box), paired with a slow breath in through the nose "
                    "and a long \"roar\" breath out, repeated 3-4 times."
                ),
                "clinical_reasoning": (
                    "Proprioceptive input (carrying) paired with paced breathing "
                    "supports down-regulation after the fine motor demand of the main "
                    "activity, and provides a calm, predictable close to the session."
                ),
                "resources": [],
                "grade_up_note": "Heavier weighted item; longer carry distance.",
                "grade_down_note": "Lighter item; shorter distance; reduce breath reps.",
            },
        ],
        "home_program": None,
    },
    # 2 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (name recognition/writing)",
            "age_years": 6, "age_months": 0,
            "default_environment": "school",
            "interests": ["Transport vehicles", "Numbers", "Sand", "Blocks (Lego/Duplo)"],
            "proformas": [],
            "current_presentation": (
                "Grasp: dynamic tripod (established). Pre-writing shapes: all "
                "mastered. Endurance: disengages from non-preferred tasks after ~5 "
                "minutes; can hold upright seated posture ~5 minutes before leaning "
                "on table. Attention stronger in mornings than afternoons. Sensory: "
                "seeks visual input; avoids sticky, foam, and wet tactile input. "
                "Writes with better letter formation and stays more motivated on "
                "iPad than paper/pencil.\n\n"
                "Component gap identified: grasp and shape-copying (mechanical "
                "prerequisites) are already in place. Actual barriers: (1) "
                "postural/core endurance — leaning after ~5 min suggests seated "
                "tabletop tolerance, not fine motor skill, is the limiting factor; "
                "(2) sustained attention/motivation — disengagement after ~5 min on "
                "non-preferred tasks means novelty/interest-matching needs building "
                "into session structure itself; (3) transfer from generic "
                "pre-writing shapes to letter-specific sequencing/recognition for "
                "his own name. Sensory-driven hard exclusion: shaving foam, wet "
                "paint, glue, textured/sticky playdough are ruled out entirely given "
                "his documented tactile aversions."
            ),
        },
        "goal": {
            "domain": "fine",
            "raw_goal_text": "Recognise and write his name.",
            "interim_goal_text": "",
            "outcome_goal_text": "Recognise and write his name.",
        },
        "option_point": None,
        "session_plan": {"session_length_minutes": 20, "environment": "school"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Loading the trucks",
                "activity_description": (
                    "Prone-lying on the floor (on elbows/forearms), pushing small toy "
                    "vehicles along the floor to \"deliver\" them to numbered "
                    "drop-off points, counting as he goes."
                ),
                "clinical_reasoning": (
                    "Prone positioning actively loads core and shoulder-girdle "
                    "stability — directly targeting the postural endurance gap — "
                    "before any seated tabletop demand is introduced. Vehicle and "
                    "number framing matches known motivators from the outset."
                ),
                "resources": [],
                "grade_up_note": "Incline surface (wedge) increases postural demand; add a light resistance \"trailer\" to pull.",
                "grade_down_note": "Reduce distance/duration; allow forearm support on a raised surface instead of full prone.",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 5,
                "title": "iPad name tracing",
                "activity_description": (
                    "Writing Wizard app (iPad), with his name entered as a custom "
                    "word to trace, finger or stylus, starting with full trace guides "
                    "visible."
                ),
                "clinical_reasoning": (
                    "The goal's actual new demand — letter-specific sequencing and "
                    "recognition — is best introduced through the modality with his "
                    "strongest documented engagement and performance. Placing this "
                    "block first captures peak attention for the most cognitively "
                    "demanding part of the task, and the screen-based, non-tactile "
                    "format sidesteps his sensory aversions entirely."
                ),
                "resources": ["Writing Wizard app"],
                "grade_up_note": (
                    "Turn off trace guide lines (in-app setting); switch to \"5-star\" "
                    "mode requiring 5 correct traces per letter; add a letter-scramble "
                    "task where he selects the correct letter order before tracing."
                ),
                "grade_down_note": (
                    "Keep trace guides on; increase letter size (in-app setting); "
                    "switch to free-play mode; reduce to first 2-3 letters only."
                ),
            },
            {
                "block_type": MOVEMENT_RESET, "order": 3, "duration_minutes": 2,
                "title": "Delivery run",
                "activity_description": "Walk/drive like a truck to a cone across the room and back.",
                "clinical_reasoning": (
                    "A brief, novel, interest-matched movement break before "
                    "attention/endurance fully depletes, resetting both postural "
                    "fatigue and attention for the second main block."
                ),
                "resources": [],
                "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 4, "duration_minutes": 5,
                "title": "Sand delivery route",
                "activity_description": (
                    "Writing/tracing his name in a shallow tray of dry sand, either "
                    "with a finger or by driving a small toy vehicle through the sand "
                    "to trace each letter shape, name card available for visual "
                    "reference."
                ),
                "clinical_reasoning": (
                    "Following digital practice with tactile-motor rehearsal in a "
                    "different sensory channel supports generalising letter-formation "
                    "practice beyond the screen — critically, dry (not wet, not "
                    "sticky) sand respects his sensory aversions, and driving a "
                    "vehicle through the sand embeds his transport interest directly "
                    "into the motor task."
                ),
                "resources": [],
                "grade_up_note": (
                    "Remove the name card (recall-based writing instead of copying); "
                    "use finger only for more precise motor demand; add distractor "
                    "letters nearby for him to select the correct ones from."
                ),
                "grade_down_note": (
                    "Keep name card visible; use vehicle-assisted tracing (grosser "
                    "motor demand, more forgiving); increase letter size in the sand."
                ),
            },
            {
                "block_type": WARM_DOWN, "order": 5, "duration_minutes": 3,
                "title": "Build his name",
                "activity_description": (
                    "Using Lego/Duplo blocks to build or match the first letter (or "
                    "full name, if time/engagement allows) from a reference card."
                ),
                "clinical_reasoning": (
                    "By this point endurance is likely near its documented limit — "
                    "closing with a low-physical-demand, high-preference activity "
                    "that still connects to the goal maintains a positive association "
                    "with the session's end."
                ),
                "resources": [],
                "grade_up_note": "Build the full name, not just the first letter; remove the reference card.",
                "grade_down_note": "Free-build with blocks as pure regulation/positive closure, no letter-matching demand.",
            },
        ],
        "home_program": None,
    },
    # 3 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (spelling / word spacing)",
            "age_years": 7, "age_months": 0,
            "default_environment": "school",
            "interests": ["Meerkats", "Ice hockey", "Pokemon", "Movement-based activities"],
            "proformas": ["Autism", "ADHD"],
            "current_presentation": (
                "AGE NOT DOCUMENTED IN SOURCE — placeholder estimate (7;0), confirm "
                "and correct against the real record.\n\n"
                "Grasp: dynamic tripod (established). Pre-writing shapes: all "
                "mastered. Endurance/strength appropriate to sustain attention and "
                "task. Diagnoses: ASD, ADHD. Uses chewellery for regulation (in "
                "active use). Difficulties: spelling accuracy, retaining what she's "
                "read, spacing between words.\n\n"
                "Component gap identified: motor mechanics (grasp, pre-writing "
                "shapes) and physical endurance are fully established — not a "
                "motor-readiness case. Actual gaps: (1) visual-spatial planning for "
                "word spacing in written output, and (2) motor/sensory "
                "reinforcement to support encoding memory for spelling. Layered on "
                "top: endurance and willing participation are not reliable "
                "indicators of regulation for this child, given documented masking."
            ),
            "masking_note": (
                "Participates in tasks regardless of how boring she finds them "
                "(masking); experiences shutdown at home after school from a full "
                "day of masking. Regulation checkpoints must be built into session "
                "structure as fixed transitions rather than offered conditionally, "
                "since she's unlikely to ask for one herself."
            ),
        },
        "goal": {
            "domain": "fine",
            "raw_goal_text": "Sound out words and spell them accurately.",
            "interim_goal_text": "",
            "outcome_goal_text": (
                "Word spacing and multisensory motor input to support letter-sound "
                "encoding memory (the OT-scoped pieces of the spelling goal — "
                "phonemic decoding itself is SLP/literacy-teacher territory)."
            ),
        },
        "option_point": None,
        "session_plan": {"session_length_minutes": 20, "environment": "school"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Meerkat lookout relay",
                "activity_description": (
                    "Movement-based relay between stations (hop, run, or animal-walk "
                    "between markers). At each station, she flips a letter/sound card "
                    "and says the sound aloud before moving to the next station."
                ),
                "clinical_reasoning": (
                    "Combines proactive movement-based regulation with auditory-motor "
                    "phoneme retrieval, priming the letter-sound pathway ahead of the "
                    "spelling task. Given her documented tendency to mask and "
                    "participate regardless of internal state, this warm-up is "
                    "regulation-forward by design rather than reactive."
                ),
                "resources": [],
                "grade_up_note": "More stations; add a memory component (recall the previous 2 sounds before saying the new one).",
                "grade_down_note": "Fewer stations; reduce to single-sound recall only, no sequencing demand.",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 14,
                "title": "Pokemon word builder",
                "activity_description": (
                    "Part A (5-7 min, multisensory encoding): using a short list of "
                    "target words (ideally from her current spelling program), she "
                    "sky-writes each word in large arm movements while saying each "
                    "sound aloud. Part B (7-8 min, word spacing with a spacer tool): "
                    "transfers the same words to paper, using a small physical spacer "
                    "(e.g. an ice-hockey-puck-shaped or meerkat-shaped popsicle "
                    "stick) placed after each word before starting the next. A brief, "
                    "non-optional pause is built in between Part A and Part B, framed "
                    "as a fixed structural transition (\"let's stretch before round "
                    "two\") rather than \"do you need a break\"."
                ),
                "clinical_reasoning": (
                    "Part A uses large-movement, multisensory input to reinforce "
                    "letter-sound correspondence through a motor/kinesthetic channel "
                    "without positioning OT as teaching phonics content itself. Part "
                    "B directly targets word-spacing with an explicit physical "
                    "strategy rather than an abstract instruction like \"leave a "
                    "space\" — concrete, external cues are typically more reliable "
                    "under attention/executive-function load. The built-in "
                    "checkpoint gives a regulation opportunity regardless of whether "
                    "she'd ask for one."
                ),
                "resources": [],
                "grade_up_note": (
                    "Longer/more complex words; fade the spacer tool to a "
                    "finger-space instead of the physical object; add a self-check "
                    "step (re-read own writing for spacing errors)."
                ),
                "grade_down_note": (
                    "Shorter word list; reduce sky-writing to just the first letter "
                    "of each word; keep spacer tool as a constant physical placement "
                    "rather than fading it."
                ),
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 4,
                "title": "Pokemon catch and breathe",
                "activity_description": (
                    "Gentle catch/throw with a soft ball (ice hockey-adjacent, lower "
                    "intensity), paired with a simple breath in-out on each catch. "
                    "Close with a quick non-verbal check — pointing to a 1-5 energy "
                    "scale rather than asking \"how are you feeling?\" directly."
                ),
                "clinical_reasoning": (
                    "Lower-intensity movement supports transition and regulation "
                    "before she returns to class and eventually goes home, where "
                    "shutdown after masking is a known pattern. The indirect, "
                    "non-verbal check is used deliberately since a masking child is "
                    "more likely to give an accurate answer through an indirect, "
                    "low-demand format than a direct question she may feel pressure "
                    "to answer \"correctly.\""
                ),
                "resources": [],
                "grade_up_note": "N/A — this block is deliberately kept low-demand regardless of session performance elsewhere.",
                "grade_down_note": "Skip the ball entirely, move straight to breathing and the check-in if she's showing signs of fatigue by this point.",
            },
        ],
        "home_program": None,
    },
    # 4 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (toileting awareness/avoidance)",
            "age_years": 11, "age_months": 0,
            "default_environment": "home",
            "interests": ["Squishmellows", "Cars", "Trucks", "Mario", "Soft toys", "Sensory play (playdough, slime)"],
            "proformas": [],
            "current_presentation": (
                "Full motor competence: manages the whole toileting routine "
                "independently when he does use the toilet. Independently manages "
                "nappy changes but needs mum to wipe when this happens. "
                "Inconsistently takes himself to the toilet; frequently passes "
                "bowel motions into his nappy instead. Known trigger: previously "
                "sat on a toilet training chair that wobbled — appears to have "
                "created ongoing avoidance of sitting on the toilet.\n\n"
                "Component gap identified: not a motor-skill case — every physical "
                "component of toileting is already mastered. Two separate things: "
                "(1) interoceptive awareness — noticing the internal bodily signal "
                "that precedes needing to go, and connecting it to action; (2) "
                "fear/avoidance response tied to the wobbly-chair incident, separate "
                "from awareness — needs graded exposure and positive "
                "re-association, not just awareness-building. Working assumption "
                "(flag to confirm): he tolerates being in the bathroom/near the "
                "toilet but avoids sitting on it specifically."
            ),
        },
        "goal": {
            "domain": "toileting",
            "raw_goal_text": "Increase his awareness that he can take himself to the toilet, 80% of the time during the day.",
            "interim_goal_text": (
                "By [date, e.g. 4 weeks], he will tolerate sitting on the toilet for "
                "at least 1 minute, paired with a preferred sensory activity, in 4/5 "
                "attempts (Rung 4 of the exposure ladder)."
            ),
            "outcome_goal_text": (
                "By [date, e.g. 3 months], he will independently take himself to the "
                "toilet to pass a bowel motion in at least 80% of opportunities "
                "across the day, as tracked by a caregiver frequency log."
            ),
        },
        "option_point": None,
        "session_plan": {"session_length_minutes": 20, "environment": "home"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 6,
                "title": "Monster truck engine check",
                "activity_description": (
                    "Big movement (jumping, running on the spot, \"revving up\" like "
                    "a monster truck) for 30-60 seconds, then sitting still and "
                    "noticing heart racing and breathing changes together — naming "
                    "what's noticed (\"my heart is going fast like an engine\")."
                ),
                "clinical_reasoning": (
                    "Interoceptive awareness is a general skill that starts with "
                    "noticing clear, strong body signals (heart rate, breath) before "
                    "it can generalize to subtler signals like bowel urgency. This "
                    "warm-up deliberately targets an easy-to-notice signal first, in "
                    "a context with zero connection to the toilet avoidance."
                ),
                "resources": [],
                "grade_up_note": "Add a second signal to notice at once (heart rate + breathing); use more intense movement for a stronger, clearer signal.",
                "grade_down_note": "Shorter movement burst; focus on just one signal (heart rate only) until that's reliably noticed.",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "Graded exposure ladder (select entry point based on actual current tolerance)",
                "activity_description": (
                    "A hierarchy, not a fixed activity — start at the rung matching "
                    "his real current tolerance, move up only once genuinely "
                    "comfortable, not just compliant. Rung 1: in the bathroom with "
                    "preferred sensory play (playdough/slime), toilet present but not "
                    "engaged. Rung 2: touching the toilet seat/lid with a hand while "
                    "continuing preferred play nearby (confirm seat is stable first). "
                    "Rung 3: sitting on the closed lid, fully clothed, briefly, with a "
                    "preferred sensory item in hand. Rung 4: sitting on the toilet as "
                    "for actual use, clothed initially if needed, brief timed sit, "
                    "with distraction/preferred activity. Rung 5: sitting on the "
                    "toilet as per real toileting attempt, paired with an "
                    "interoceptive check-in prompt (\"does your tummy feel like it "
                    "needs to go?\"), only once rung 4 is comfortable. Suggested "
                    "starting point: Rung 2, adjusted down to Rung 1 if bathroom "
                    "tolerance isn't established or he shows any distress at Rung 2."
                ),
                "clinical_reasoning": (
                    "Progressing too fast past a genuine fear response risks "
                    "reinforcing the avoidance rather than resolving it — the aim is "
                    "comfort at each rung, not just getting him to comply once. "
                    "Pairing every rung with a strongly preferred sensory activity is "
                    "deliberate counter-conditioning: building a new, positive "
                    "association with the toilet alongside — not replacing — the old "
                    "negative one."
                ),
                "resources": [],
                "grade_up_note": "Move to the next rung; reduce reliance on the sensory toy as comfort at the current rung solidifies.",
                "grade_down_note": "Stay at the current rung longer; increase the preferred activity's role; shorten duration; if any distress is shown, drop back a rung rather than pushing through.",
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 5,
                "title": "Squishmellow settle",
                "activity_description": (
                    "Calm, low-demand sensory play with a preferred soft "
                    "toy/squishmellow, regardless of how far up the ladder the "
                    "session got."
                ),
                "clinical_reasoning": (
                    "Ending on a positive, low-demand note — independent of session "
                    "\"success\" against the ladder — protects against the session "
                    "itself becoming another negative association with the "
                    "toilet/bathroom."
                ),
                "resources": [],
                "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 5 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (dressing / transition tolerance)",
            "age_years": 3, "age_months": 0,
            "default_environment": "home",
            "interests": ["Cars", "Trucks", "Planes", "Animals", "Colours", "Numbers"],
            "proformas": [],
            "current_presentation": (
                "Threads arms and legs through clothing independently. Attempts to "
                "pull pants up/down. Doffs (removes) clothing independently when "
                "needed. Becomes upset when asked to dress on days childcare is "
                "later in the day. No difficulty at all with dressing/transitions on "
                "early (6am) drop-off days. Mum's observation: \"he will get dressed "
                "on his own terms.\"\n\n"
                "Component gap identified: motor competence for dressing is largely "
                "already present and age-appropriate — not a skill-building case. "
                "The actual gap is self-initiation and transition tolerance "
                "specifically in a low-immediacy context: when childcare is hours "
                "away, being asked to dress mid-activity registers as an unexpected "
                "interruption rather than a clear, imminent transition."
            ),
        },
        "goal": {
            "domain": "dressing",
            "raw_goal_text": "Parents want him to put his own clothing on — orientation doesn't need to be correct.",
            "interim_goal_text": "",
            "outcome_goal_text": (
                "By [date], he will independently put on his shirt (orientation not "
                "required to be correct) without physical assistance, in at least "
                "4/5 attempts on days when childcare is later in the day — tracked "
                "separately from early drop-off days, since those are already going "
                "well."
            ),
        },
        "option_point": {
            "question_text": (
                "Which complementary strategy should lead: predictability-building "
                "(a visual schedule so dressing isn't an out-of-nowhere "
                "interruption) or choice-embedding (meaningful control within the "
                "dressing task itself)?"
            ),
            "options": [
                "(A) Predictability-building — visual schedule/checklist",
                "(B) Choice-embedding — control over which shirt, which limb first",
            ],
            "selected_option": "(A) Predictability-building, with (B) retained as a secondary element in the main activity",
            "rationale_note": "Predictability and routine are foundational to supporting initiation broadly, not just for this specific transition issue.",
        },
        "session_plan": {"session_length_minutes": 20, "environment": "home"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Today's flight plan",
                "activity_description": (
                    "Make a simple visual checklist with 4-5 picture cards showing "
                    "the sequence of the day, plane/car themed, e.g. \"Play time -> "
                    "Get dressed -> Snack -> Drive to childcare,\" with \"Get "
                    "dressed\" positioned clearly partway through rather than right "
                    "before leaving. Go through the sequence together out loud once "
                    "before free play. Refer back to the \"Get dressed\" card briefly "
                    "a couple of minutes before the main activity starts, as an "
                    "advance heads-up rather than a sudden instruction."
                ),
                "clinical_reasoning": (
                    "Since he manages the immediate, unambiguous transition of early "
                    "drop-off well but struggles when there's a time gap, this builds "
                    "concrete predictability into what's otherwise an abstract "
                    "\"later\" transition — giving him advance information rather "
                    "than an unexpected interruption."
                ),
                "resources": [],
                "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "\"Pit stop\" shirt change with driver's choice",
                "activity_description": (
                    "Bring out a toy race car with a driver figure needing a \"pit "
                    "stop\" to change into driving gear — it's his job to do his own "
                    "pit stop too. Offer two genuine choices before starting: which "
                    "shirt to wear, and which way to start (arms first or head "
                    "first). Let him put the shirt on with no physical assistance "
                    "unless he asks, narrating progress in racing language rather "
                    "than correcting orientation. Once on — regardless of orientation "
                    "— celebrate the \"pit stop\" as complete and race the toy car as "
                    "the payoff. Deliberately schedule this practice for a time that "
                    "is not immediately before an actual transition."
                ),
                "clinical_reasoning": (
                    "Rather than drilling motor components already in place, this "
                    "targets the actual gap — self-initiation under low-immediacy "
                    "conditions — by embedding genuine choice (reducing the "
                    "power-struggle dynamic common at this age) and practicing "
                    "specifically in the harder context. Not correcting orientation "
                    "keeps the win condition genuinely achievable, protecting "
                    "motivation to keep initiating independently."
                ),
                "resources": [],
                "grade_up_note": (
                    "Offer more clothing choices (shirt and shorts); reduce the "
                    "advance-notice window on the visual schedule; introduce the "
                    "practice closer to how it plays out on an actual later-childcare "
                    "day."
                ),
                "grade_down_note": (
                    "Reduce to one choice only (which shirt, no start-side choice); "
                    "extend the advance-notice window; allow a support person to "
                    "start the process alongside him without taking over."
                ),
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 4,
                "title": "Refuel the car",
                "activity_description": (
                    "A short, low-demand \"refuelling\" moment — a small preferred "
                    "snack or a couple of minutes of car play — regardless of how the "
                    "dressing practice went that session."
                ),
                "clinical_reasoning": (
                    "Keeps the overall session association positive and separate "
                    "from task success, which matters given the goal is "
                    "fundamentally about willingness and initiation, not ability."
                ),
                "resources": [],
                "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 6 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (tooth-brushing tolerance / oral desensitization)",
            "age_years": 6, "age_months": 0,
            "default_environment": "home",
            "interests": ["Peppa Pig", "Cars", "Baby Shark", "Music", "Robotic swimming fish"],
            "proformas": ["Autism"],
            "current_presentation": (
                "Non-verbal, communicates via AAC. Does not tolerate toothpaste, "
                "toothbrush, or any novel object in his mouth. Does tolerate the "
                "bottle teat — currently used for self-soothing, not just feeding. "
                "Grinds teeth when concentrating/engaged in an activity — a "
                "self-directed, firm oral-proprioceptive behavior. Very restricted "
                "diet: one specific pureed-with-lumps dish daily, plus yoghurt. "
                "Learned pattern: escalated crying reliably results in the demand "
                "being withdrawn — family has consistently accommodated this.\n\n"
                "Component gap, reframed: not \"zero oral tolerance\" — tolerance is "
                "currently limited to one specific, highly familiar, self-controlled "
                "object (the bottle). The gap is bridging from that known tolerance "
                "point outward, not starting from nothing. Self-direction (him "
                "controlling what enters his mouth and when) looks like the more "
                "important variable than firmness alone, and should shape the whole "
                "approach. All instructions and choices must be offered through his "
                "AAC system, not verbally. Before any oral-adjacent activity, "
                "confirm/teach a clear AAC \"stop\"/\"all done\" signal and commit "
                "to honoring it immediately and completely every time — backing off "
                "to the last comfortable step, not ending the whole session."
            ),
        },
        "goal": {
            "domain": "grooming",
            "raw_goal_text": "Tolerate a toothbrush in his mouth so brushing can begin.",
            "interim_goal_text": (
                "This phase: bring a novel, bottle-adjacent textured object to his "
                "own lips or mouth, self-directed, for at least 3 seconds, in "
                "[X]/5 opportunities. This session works at Rung 1-2 of the "
                "10-rung bridging hierarchy only (1: bottle teat, self-directed; 2: "
                "a near-identical-texture silicone item offered alongside the "
                "bottle, self-directed exploration only) — confirm before starting "
                "whether he tolerates any object other than his own bottle near his "
                "mouth at all; if not, stay at Rung 1."
            ),
            "outcome_goal_text": (
                "Long-term: tolerate a toothbrush touching his teeth for at least "
                "10 seconds, self-initiated, without distress."
            ),
        },
        "option_point": None,
        "session_plan": {"session_length_minutes": 18, "environment": "home"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 6,
                "title": "Car wash hands",
                "activity_description": (
                    "Using a firm-pressure textured mitt or roller (car-themed if "
                    "available), do a \"car wash\" massage game on his hands and arms "
                    "— firm, predictable pressure, paired with Baby Shark or Peppa "
                    "Pig music. Offer AAC choices throughout (\"more\" / \"all "
                    "done\") and follow them immediately. Stay away from the face "
                    "entirely unless he independently brings the tool there himself."
                ),
                "clinical_reasoning": (
                    "Builds regulation and trust using firm, predictable "
                    "proprioceptive input — matching the sensory profile suggested by "
                    "his tolerance for self-directed grinding — in a context with "
                    "zero connection to the mouth, and establishes the AAC "
                    "choice-and-honor pattern before it matters for the harder main "
                    "activity."
                ),
                "resources": [],
                "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 9,
                "title": "\"Bottle friends\" self-directed exploration",
                "activity_description": (
                    "Alongside his usual bottle (available throughout, not "
                    "withheld), offer one new, texturally similar silicone item "
                    "(interest-themed if possible, chosen for a texture close to the "
                    "bottle teat). Place it within reach and let him choose whether "
                    "to explore it, bring it near his face, or bring it to his mouth "
                    "entirely on his own initiative — no hand-over-hand guidance, no "
                    "encouragement to \"just try it,\" no praise contingent on mouth "
                    "contact specifically. Music continues throughout. AAC "
                    "\"stop\"/\"all done\" honored immediately if used."
                ),
                "clinical_reasoning": (
                    "Builds directly from his one known point of oral tolerance "
                    "rather than starting from an assumed zero, and keeps the entire "
                    "interaction self-directed given that self-direction appears to "
                    "be the key variable in what he currently tolerates. No "
                    "adult-initiated touch to his mouth happens at this stage; "
                    "success is measured by exploration and engagement, not by "
                    "reaching the mouth."
                ),
                "resources": [],
                "grade_up_note": "Introduce a second, slightly different-textured item; briefly extend exploration time (if he shows clear comfort/interest fast).",
                "grade_down_note": "Stay purely at Rung 1 — this session becomes trust-building and AAC-system practice only, with the new item simply present, not actively offered again (if the item is refused or ignored entirely).",
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 3,
                "title": "Regulation, on his terms",
                "activity_description": (
                    "Access to his bottle and a preferred calming activity (music, "
                    "robotic swimming fish if calming rather than stimulating for "
                    "him — confirm which), no further oral-adjacent demand at all."
                ),
                "clinical_reasoning": (
                    "Ends the session on unambiguous comfort and self-soothing, "
                    "regardless of how much exploration happened — protecting the "
                    "association with this work overall, given how much rides on it "
                    "staying low-pressure over a long program."
                ),
                "resources": [],
                "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 7 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (postural endurance / seated tolerance)",
            "age_years": 6, "age_months": 0,
            "default_environment": "school",
            "interests": ["Trains", "Cars", "Trucks"],
            "proformas": [],
            "current_presentation": (
                "Flops over/collapses onto the table after ~5 minutes of seated "
                "tabletop work and disengages. Uses an egg chair (a supportive, "
                "bucket-style seat) during floor/mat time — indicating reliance on "
                "extra postural support in another seated context too, not just at "
                "the table.\n\n"
                "Component gap identified: core/postural muscular endurance for "
                "sustained upright sitting is the gap itself, not a downstream "
                "consequence of something else. The egg chair use during mat time is "
                "corroborating data for a generalized postural endurance limitation "
                "across seated contexts. Worth flagging for clinical judgment: if "
                "this pattern is broader than tabletop sitting (loose/floppy "
                "movement generally, easy fatigue across many gross motor "
                "contexts), a wider screen or PT collaboration may be worth "
                "considering rather than treating this as an isolated seated-"
                "endurance goal."
            ),
        },
        "goal": {
            "domain": "gross",
            "raw_goal_text": "Maintain an upright seated position at the table for 10 minutes.",
            "interim_goal_text": (
                "By [date], he will maintain an upright seated position for at "
                "least 7 minutes, in 4/5 opportunities."
            ),
            "outcome_goal_text": (
                "By [date], he will maintain an upright seated position at the "
                "table for at least 10 minutes without postural collapse, in 4/5 "
                "opportunities."
            ),
        },
        "option_point": None,
        "session_plan": {"session_length_minutes": 45, "environment": "school"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Train yard loading",
                "activity_description": (
                    "Crawling or wheelbarrow-walking while pushing small toy trucks "
                    "along a taped floor \"track\" toward a drawn depot. Repeat 3-4 "
                    "loops."
                ),
                "clinical_reasoning": (
                    "Loads the core and shoulder girdle in prone/quadruped "
                    "positioning before any seated demand is introduced — priming "
                    "the postural foundation the seated task depends on."
                ),
                "resources": [],
                "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 5,
                "title": "Truck depot sorting (Main 1)",
                "activity_description": (
                    "Seated at the table, sort toy trucks/cars by color or type into "
                    "labeled depot bins. Use a supportive seating modification as a "
                    "starting scaffold — a wedge or dynamic stability cushion and/or "
                    "a footrest ensuring feet are flat and hips/knees/ankles are near "
                    "90 degrees — informed by his known reliance on extra support in "
                    "the egg chair. Timed at roughly 4-5 minutes, just under his "
                    "documented tolerance."
                ),
                "clinical_reasoning": (
                    "Starting with more external postural support (mirroring the egg "
                    "chair precedent) gives the best chance of meeting the "
                    "seated-tolerance target this early, and ending the block just "
                    "before his typical collapse point protects a sense of success."
                ),
                "resources": [],
                "grade_up_note": "Extend duration slightly beyond 5 min; reduce cushion support toward a standard chair.",
                "grade_down_note": "Shorten to 3-4 min; add more support (e.g. a chair with arms).",
            },
            {
                "block_type": MOVEMENT_RESET, "order": 3, "duration_minutes": 3,
                "title": "All aboard",
                "activity_description": "Stand and move around a small loop like a train, arms as wheels, animal-walk style.",
                "clinical_reasoning": "A brief proprioceptive/movement reset between seated blocks rather than pushing through fatigue toward collapse.",
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 4, "duration_minutes": 5,
                "title": "Train track building (Main 2)",
                "activity_description": (
                    "Seated at the table, build a small toy train track layout, same "
                    "supportive seating setup as Main 1."
                ),
                "clinical_reasoning": (
                    "Continues seated-tolerance practice at the same conservative "
                    "duration this session, while cross-session tracking is what "
                    "actually shows progress toward the 10-minute goal."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MOVEMENT_RESET, "order": 5, "duration_minutes": 3,
                "title": "Truck refuel",
                "activity_description": "A brief standing/movement break — pushing a weighted toy truck a short distance and back.",
                "clinical_reasoning": "",
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 6, "duration_minutes": 5,
                "title": "Car wash checklist (Main 3)",
                "activity_description": (
                    "A simple seated tabletop task themed as a car wash inspection "
                    "checklist (matching/tracing/ticking boxes), same seating "
                    "support continued."
                ),
                "clinical_reasoning": (
                    "A third short seated block rather than one longer one, "
                    "consistent with the session-length scaling rule for a child "
                    "with documented short tolerance."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": WARM_DOWN, "order": 7, "duration_minutes": 5,
                "title": "Calm truck play",
                "activity_description": "A few minutes of low-demand, preferred truck/train play, no seated or postural demand.",
                "clinical_reasoning": "Ends the session on a positive, low-demand note regardless of how long he sustained upright sitting that day.",
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 8 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (sensory regulation / portable toolkit)",
            "age_years": 6, "age_months": 0,
            "default_environment": "school",
            "interests": ["Ice hockey", "Pokemon", "Magic Mixies", "Animals"],
            "proformas": [],
            "current_presentation": (
                "Highly anxious throughout the day. Already self-identifies "
                "dysregulation and requests breaks (toilet or the sensory regulation "
                "room) — a genuinely advanced self-awareness skill, not a gap. The "
                "regulation room is inconsistently available due to staffing. "
                "Becomes significantly dysregulated after school, shutting down "
                "(removing herself, low lighting, quiet) and reacting strongly to "
                "simple demands from a parent at home. History: self-harm (head "
                "banging, scratching). A parent is also highly anxious.\n\n"
                "Component gap, reframed: the self-regulation skill — noticing "
                "dysregulation and asking for help — is already present and more "
                "advanced than most cases. The actual gaps are systemic: (1) access "
                "reliability — support depends on a room that isn't consistently "
                "staffed; (2) reactive-only structure — she has to reach the point "
                "of asking, which, given how well she masks, may already be later "
                "than ideal."
            ),
            "masking_note": (
                "Masks well at school despite being highly anxious throughout the "
                "day. Given how well she masks, a direct verbal check-in (\"how are "
                "you feeling?\") is unlikely to get an accurate answer — use an "
                "indirect visual scale instead."
            ),
        },
        "goal": {
            "domain": "sensory",
            "raw_goal_text": "Implement sensory regulation activities throughout the day so she isn't severely dysregulated by hometime.",
            "interim_goal_text": (
                "Session-level: identify and select at least 2 personally "
                "regulating items from a menu of options, building a portable "
                "toolkit she keeps with her."
            ),
            "outcome_goal_text": (
                "School-day system goal (staff-implemented, not a child-performance "
                "goal): school staff will prompt a brief, scheduled toolkit-use "
                "break at set points across the day, independent of "
                "regulation-room availability."
            ),
        },
        "option_point": {
            "question_text": "Exactly which times/transitions should proactive toolkit-use breaks be scheduled at across her school day?",
            "options": [
                "Mid-morning, before a demanding subject",
                "Before lunch/recess transition",
                "Mid-afternoon",
                "Before end-of-day transition/dismissal",
            ],
            "selected_option": "",
            "rationale_note": "Depends on her actual timetable and what staff can realistically sustain — a starting template only, for the school team to adapt, not prescribed here.",
        },
        "session_plan": {"session_length_minutes": 45, "environment": "school"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 6,
                "title": "Low-demand check-in",
                "activity_description": (
                    "Quiet time with a preferred low-demand item (Magic Mixies or a "
                    "Pokemon toy), with an indirect check-in — pointing to a simple "
                    "1-5 scale rather than asking \"how are you feeling\" directly."
                ),
                "clinical_reasoning": (
                    "Builds rapport and a regulation baseline before any exploration "
                    "task, using the same indirect-check-in pattern that's worked in "
                    "other masking-relevant cases."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 13,
                "title": "\"Trainer's calm kit\" — exploration and selection",
                "activity_description": (
                    "Present a menu of several regulation tool options, framed as "
                    "choosing \"trainer gear\": a fidget item, a small weighted lap "
                    "item, noise-reducing ear defenders, a textured or scented item, "
                    "and a small animal figure for tactile comfort. Let her try each "
                    "briefly and rate how it feels using the same 1-5 scale. "
                    "Collaboratively select her top 2-3 choices and pack them into a "
                    "small pouch or tin she decorates (ice hockey/Pokemon themed)."
                ),
                "clinical_reasoning": (
                    "Since her specific regulating sensory inputs aren't yet known "
                    "from the referral, this is built as genuine exploration and "
                    "self-selection — respecting the self-awareness she's already "
                    "demonstrated rather than the therapist pre-selecting on her "
                    "behalf. Building the kit into something small and personal she "
                    "keeps with her directly solves the access-reliability gap."
                ),
                "resources": ["Weighted lap pad", "Noise-cancelling headphones"],
                "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 3, "duration_minutes": 11,
                "title": "Practicing scheduled, proactive use",
                "activity_description": (
                    "Introduce a simple visual timer or a small set of \"check-in\" "
                    "cards. Practice once during session: at a set point (not "
                    "waiting for her to ask), pause, use the timer/card cue, and "
                    "briefly use one item from her new kit."
                ),
                "clinical_reasoning": (
                    "Directly builds the proactive habit the school-day system goal "
                    "depends on — rehearsing the scheduled, non-optional check-in "
                    "pattern in session before asking staff to run it for real."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": WARM_DOWN, "order": 4, "duration_minutes": 5,
                "title": "Preferred low-demand activity",
                "activity_description": "A few minutes of ice hockey or animal-themed play/drawing, no further regulation demand.",
                "clinical_reasoning": "Ends the session on an unambiguously positive, low-demand note.",
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 9 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (CVI visual tracking)",
            "age_years": 9, "age_months": 0,
            "default_environment": "school",
            "interests": ["iPad videos (Mario, Mister Maker, Octonauts)"],
            "proformas": ["Cortical/Cerebral Visual Impairment (CVI)"],
            "current_presentation": (
                "Preference for red and yellow. Non-verbal; OT exploring "
                "communication access (interested in switch access; has one "
                "functional message so far). Significant tactile sensitivity — does "
                "not hold/grasp objects. Light-sensitive, self-protects by covering "
                "the top of her head.\n\n"
                "Component gap, reframed through CVI: given the strong single-color "
                "preference, likely absent visually-guided reach, and light "
                "sensitivity, \"tracking items around the room\" (implying ambient "
                "complexity, multiple objects, typical room lighting) is probably "
                "well beyond current capacity. The realistic starting point is a "
                "single, familiar, preferred-color object with movement properties, "
                "against a plain background, at close range. Worth distinguishing "
                "light sensitivity (protective avoidance/photophobia) from "
                "light-gazing (a distinct CVI characteristic) — confirm which is "
                "actually happening, since they call for different environmental "
                "responses."
            ),
        },
        "goal": {
            "domain": "visual",
            "raw_goal_text": "Increase visual tracking to items that move around the room.",
            "interim_goal_text": (
                "By [date], she will visually fixate on and track a single "
                "preferred-color (red or yellow), high-contrast, moving object "
                "against a plain background, at close range within her preferred "
                "visual field, for at least 3 seconds, in 4/5 trials."
            ),
            "outcome_goal_text": (
                "Longer-term, multi-stage: tracking a preferred-color moving object "
                "across a wider range (e.g. arm's reach side to side) in a "
                "low-complexity environment — \"around the room\" treated as a "
                "distant target reached through many incremental steps of "
                "increasing distance/field/complexity, not approached directly."
            ),
        },
        "option_point": {
            "question_text": "Red or yellow as the primary stimulus color?",
            "options": ["Red", "Yellow"],
            "selected_option": "",
            "rationale_note": "Both are stated preferences; pick one to start (or alternate across sessions) based on which reads as stronger in practice.",
        },
        "session_plan": {"session_length_minutes": 45, "environment": "school"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Environmental settling, not movement",
                "activity_description": (
                    "Before any visual task, reduce environmental complexity — dim "
                    "lighting, minimal clutter or ambient movement in her visual "
                    "field, seated calmly. Allow her time to settle before "
                    "introducing any target. Not a movement warm-up like other "
                    "domains; environmental preparation specific to her sensory "
                    "profile."
                ),
                "clinical_reasoning": (
                    "Given her light sensitivity and difficulty with visual "
                    "complexity, starting in an already-controlled environment "
                    "matters more than any warm-up activity itself."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 9,
                "title": "Single-object tracking, familiar and repeated",
                "activity_description": (
                    "Using the same object each time (not varying it for novelty), "
                    "present a single plain, preferred-color object with movement or "
                    "shine properties — e.g. a red or yellow shiny/reflective wand or "
                    "a small light-up toy — against a plain, dark, uncluttered "
                    "background. Move it slowly, close range, within her known or "
                    "observed preferred visual field. Allow generous latency — pause "
                    "and wait for her visual response rather than moving on quickly. "
                    "No reaching or holding is asked of her at any point; looking "
                    "only."
                ),
                "clinical_reasoning": (
                    "Matches the core CVI-informed principles directly: single "
                    "preferred color, movement/shine property, plain background, "
                    "familiar/repeated object, and enough processing time. "
                    "Separating the visual task entirely from any reach/grasp demand "
                    "respects both her tactile sensitivity and the likely "
                    "absence-of-visually-guided-reach pattern."
                ),
                "resources": [],
                "grade_up_note": "Slightly increase movement speed or distance; introduce a second, equally familiar preferred-color object.",
                "grade_down_note": "Slow movement further; reduce distance; allow more latency between presentations.",
            },
            {
                "block_type": MOVEMENT_RESET, "order": 3, "duration_minutes": 4,
                "title": "Visual rest break",
                "activity_description": (
                    "A genuinely low-visual-demand pause — dim, quiet, no new visual "
                    "task. Not a movement reset like other domains; visual fatigue, "
                    "not physical fatigue, is the relevant tolerance here."
                ),
                "clinical_reasoning": (
                    "Visual processing itself is effortful in CVI — treating this as "
                    "its own kind of endurance limit, the same way physical "
                    "endurance shaped block structure in the gross motor case, just "
                    "with a different underlying tolerance."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 4, "duration_minutes": 9,
                "title": "Extending range",
                "activity_description": (
                    "Same familiar red/yellow object, same plain background, now "
                    "moved across a slightly wider path within close range."
                ),
                "clinical_reasoning": (
                    "Extends the just-practiced skill incrementally rather than "
                    "jumping to a harder format, keeping every other variable "
                    "constant so only one thing changes at a time."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": WARM_DOWN, "order": 5, "duration_minutes": 5,
                "title": "Preferred iPad time",
                "activity_description": "A few minutes of her chosen, already-tolerated iPad content (Mario, Mister Maker, or Octonauts).",
                "clinical_reasoning": (
                    "Since this is content she already watches and tolerates, it's "
                    "reasonable as a genuinely calming, motivating close — distinct "
                    "from the deliberately simpler therapy stimulus in Main 1/2."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 10 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (childcare transition meltdowns)",
            "age_years": 3, "age_months": 0,
            "default_environment": "school",
            "interests": ["Cars", "Trucks", "Colours", "Numbers and letters"],
            "proformas": [],
            "current_presentation": (
                "NOTE: session held at childcare — Child.Environment has no "
                "\"childcare\" option, seeded as SCHOOL (closest available choice). "
                "Becomes upset transitioning into childcare. Attendance timing is "
                "inconsistent (varies by parents' rotating roster); either parent "
                "may do drop-off/pick-up. One documented meltdown during a "
                "mid-morning transition took 45 minutes to resolve, recovering only "
                "after being removed to a quieter area. Noise-sensitive; closes his "
                "eyes when overwhelmed. The mid-morning transition room is "
                "specifically described as very busy and loud.\n\n"
                "Component gap, reframed: (1) a specific sensory trigger, not "
                "generic transition difficulty — the meltdown coincided with "
                "entering a loud, busy room, alongside known noise sensitivity; (2) "
                "double unpredictability — both drop-off timing and which parent "
                "does it vary day to day. The quiet-space removal that already "
                "worked for recovery is good evidence a calmer environment helps — "
                "the shift worth making is using that proactively (before entry) "
                "rather than only reactively."
            ),
        },
        "goal": {
            "domain": "sensory",
            "raw_goal_text": "Support transitions so meltdowns aren't happening each time.",
            "interim_goal_text": (
                "By [date], he will use a quiet regulation space for at least 2 "
                "minutes upon arrival, before joining the main room, in place of an "
                "escalated meltdown, in 3/5 transitions."
            ),
            "outcome_goal_text": (
                "By [date], he will transition into childcare — regardless of time "
                "of day or which parent drops off — without an escalated meltdown "
                "requiring full removal and extended recovery, in at least 4/5 "
                "transitions, tracked by childcare staff/parent log."
            ),
        },
        "option_point": {
            "question_text": "Is a genuinely separate quiet entry route physically possible at this childcare?",
            "options": [
                "Separate quiet entry route",
                "A quieter corner of the same room before joining the main activity",
            ],
            "selected_option": "",
            "rationale_note": "Depends on the actual layout and staffing at this childcare, not something to assume from outside.",
        },
        "session_plan": {"session_length_minutes": 45, "environment": "school"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Building the quiet space as a genuine base",
                "activity_description": (
                    "Spend a few minutes in the already-known-to-work quiet area, "
                    "engaging with a preferred low-demand activity — cars/trucks or "
                    "simple counting/colour naming — establishing this space as calm "
                    "and enjoyable in its own right, not just somewhere he ends up "
                    "after a meltdown."
                ),
                "clinical_reasoning": (
                    "The quiet space already has a proven regulating effect; using "
                    "it here as a positive starting point supports using it "
                    "proactively later in the session."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "\"Same goodbye every time\"",
                "activity_description": (
                    "With whichever parent is available, build and rehearse a "
                    "short, simple goodbye ritual — identical every time regardless "
                    "of which parent runs it, e.g. \"one more lap for the truck, "
                    "then wave bye-bye at the door.\" Practice it together a few "
                    "times."
                ),
                "clinical_reasoning": (
                    "Restores predictability at the one point that can be made "
                    "consistent even when timing and personnel can't be — the "
                    "ritual itself becomes the stable, familiar cue."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 3, "duration_minutes": 11,
                "title": "Practicing a calm-first entry",
                "activity_description": (
                    "Walk through entering via the quiet area first — a few minutes "
                    "there with a preferred activity — before moving into the main "
                    "room only once settled, narrating the sequence simply each "
                    "time (\"quiet corner first, then trucks room\")."
                ),
                "clinical_reasoning": (
                    "Directly rehearses the proactive shift identified above — calm "
                    "space before the busy room, not only as recovery after "
                    "distress. Practicing the actual sequence in the real "
                    "environment gives caregivers and childcare staff something "
                    "concrete to replicate."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": WARM_DOWN, "order": 4, "duration_minutes": 5,
                "title": "Positive close",
                "activity_description": "A few minutes of preferred play in the main room once settled, ending on a genuinely calm note.",
                "clinical_reasoning": "Confirms the sequence ends somewhere positive — quiet entry leading to successful, calm participation.",
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 11 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "Real client (conversational turn-taking)",
            "age_years": 7, "age_months": 0,
            "default_environment": "school",
            "interests": ["Pokemon", "Lego", "Star Wars"],
            "proformas": ["Autism"],
            "current_presentation": (
                "Social skills still developing per referral. Generally quiet, "
                "talks little in most contexts. When discussing his special "
                "interests, talks at length to the point peers have told him to "
                "stop, which has affected his social engagement with them. Presents "
                "with flat affect.\n\n"
                "Scope note: this goal sits significantly in SLP's "
                "pragmatics/conversational-reciprocity territory — strong candidate "
                "for SLP collaboration if not already involved. OT's contribution "
                "is best scoped to concrete tool-building and structured "
                "turn-taking practice, not underlying language-content teaching.\n\n"
                "Goal, reframed: \"self-awareness\" is internal and unobservable. "
                "Rather than targeting intuitive awareness directly, this plan "
                "builds an explicit, external self-monitoring tool he can use "
                "instead of needing to read subtle social cues — harder and less "
                "certain given both the general difficulty of implicit "
                "social-cue reading and his flat affect. Framing as \"share and "
                "ask\" rather than \"talk less\" matters — the goal is reciprocal "
                "balance, not suppressing his interests."
            ),
        },
        "goal": {
            "domain": "play",
            "raw_goal_text": "Develop self-awareness of when he is talking too much.",
            "interim_goal_text": (
                "By [date], he will use a turn-taking tool during structured "
                "practice conversation to pause after sharing and invite the other "
                "person's turn, in 4/5 practice trials."
            ),
            "outcome_goal_text": (
                "By [date], he will independently use the same tool or an agreed "
                "signal during natural peer interaction to pause his topic and ask "
                "the listener a question, in 4/5 observed opportunities."
            ),
        },
        "option_point": {
            "question_text": "What form should the turn-taking tool/signal take?",
            "options": [
                "A physical turn-token",
                "A visual timer",
                "An agreed subtle hand signal from a peer or adult",
            ],
            "selected_option": "A physical turn-token (used in this worked example, not a fixed prescription)",
            "rationale_note": "Depends on what's feasible in his actual classroom and what SLP may already be using if involved.",
        },
        "session_plan": {"session_length_minutes": 45, "environment": "school"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 6,
                "title": "Introducing the tool",
                "activity_description": (
                    "Introduce a small lightsaber-shaped \"talk baton\" (or similar "
                    "Star Wars/Lego-themed token). Explain the simple rule: whoever "
                    "holds the baton gets to share 2-3 sentences, then passes it and "
                    "asks the other person a question before getting it back. "
                    "Practice the physical pass-and-ask mechanic with a low-stakes, "
                    "neutral topic first."
                ),
                "clinical_reasoning": (
                    "Introduces the concrete mechanic before applying it to the "
                    "harder, higher-motivation context of his actual special "
                    "interests. Keeping the rule explicit avoids relying on any "
                    "cue-reading at all."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "\"Jedi conversation training\" — neutral topic",
                "activity_description": (
                    "Practice the full turn-token routine on a neutral, lower-stakes "
                    "topic (not yet his special interest), tracking successful "
                    "pass-and-question rounds on a simple points chart working "
                    "toward a small \"training badge\" as the payoff."
                ),
                "clinical_reasoning": (
                    "Builds the mechanical skill in a context with less pull toward "
                    "monologuing, before testing it against the harder pull of a "
                    "special-interest topic. The points-and-badge structure gives a "
                    "genuine goal state rather than the practice being an end in "
                    "itself."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 3, "duration_minutes": 11,
                "title": "\"Jedi conversation training\" — high-interest topic",
                "activity_description": (
                    "Same token system and rule, now applied to a genuine "
                    "special-interest topic (Pokemon, Lego, or Star Wars — his "
                    "choice). Continue the points chart toward the same badge."
                ),
                "clinical_reasoning": (
                    "This is the actual trigger context — practice needs to happen "
                    "here, not only on neutral topics, since the pull to monologue "
                    "is specifically strongest around his special interests."
                ),
                "resources": [],
                "grade_up_note": "Reduce the sentence count before passing (e.g. 1-2 sentences instead of 2-3); introduce a peer instead of an adult conversation partner.",
                "grade_down_note": "Increase the sentence count allowed before passing; provide a visual prompt card reminding him of the rule at each turn.",
            },
            {
                "block_type": WARM_DOWN, "order": 4, "duration_minutes": 5,
                "title": "Free talk time",
                "activity_description": (
                    "A few minutes of unstructured, tool-free time to talk about or "
                    "build with a preferred interest, no turn-taking demand at all."
                ),
                "clinical_reasoning": (
                    "Ends on a genuinely positive note that preserves his interests "
                    "as something enjoyable to share, not something to be managed "
                    "or suppressed."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 12 -------------------------------------------------------------- J. dressing (synthetic, has home program)
    {
        "child": {
            "initial_or_name": "J. (synthetic, dressing)",
            "age_years": 5, "age_months": 3,
            "default_environment": "clinic",
            "interests": ["Space/astronauts", "Robots", "Superheroes"],
            "proformas": [],
            "current_presentation": (
                "Independently manages elastic-waist pants and pullover tops. "
                "Struggles specifically with buttons (large and small) — motor "
                "planning of the pinch-and-push action, and visual-spatial "
                "alignment of buttonhole to button. Bilateral coordination "
                "otherwise solid — already manages simple lacing/threading. No "
                "balance or standing-dressing concerns. Sensory: mild preference "
                "against tight collars/snug clothing; no other notable aversions. "
                "Frustration tolerance: tends to disengage after 2-3 failed button "
                "attempts; engages well with game-based framing.\n\n"
                "Component gap identified: bilateral coordination broadly is not "
                "the barrier — J. already manages lacing, a comparable two-handed "
                "task. The specific gap is (1) the motor plan for the pinch-push "
                "button action, and (2) visual-spatial alignment of buttonhole to "
                "button. Secondary factor: documented low frustration tolerance "
                "after repeated failure, meaning early practice needs a "
                "near-guaranteed success rate rather than being graded for "
                "challenge from the start."
            ),
        },
        "goal": {
            "domain": "dressing",
            "raw_goal_text": "Get dressed independently for school.",
            "interim_goal_text": (
                "By [date], J. will independently button 3 large buttons on a "
                "shirt in under 2 minutes, in 4/5 attempts."
            ),
            "outcome_goal_text": (
                "By [date], J. will independently dress for school (pants, top, "
                "fasteners) with no more than 1 prompt, in 4/5 mornings, as tracked "
                "by a caregiver checklist."
            ),
        },
        "option_point": {
            "question_text": "Practice buttons in isolation on a skills board, or embedded within the full dressing routine from the start?",
            "options": [
                "Practice buttons in isolation on a skills board",
                "Practice embedded within the full dressing routine from the start",
            ],
            "selected_option": "Practice buttons in isolation on a skills board (this worked example's approach)",
            "rationale_note": "Depends on the family's routine and J.'s tolerance for combined demands — both are clinically reasonable starting points.",
        },
        "session_plan": {"session_length_minutes": 20, "environment": "clinic"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Robot hand calibration",
                "activity_description": (
                    "Set up a toy robot next to a small pre-built block tower. The "
                    "robot needs \"power cells\" to become strong enough to charge "
                    "through the tower. Place 5 large pom-poms (\"power cells\") in "
                    "a bowl. Using large clothespins or child-safe tweezers, J. "
                    "picks up one power cell at a time and transfers it into the "
                    "robot's \"battery slot.\" Count each power cell aloud as it's "
                    "added. Once all 5 are in, the robot is \"fully charged\" — J. "
                    "then drives/crashes it through the block tower as the payoff."
                ),
                "clinical_reasoning": (
                    "Isolates and warms up the pinch motor pattern that buttoning "
                    "requires, in a lower-stakes, guaranteed-success context before "
                    "applying it to the more demanding, visually precise buttoning "
                    "task — protecting J.'s limited tolerance for early failure by "
                    "ensuring an easy win first. The tower-knockdown payoff turns "
                    "the pincer practice into genuine functional play with a clear "
                    "goal state."
                ),
                "resources": ["Child-safe tweezers or large clothespins"],
                "grade_up_note": "Smaller objects requiring more precision.",
                "grade_down_note": "Larger, easier-to-grip objects; hand-over-hand support initially.",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "Button practice with the Melissa & Doug Basic Skills Board",
                "activity_description": (
                    "Draw or print a simple star map — a dotted path of 5-6 stars "
                    "leading to a picture of the moon, with a small toy rocket that "
                    "can be physically moved along the path. Set up the Melissa & "
                    "Doug Basic Skills Board with the button panel accessible. For "
                    "each button J. successfully fastens (starting with the "
                    "largest), move the rocket one star closer to the moon, "
                    "narrating progress. Once the rocket reaches the moon, J. opens "
                    "a small prize box or places a sticker on a \"mission complete\" "
                    "chart. Once comfortable on the board, repeat the same "
                    "structure using a real or practice garment with large buttons "
                    "instead of the board, framed as \"putting on your real space "
                    "jacket for the mission.\""
                ),
                "clinical_reasoning": (
                    "The board isolates the buttoning motor pattern from the added "
                    "demand of fabric shifting during real garment use, letting J. "
                    "build the specific skill before applying it to a less "
                    "predictable real-world context. The star-map structure breaks "
                    "the goal into a visible sequence of small, achievable wins "
                    "rather than one large, failure-prone attempt, directly "
                    "managing the frustration-tolerance factor noted in his "
                    "presentation."
                ),
                "resources": ["Melissa & Doug Basic Skills Board"],
                "grade_up_note": (
                    "Move from the board to a real shirt; progress from large to "
                    "smaller buttons; reduce visual/verbal cueing."
                ),
                "grade_down_note": (
                    "Stay on the board longer before moving to fabric; use only the "
                    "largest buttons; provide hand-over-hand guidance for the "
                    "alignment step specifically, fading only that part first."
                ),
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 4,
                "title": "Mission control debrief",
                "activity_description": (
                    "J. does 3 \"blast off\" jumps — crouching down low, counting "
                    "down \"3, 2, 1\" together, then jumping up with arms overhead "
                    "like a rocket launching. After the third launch, sit down "
                    "together for a brief \"mission control debrief\": ask J. to "
                    "give a thumbs up, sideways, or down for how the mission felt, "
                    "then give one specific, genuine piece of praise about "
                    "something concrete he did well that session — regardless of "
                    "how far he got with buttons."
                ),
                "clinical_reasoning": (
                    "Given the known frustration-tolerance pattern, ending on a "
                    "positive, achievable physical activity — separate from how the "
                    "button practice specifically went — protects the overall "
                    "session association. The thumbs up/sideways/down check-in "
                    "gives J. a low-demand way to communicate how he felt without "
                    "needing to verbalize it."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": {
            "goal_plain_language": "Help J. get better at buttoning his shirt on his own.",
            "why_this_helps": (
                "Practicing a little bit at home, the same way we work on it in "
                "his sessions, helps him get faster and more confident with "
                "buttons — and means he'll need less help getting dressed for "
                "school over time."
            ),
            "activity_description": (
                "\"Space mission buttons\": draw a simple line of 5 stars on a "
                "piece of paper, ending in a picture of the moon. Using a shirt J. "
                "already owns with large buttons, let him try buttoning it "
                "himself. Each time he manages a button (with as much help as he "
                "currently needs), move a sticker one star closer to the moon. "
                "When the sticker reaches the moon, that's the win — a high five, "
                "a cheer, whatever feels right for your family. The clinic session "
                "uses a specialized practice board — that's not needed at home. A "
                "shirt you already own and a hand-drawn star chart work just as "
                "well for this stage."
            ),
            "home_resources": [],
            "frequency": "A few minutes, 3-4 times a week, 5 minutes or less each time.",
            "grade_up_tip_plain": "Let him try more buttons before you step in to help, or try a shirt with slightly smaller buttons once the big ones are easy.",
            "grade_down_tip_plain": "Do most of the buttons for him and let him finish just the very last one — he still gets to feel like he did it, and that's a real win worth celebrating. Build up from there over the following weeks.",
            "safety_note": "None specific to this activity.",
        },
    },
    # 13 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "T. (synthetic, emotional regulation)",
            "age_years": 8, "age_months": 0,
            "default_environment": "clinic",
            "interests": ["Video games", "Basketball", "Drawing"],
            "proformas": [],
            "current_presentation": (
                "Referred for support handling losing games with peers — reacts "
                "with yelling or crying, sometimes shuts down and says \"I'm fine\" "
                "rather than expressing what he's feeling. Emotional vocabulary "
                "limited largely to \"mad\" and \"happy\" — no clear language for "
                "in-between feelings (frustration, disappointment, embarrassment). "
                "No flexible coping strategy currently in use. Tends to blame "
                "others when upset.\n\n"
                "Component gap identified: jumping straight to \"use a coping "
                "strategy after losing\" risks targeting the wrong layer — T.'s "
                "limited emotional vocabulary and pattern of saying \"I'm fine\" or "
                "shutting down suggest the more foundational gap is identifying and "
                "naming his actual feeling state, not yet impulse control or "
                "strategy use specifically.\n\n"
                "Scope note: if these reactions are frequent, intense, or connected "
                "to broader patterns beyond game-losing specifically, this may be "
                "worth flagging for collaboration with a counsellor or psychologist "
                "alongside OT's functional/skill-building lens — this worked "
                "example assumes a situational pattern specific to game contexts."
            ),
            "masking_note": (
                "The shutdown/\"I'm fine\" pattern when upset is itself a form of "
                "masking — his outward presentation (\"fine,\" or blaming others) "
                "likely doesn't match his internal state."
            ),
        },
        "goal": {
            "domain": "emotional",
            "raw_goal_text": "Help T. handle losing games without a big reaction.",
            "interim_goal_text": (
                "By [date], T. will correctly identify and label his own emotional "
                "state using an expanded feelings vocabulary (beyond mad/happy) in "
                "4/5 opportunities during a structured activity."
            ),
            "outcome_goal_text": (
                "By [date], T. will use a taught coping strategy after losing a "
                "low-stakes game, remaining regulated (no yelling/shutdown), in "
                "4/5 opportunities."
            ),
        },
        "option_point": {
            "question_text": "Which coping strategy should be introduced first: a physical strategy or a cognitive strategy?",
            "options": [
                "A physical strategy (e.g. squeezing a stress ball)",
                "A cognitive strategy (e.g. a simple \"next time\" reframe phrase)",
            ],
            "selected_option": "",
            "rationale_note": "Depends on what fits T. and the family's approach; not decided unilaterally.",
        },
        "session_plan": {"session_length_minutes": 20, "environment": "clinic"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Feelings scoreboard",
                "activity_description": (
                    "Using a basketball-themed feelings chart with a wider "
                    "vocabulary than mad/happy (frustrated, disappointed, proud, "
                    "nervous, excited), show T. simple scenario cards (not yet real "
                    "losing situations) and have him match the scenario to a "
                    "feeling. Each correct match scores a point on a mini "
                    "basketball hoop toy."
                ),
                "clinical_reasoning": (
                    "Builds the emotional vocabulary gap identified above in a "
                    "low-stakes, disconnected context before applying it to the "
                    "harder real trigger (an actual loss) — the \"build the "
                    "component skill before the compound task\" pattern used "
                    "throughout every domain."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "Practice game, practice feelings",
                "activity_description": (
                    "Play a short, low-stakes game with a quick, low-intensity "
                    "built-in \"loss\" (a simple dice or card game — not something "
                    "T. is deeply invested in). Immediately after the loss, pause "
                    "and help T. name the feeling using the vocabulary just "
                    "practiced in warm-up. Offer/model a chosen coping strategy "
                    "afterward rather than requiring T. to produce it unprompted "
                    "yet."
                ),
                "clinical_reasoning": (
                    "Deliberately uses a low-stakes game T. isn't emotionally "
                    "invested in, keeping the practice within a tolerable zone "
                    "rather than risking a full reaction during skill-building — "
                    "and targets the identification step specifically, matching "
                    "the actual component gap, rather than skipping ahead to "
                    "strategy use before the vocabulary/awareness piece is solid."
                ),
                "resources": [],
                "grade_up_note": (
                    "Use a game T. cares about more; require him to name the "
                    "feeling independently before it's offered; introduce the "
                    "coping strategy as something he selects rather than has "
                    "modeled."
                ),
                "grade_down_note": (
                    "Keep the game entirely low-stakes; provide full support "
                    "naming the feeling; skip the coping-strategy step for now and "
                    "focus purely on identification."
                ),
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 4,
                "title": "Drawing time",
                "activity_description": (
                    "A few minutes of drawing, a known calming preferred activity, "
                    "ending with one specific strength-based comment about "
                    "something T. did well that session — not focused on the loss "
                    "itself."
                ),
                "clinical_reasoning": "Ends on a positive, low-demand note that reinforces effort and skill-building rather than the losing scenario.",
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 14 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "M. (synthetic, feeding)",
            "age_years": 3, "age_months": 8,
            "default_environment": "home",
            "interests": ["Trains", "Farm animals", "Bubbles"],
            "proformas": [],
            "current_presentation": (
                "Self-feeds most foods by hand; inconsistent spoon/fork use, "
                "frequently drops the utensil or spills before reaching mouth. "
                "Sensory profile: avoids mixed/lumpy textures (soup with chunks, "
                "pasta with sauce); tolerates smooth purees and dry, crunchy foods "
                "well. No reported gagging, choking, or swallowing safety "
                "concerns. Referral raised two possible goal areas: utensil use, "
                "and expanding food texture tolerance.\n\n"
                "Standing safety flag for this domain: any signs of gagging "
                "progressing to choking, coughing during/after swallowing, or "
                "other aspiration signs should prompt referral to SLP for a "
                "swallowing assessment rather than continued OT-led practice — not "
                "relevant to this specific case but a standing checklist item for "
                "every feeding case.\n\n"
                "Component gap identified: sensory tolerance is not the barrier "
                "for this specific goal — M. already tolerates smooth purees well. "
                "The actual gap is purely the motor control of the utensil itself: "
                "scooping, keeping food on the spoon, and guiding it to the mouth "
                "without spilling. Using an already-tolerated food isolates this "
                "motor demand from the sensory challenge."
            ),
        },
        "goal": {
            "domain": "feeding",
            "raw_goal_text": "Utensil use, or expanding food texture tolerance (two possible goal areas raised at referral).",
            "interim_goal_text": "",
            "outcome_goal_text": (
                "By [date], M. will independently use a spoon to self-feed a "
                "smooth, already-tolerated food for at least 5 consecutive scoops "
                "without spilling, in 4/5 opportunities. (Option A: utensil-use "
                "only.)"
            ),
        },
        "option_point": {
            "question_text": "Target utensil use and texture tolerance in the same session, or keep them separate?",
            "options": [
                "(A) Utensil-use only — uses an already-tolerated food to isolate the motor skill from the sensory challenge",
                "(B) Combined — uses a food that also targets texture tolerance, accepting that this stacks two demands into one session",
            ],
            "selected_option": "(A) Utensil-use only (this worked example's approach)",
            "rationale_note": "Depends on family priorities and the therapist's judgment of how much combined demand this child can tolerate at once.",
        },
        "session_plan": {"session_length_minutes": 20, "environment": "home"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Loading the train",
                "activity_description": (
                    "Using a spoon to scoop dry, preferred material (dry cereal, "
                    "rice, or similar) from a bowl and transfer it into a small toy "
                    "train car, \"delivering cargo\" along a short track."
                ),
                "clinical_reasoning": (
                    "Practices the core scooping and utensil-control motor pattern "
                    "in a non-food, low-stakes context first, before applying it to "
                    "an actual eating task — building the motor pattern without "
                    "also managing the separate demand of it being food he needs to "
                    "eat."
                ),
                "resources": [],
                "grade_up_note": "Smaller \"cargo\" pieces requiring more precision; add a distance/speed element.",
                "grade_down_note": "Larger, easier-to-scoop material; shorter transfer distance; adult stabilizes the receiving container.",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 10,
                "title": "Farm animal feeding time",
                "activity_description": (
                    "M. uses a spoon to self-feed a smooth, already-tolerated food "
                    "(clinician selects specific food — e.g. apple puree, mashed "
                    "banana, mashed potato, plain yoghurt, pudding/custard, based on "
                    "this child's specific tolerance and family routine), framed as "
                    "\"feeding time\" for a small farm animal toy watching nearby, "
                    "aiming for consecutive independent scoops."
                ),
                "clinical_reasoning": (
                    "Directly practices the target skill using a food that removes "
                    "sensory tolerance as a confound, so any difficulty observed "
                    "here is attributable to the motor skill itself, not food "
                    "aversion."
                ),
                "resources": [],
                "grade_up_note": "Standard adult-sized spoon instead of child-sized; increase consecutive scoop target; reduce verbal prompting.",
                "grade_down_note": "Built-up/easier-grip spoon handle; pre-loaded spoon (M. only manages the lift-to-mouth portion); hand-over-hand support faded gradually; fewer consecutive scoops targeted per attempt.",
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 5,
                "title": "Bubble break",
                "activity_description": "Bubble play, no food or utensil demand at all.",
                "clinical_reasoning": (
                    "Feeding-related tasks carry a higher risk of the session "
                    "becoming a source of pressure or frustration around food — "
                    "ending on a completely food-unrelated, purely enjoyable "
                    "activity protects the positive association with the session "
                    "overall."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 15 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "K. (synthetic, grooming)",
            "age_years": 4, "age_months": 5,
            "default_environment": "home",
            "interests": ["Unicorns", "Glitter/sparkly things", "Singing"],
            "proformas": [],
            "current_presentation": (
                "Holds the toothbrush with an appropriate grasp — no grip/motor "
                "concern. Brushes front teeth only, inconsistently; doesn't "
                "systematically reach back or side teeth. Oral sensory "
                "sensitivity: gags on mint-flavoured toothpaste; dislikes strong "
                "bristle vibration. Currently tolerates brushing for roughly 10 "
                "seconds before resisting; needs full physical assistance for a "
                "thorough brush.\n\n"
                "Component gap identified: grasp/motor control of the toothbrush "
                "itself isn't the barrier. Two things are actually happening: "
                "systematic coverage (no spatial routine for reaching all "
                "quadrants of her mouth) and oral sensory tolerance (mint flavour "
                "and bristle intensity trigger gagging, capping how long she'll "
                "tolerate brushing at all). Sensory tolerance is likely the "
                "rate-limiter — she can't build the coverage habit if she's "
                "disengaging after 10 seconds regardless of technique."
            ),
        },
        "goal": {
            "domain": "grooming",
            "raw_goal_text": "For K. to brush her teeth independently.",
            "interim_goal_text": (
                "By [date], K. will tolerate toothbrushing with a non-mint "
                "flavoured paste for at least 30 seconds without gagging, in 4/5 "
                "attempts."
            ),
            "outcome_goal_text": (
                "By [date], K. will independently brush all surfaces of her teeth "
                "(front, back, both sides, top and bottom) for at least 2 minutes "
                "once daily, with no more than 1 verbal prompt."
            ),
        },
        "option_point": {
            "question_text": "Prioritise sensory tolerance first before introducing the full coverage routine, or work on both together from the start?",
            "options": [
                "(A) Sensory-first — trial non-mint flavours and a softer/manual brush before introducing the full routine",
                "(B) Combined — introduce the coverage routine and sensory adjustments together, accepting a slower initial pace on coverage",
            ],
            "selected_option": "(A) Sensory-first (this worked example's approach, since sensory tolerance looks like the current bottleneck)",
            "rationale_note": "Depends on what alternative pastes/brushes the family has access to and how much the gagging is currently limiting participation day to day.",
        },
        "session_plan": {"session_length_minutes": 20, "environment": "home"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Unicorn ice-cream lick",
                "activity_description": (
                    "Using a clean, soft-textured tool (a clean silicone teether, a "
                    "soft flannel wrapped around a finger, or a soft baby "
                    "toothbrush with no paste), guide K. to \"lick\" it like an "
                    "ice-cream cone in different directions while singing a "
                    "favourite short song together. Frame the tool as a \"magic "
                    "unicorn wand\" that's helping her mouth get ready to sparkle. "
                    "Oral-sensory input only — no paste, no full brush."
                ),
                "clinical_reasoning": (
                    "Gradual, playful oral-sensory input before the higher-demand "
                    "brushing task supports desensitisation without directly "
                    "confronting the trigger (mint/bristle intensity) yet — the "
                    "same layered approach used in the interoception warm-up, where "
                    "a foundational skill is primed before the harder task that "
                    "depends on it."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "\"Sparkle map\" tooth brushing",
                "activity_description": (
                    "Draw or print a simple 4-quadrant mouth map (front-top, "
                    "front-bottom, back-top, back-bottom), each quadrant decorated "
                    "with a small unicorn or star outline. Using a non-mint "
                    "flavoured toothpaste and K.'s own toothbrush, brush one "
                    "quadrant at a time, singing a short verse or counting to a set "
                    "number together while brushing that section. Once a quadrant "
                    "is done, K. places a glitter sticker on that quadrant's "
                    "outline on the map. Once all four quadrants \"sparkle,\" hold "
                    "up a small hand mirror so she can see her \"shiny unicorn "
                    "smile\" as the payoff."
                ),
                "clinical_reasoning": (
                    "Targets both identified gaps at once: the quadrant map builds "
                    "the systematic coverage routine she doesn't yet have, while "
                    "the non-mint paste addresses the sensory trigger most likely "
                    "limiting her tolerance. Singing/counting per quadrant acts as "
                    "a natural, engaging timer rather than asking her to simply "
                    "\"brush for two minutes.\""
                ),
                "resources": ["Handheld mirror"],
                "grade_up_note": (
                    "Reduce sticker/song support as tolerance builds; reintroduce "
                    "standard mint paste in small trials once non-mint tolerance is "
                    "solid; extend brushing time per quadrant."
                ),
                "grade_down_note": (
                    "Reduce to 2 quadrants (top/bottom only) before introducing "
                    "left/right distinction; shorten the song/count per section; "
                    "allow physical assistance for the back quadrants specifically "
                    "while she independently manages the front."
                ),
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 4,
                "title": "Unicorn shine",
                "activity_description": (
                    "A brief favourite song or a little dance/twirl in front of "
                    "the mirror admiring her \"sparkly smile,\" with no further "
                    "brushing demand."
                ),
                "clinical_reasoning": (
                    "Closes the routine on a positive, low-demand note tied to her "
                    "interests, protecting the overall association with "
                    "tooth-brushing regardless of how much of the map got "
                    "completed that session."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 16 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "A. (synthetic, gross motor)",
            "age_years": 6, "age_months": 0,
            "default_environment": "school",
            "interests": ["Superheroes", "Space"],
            "proformas": [],
            "current_presentation": (
                "Referred after struggling to catch during PE, now avoiding ball "
                "games with peers. Good static and dynamic balance; runs and moves "
                "well. Struggles specifically with catching — poor visual tracking "
                "of moving objects and reactive timing. Can successfully catch a "
                "ball placed directly in his hands (stationary), but the skill "
                "breaks down once the object is moving toward him.\n\n"
                "Component gap identified: balance and bilateral coordination are "
                "both present in static contexts — not a general coordination "
                "deficit. The specific gap is reactive visual tracking and "
                "anticipatory timing for a moving target, distinct from the static "
                "catch he can already do."
            ),
        },
        "goal": {
            "domain": "gross",
            "raw_goal_text": "Improve ball skills so he can play with friends at recess.",
            "interim_goal_text": (
                "By [date], A. will visually track and successfully catch a "
                "slow-rolled ball, in 4/5 attempts."
            ),
            "outcome_goal_text": (
                "By [date], A. will catch a ball thrown from 2m away with a "
                "two-handed catch, in 4/5 attempts, during recess play."
            ),
        },
        "option_point": {
            "question_text": "Start with a ground-level rolled ball (slower, more predictable) or a low aerial underhand toss?",
            "options": [
                "Ground-level rolled ball (more conservative default)",
                "Low aerial underhand toss",
            ],
            "selected_option": "Ground-level rolled ball (more conservative default)",
            "rationale_note": "Depends on what A. tolerates on the day; this worked example uses the rolled-ball entry point as the more conservative default.",
        },
        "session_plan": {"session_length_minutes": 20, "environment": "school"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Superhero radar training",
                "activity_description": (
                    "Roll a large, brightly colored ball slowly across the floor in "
                    "different directions. A. tracks it with his eyes and points at "
                    "it the moment it stops, without catching yet — purely visual "
                    "tracking practice. After 5 successful \"radar spots,\" "
                    "announce his superhero vision is fully powered up."
                ),
                "clinical_reasoning": (
                    "Isolates the visual-tracking component from the "
                    "motor-catching demand, building the foundational skill before "
                    "combining it with the harder reactive-catch task."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "Rocket catch training",
                "activity_description": (
                    "Starting with the same large ball rolled gently along the "
                    "ground, A. attempts to stop and scoop it up with two hands. "
                    "Each successful catch fills a section of a drawn \"rocket fuel "
                    "gauge.\" Once the gauge is full, \"launch\" a toy rocket across "
                    "the room as the payoff. Progress to a slow underhand toss once "
                    "ground-rolled catches are consistent."
                ),
                "clinical_reasoning": (
                    "Builds directly on the visual-tracking skill just practiced, "
                    "adding the motor-catch demand at the lowest-speed, most "
                    "predictable format before introducing aerial timing, a "
                    "substantially harder reactive-timing task."
                ),
                "resources": [],
                "grade_up_note": "Progress to an underhand toss; increase distance; use a smaller ball.",
                "grade_down_note": "Stay with ground-rolled catches longer; reduce distance; use an even larger, softer ball.",
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 4,
                "title": "Mission complete",
                "activity_description": (
                    "A short round of high-fives and a favorite low-demand stretch "
                    "or movement, celebrating \"mission complete\" regardless of "
                    "catch success rate that session."
                ),
                "clinical_reasoning": "Ends on a positive, low-demand note independent of performance — protects motivation for a skill he's already anxious about in front of peers.",
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 17 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "S. (synthetic, sensory regulation)",
            "age_years": 7, "age_months": 0,
            "default_environment": "school",
            "interests": ["Dinosaurs", "Space", "Calm music"],
            "proformas": [],
            "current_presentation": (
                "Becomes overwhelmed by classroom noise. Currently has zero "
                "self-initiated regulation strategies — fully dependent on an "
                "adult removing him from the room once overwhelmed. Not yet clear "
                "whether he has any known strategy repertoire at all.\n\n"
                "Component gap identified: S. does register noise as aversive — "
                "sensory processing awareness isn't the gap. The actual gap is "
                "self-initiation (no strategy currently used without full "
                "adult-led removal) and possibly strategy knowledge (may not have "
                "a known repertoire to draw from at all)."
            ),
        },
        "goal": {
            "domain": "sensory",
            "raw_goal_text": "For S. to calm down independently instead of needing to leave the room.",
            "interim_goal_text": (
                "By [date], S. will identify and request one of two taught "
                "regulation strategies using a visual choice card, in 4/5 "
                "opportunities, before needing full removal from the room."
            ),
            "outcome_goal_text": (
                "By [date], S. will use a self-selected regulation strategy "
                "independently when overwhelmed, remaining in the classroom in at "
                "least 3/5 instances, tracked by teacher log."
            ),
        },
        "option_point": {
            "question_text": "Which regulation strategies should be taught first?",
            "options": [
                "Noise-cancelling headphones",
                "A weighted lap pad",
                "A designated calm corner",
            ],
            "selected_option": "Headphones and a weighted pad (this worked example's choice)",
            "rationale_note": "Depends on what's actually feasible in the real classroom; the actual choice should be made with the teacher's input on what's practical.",
        },
        "session_plan": {"session_length_minutes": 20, "environment": "school"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Space station check-in",
                "activity_description": (
                    "In a calm moment with no trigger present, introduce a simple "
                    "visual \"astronaut fuel gauge\" (low/medium/high) and practice "
                    "pointing to how he feels right now, a few times across the "
                    "session, framed as routine \"mission check-ins.\""
                ),
                "clinical_reasoning": (
                    "Builds the arousal-naming skill in a low-stakes, disconnected "
                    "context first — before expecting him to use it under real "
                    "classroom stress."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "Mission control toolkit",
                "activity_description": (
                    "Introduce a small choice board with two regulation options — "
                    "astronaut-helmet-themed noise-cancelling headphones and a "
                    "\"gravity pad\" (weighted lap pad) — in a simulated, "
                    "moderately (not overwhelmingly) noisy environment. Let S. "
                    "choose and use a strategy self-directed. Teach and honor a "
                    "\"too much\" visual stop card immediately if used — back off "
                    "to a quieter simulated level rather than pushing through. Each "
                    "successful self-directed choice-and-use fills part of a "
                    "\"mission control calm\" chart."
                ),
                "clinical_reasoning": (
                    "Keeps the practice self-directed and consent-based, the same "
                    "pattern used in the oral desensitization case — S. controls "
                    "the input and can signal \"stop,\" which both respects him and "
                    "builds the self-initiation skill directly."
                ),
                "resources": ["Noise-cancelling headphones", "Gravity pad (weighted lap pad)"],
                "grade_up_note": "Increase simulated noise level closer to real classroom volume; reduce visual prompting to choose.",
                "grade_down_note": "Lower the simulated noise level further; provide more direct prompting to use the choice card.",
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 4,
                "title": "Calm music wind-down",
                "activity_description": "A few minutes of his preferred calm/space-themed music, no further regulation demand.",
                "clinical_reasoning": "Ends the session in a genuinely regulated state on a preferred, low-demand note.",
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
    # 18 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "T. (synthetic, toileting)",
            "age_years": 4, "age_months": 2,
            "default_environment": "home",
            "interests": ["Superheroes", "Cars/trains", "Bubbles"],
            "proformas": [],
            "current_presentation": (
                "Daytime bladder/bowel awareness already established — verbalizes "
                "need to go reliably. Fair standing balance; needs support for "
                "single-leg balance while removing/donning pants. Can grip and "
                "pull his waistband up independently while seated on the toilet "
                "edge with feet on the floor — loses balance and needs full "
                "physical support once transitioning to standing to complete the "
                "pull-up. Occasional accidents linked to not managing clothing "
                "quickly enough once he's indicated need — not linked to "
                "awareness/readiness. Sensory: dislikes the feel of wet/soiled "
                "clothing (can be leveraged as a motivator); mild preference for "
                "softer wipes over standard toilet paper.\n\n"
                "Component gap identified: bladder/bowel awareness — the readiness "
                "piece — is already established, so this isn't a "
                "toilet-training-readiness case. T. already independently manages "
                "the seated portion of pulling his waistband up; the genuine, "
                "specific gap is the standing balance transition — moving from "
                "seated to standing while completing the pull-up. The sensory "
                "dislike of wet/soiled clothing is a genuine asset here, not a "
                "barrier — an intrinsic motivator toward the clean, dry end-state. "
                "Goal is scoped to pulling pants up only, per the one-skill-per-"
                "goal rule — wiping technique and pulling pants down would be "
                "separate goals if targeted."
            ),
        },
        "goal": {
            "domain": "toileting",
            "raw_goal_text": "Independently pull pants/underwear up after toileting.",
            "interim_goal_text": "",
            "outcome_goal_text": (
                "By [date], T. will independently pull his pants/underwear up "
                "after toileting, with no more than 1 prompt, in 4/5 "
                "opportunities."
            ),
        },
        "option_point": None,
        "session_plan": {"session_length_minutes": 20, "environment": "home"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Superhero stance",
                "activity_description": (
                    "Standing balance game — holding a single-leg \"superhero "
                    "landing\" pose, alternating legs, with light hip movement "
                    "(marching, gentle lunges) worked in."
                ),
                "clinical_reasoning": (
                    "Single-leg standing balance is a prerequisite for "
                    "independently pulling pants up while standing, so warm-up "
                    "primes that specific foundational skill before the "
                    "clothing-management task itself."
                ),
                "resources": [],
                "grade_up_note": "Longer hold duration; add an arm movement (reaching) while balancing.",
                "grade_down_note": "Allow wall or chair support for balance; reduce hold time.",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "\"Finish the job\" (whole-task, targeted support)",
                "activity_description": (
                    "T. completes the real toileting routine as independently as "
                    "he's already able — including the seated portion of pulling "
                    "his waistband up, which he can already do — with physical "
                    "support provided specifically at the standing balance "
                    "transition, faded progressively (full hand-hold -> fingertip "
                    "support at a stable surface -> independent) as he gains "
                    "stability. Elastic-waist pants are used initially to keep the "
                    "practice focused on the balance transition rather than adding "
                    "fastener complexity at the same time. Superhero-print "
                    "underwear is used if available."
                ),
                "clinical_reasoning": (
                    "Rather than truncating the task to an isolated final step, "
                    "this builds from T.'s genuine current capacity and targets "
                    "support specifically where the real gap is: the standing "
                    "transition. This keeps the practice embedded in the actual, "
                    "whole toileting routine, more meaningful and more likely to "
                    "generalize than repeating an artificial isolated drill. The "
                    "known sensory dislike of wet/soiled clothing is used "
                    "deliberately — completing the routine reliably delivers the "
                    "clean/dry state he already prefers."
                ),
                "resources": [],
                "grade_up_note": (
                    "Fade support at the standing transition further — from a "
                    "light hand-hold to fingertip contact only, then to a nearby "
                    "but untouched support surface, then none; once elastic waist "
                    "is consistently mastered, progress to button or zip pants as "
                    "the next garment-lever step; practice the transition in a "
                    "different, less familiar bathroom to generalize."
                ),
                "grade_down_note": (
                    "Provide full hand-hold support through the standing "
                    "transition; reduce the number of standing repetitions per "
                    "session; if standing balance is too unreliable yet, practice "
                    "the transition itself in isolation before reintroducing it "
                    "into the whole routine."
                ),
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 4,
                "title": "Bubble hands",
                "activity_description": (
                    "Hand-washing to close the routine, using bubble-themed soap "
                    "or blowing a few bubbles as part of the rinse-off."
                ),
                "clinical_reasoning": (
                    "Closing the full toileting sequence with hand-washing "
                    "reinforces the natural end point of the routine, and pairing "
                    "it with a preferred, sensory-pleasant activity leaves the "
                    "session on a positive note."
                ),
                "resources": [],
                "grade_up_note": "Increase independence in the hand-washing steps themselves (soap, scrub, rinse, dry) rather than just the reward moment.",
                "grade_down_note": "Keep hand-washing fully supported, focus warm-down purely on the positive/reward element.",
            },
        ],
        "home_program": None,
    },
    # 19 --------------------------------------------------------------
    {
        "child": {
            "initial_or_name": "L. (synthetic, visual perception)",
            "age_years": 5, "age_months": 0,
            "default_environment": "clinic",
            "interests": ["Unicorns", "Farm animals", "Colours"],
            "proformas": [],
            "current_presentation": (
                "Referred for pre-literacy visual skill concerns — teacher "
                "reports difficulty finding her own belongings among "
                "similar-looking items in her cubby, and more difficulty with "
                "puzzles than peers. Grasp and fine motor control are "
                "age-appropriate — no motor concern. Notable difficulty with "
                "figure-ground tasks (finding a target among visually similar "
                "distractors) and matching identical images. Performs better with "
                "3D/physical tasks than 2D/picture-based tasks.\n\n"
                "Component gap identified: fine motor/visual-motor integration "
                "isn't the barrier — grasp is fine. The specific gap is "
                "figure-ground discrimination — finding a target among similar "
                "distractors — rather than general matching or visual-motor skill "
                "broadly. Her stronger performance in 3D than 2D formats is "
                "informative and should shape where practice starts, per the "
                "format grading lever in the domain reference."
            ),
        },
        "goal": {
            "domain": "visual",
            "raw_goal_text": "Improve visual skills to help with pre-literacy readiness.",
            "interim_goal_text": (
                "By [date], L. will locate a specific target object among "
                "physical 3D objects in a lightly cluttered set, in 4/5 trials."
            ),
            "outcome_goal_text": (
                "By [date], L. will locate a specific target object within a "
                "moderately cluttered picture/scene in 4/5 trials."
            ),
        },
        "option_point": {
            "question_text": "Progress from 3D to 2D within the same session, or spread the progression across sessions?",
            "options": [
                "Progress 3D to 2D within the same session",
                "Spread 3D and 2D progression across multiple sessions",
            ],
            "selected_option": "",
            "rationale_note": "Depends on how quickly comfort builds on the day — not fixed in advance.",
        },
        "session_plan": {"session_length_minutes": 20, "environment": "clinic"},
        "blocks": [
            {
                "block_type": WARM_UP, "order": 1, "duration_minutes": 5,
                "title": "Unicorn treasure hunt",
                "activity_description": (
                    "Spread 2-3 farm animal figures on the floor along with one "
                    "obviously different unicorn figure (different color/size, "
                    "high visual salience, minimal distractor difficulty). L. "
                    "finds and collects the unicorn each round, placing it in a "
                    "\"treasure chest\" box. After several easy finds, open the "
                    "chest for a small payoff."
                ),
                "clinical_reasoning": (
                    "Warms up the figure-ground skill at the easiest possible "
                    "level — high target salience, few distractors — building an "
                    "early success streak before increasing difficulty."
                ),
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
            {
                "block_type": MAIN, "order": 2, "duration_minutes": 11,
                "title": "Farm hide and seek",
                "activity_description": (
                    "Hide farm animal toys among an increasing number of "
                    "similar-looking distractor objects — staying in 3D per her "
                    "presentation. Each found animal \"comes home\" to a toy barn. "
                    "Once comfortable in 3D, offer the option to try a printed "
                    "\"busy farm scene\" picture (2D) with the same find-the-animal "
                    "task, completing the same barn scene as the payoff either "
                    "way."
                ),
                "clinical_reasoning": (
                    "Builds the figure-ground skill using her stronger current "
                    "format (3D) before asking her to transfer it to the harder 2D "
                    "format, directly reflecting the format-preference noted in "
                    "her presentation instead of treating it as incidental."
                ),
                "resources": [],
                "grade_up_note": "More distractors; more visually similar targets; move to the 2D version.",
                "grade_down_note": "Fewer distractors; larger size difference between target and distractors; stay in 3D longer.",
            },
            {
                "block_type": WARM_DOWN, "order": 3, "duration_minutes": 4,
                "title": "Free colouring",
                "activity_description": "A few minutes of colouring or free play with a preferred toy, no visual-search demand.",
                "clinical_reasoning": "Ends on a calm, low-demand, preferred activity, protecting motivation for a skill area she's currently finding effortful.",
                "resources": [], "grade_up_note": "", "grade_down_note": "",
            },
        ],
        "home_program": None,
    },
]


class Command(BaseCommand):
    help = "Seed the 19 Phase 0 worked examples and 1 home-program example"

    @transaction.atomic
    def handle(self, *args, **options):
        domains = {}
        for key, slug in DOMAIN_SLUGS.items():
            try:
                domains[key] = Domain.objects.get(slug=slug)
            except Domain.DoesNotExist as exc:
                raise CommandError(
                    f"Domain '{slug}' not found — run `manage.py seed_resources` first."
                ) from exc

        proformas = {p.name: p for p in Proforma.objects.all()}

        created = 0
        for case in CASES:
            name = case["child"]["initial_or_name"]
            Child.objects.filter(initial_or_name=name).delete()

            interests = [
                Interest.objects.get_or_create(name=n)[0]
                for n in case["child"]["interests"]
            ]
            child = Child.objects.create(
                initial_or_name=name,
                age_years=case["child"]["age_years"],
                age_months=case["child"]["age_months"],
                default_environment=case["child"]["default_environment"],
                current_presentation=case["child"]["current_presentation"],
                masking_note=case["child"].get("masking_note", ""),
            )
            child.interests.set(interests)
            child.proformas.set([proformas[n] for n in case["child"]["proformas"]])

            goal = Goal.objects.create(
                child=child,
                domain=domains[case["goal"]["domain"]],
                raw_goal_text=case["goal"]["raw_goal_text"],
                interim_goal_text=case["goal"]["interim_goal_text"],
                outcome_goal_text=case["goal"]["outcome_goal_text"],
            )

            if case["option_point"]:
                op = case["option_point"]
                OptionPoint.objects.create(
                    goal=goal,
                    question_text=op["question_text"],
                    options_json=op["options"],
                    selected_option=op["selected_option"],
                    rationale_note=op["rationale_note"],
                )

            session_plan = SessionPlan.objects.create(
                goal=goal,
                session_length_minutes=case["session_plan"]["session_length_minutes"],
                environment=case["session_plan"]["environment"],
            )

            for block in case["blocks"]:
                resource_names = [RESOURCE_ALIASES.get(r, r) for r in block["resources"]]
                resources = Resource.objects.filter(name__in=resource_names)
                activity_block = ActivityBlock.objects.create(
                    session_plan=session_plan,
                    block_type=block["block_type"],
                    order=block["order"],
                    duration_minutes=block["duration_minutes"],
                    title=block["title"],
                    activity_description=block["activity_description"],
                    clinical_reasoning=block["clinical_reasoning"],
                    grade_up_note=block["grade_up_note"],
                    grade_down_note=block["grade_down_note"],
                )
                activity_block.resources.set(resources)

            if case["home_program"]:
                hp = case["home_program"]
                home_resources = Resource.objects.filter(
                    name__in=[RESOURCE_ALIASES.get(r, r) for r in hp["home_resources"]]
                )
                home_program = HomeProgram.objects.create(
                    session_plan=session_plan,
                    goal_plain_language=hp["goal_plain_language"],
                    why_this_helps=hp["why_this_helps"],
                    activity_description=hp["activity_description"],
                    frequency=hp["frequency"],
                    grade_up_tip_plain=hp["grade_up_tip_plain"],
                    grade_down_tip_plain=hp["grade_down_tip_plain"],
                    safety_note=hp["safety_note"],
                )
                home_program.home_resources.set(home_resources)

            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {created} worked-example cases "
            f"({sum(len(c['blocks']) for c in CASES)} activity blocks, "
            f"{sum(1 for c in CASES if c['option_point'])} option points, "
            f"{sum(1 for c in CASES if c['home_program'])} home program)."
        ))

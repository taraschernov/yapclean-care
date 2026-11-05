"""Multi-profile test strings for the rule-based cleanup helper.

All `baseline_raw` strings are HAND-WRITTEN illustrations of the pattern each profile
describes. None of them is output of a speech recognizer, and the profile-A references are
TORGO prompt sentences only: the audio was never decoded into these strings. Nothing here
measures recognition quality on real atypical speech (see docs/TORGO_CARE_MODE_BENCHMARK.md).

Covers 4 illustrative cohorts:
- Profile A: Phoneme slips (acoustic slurring, vowel drift): rules cannot repair these
- Profile B: Stuttering & Cluttering (sound repetitions, prolongations, blocks)
- Profile C: Breath Pauses / Spasms (long intra-sentence gaps > 1.2s, fragmentation)
- Profile D: Control Group (Typical Fluent Speech - business emails, casual chat, nuance)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ProfileType = Literal["A", "B", "C", "D"]


@dataclass(frozen=True, slots=True)
class BenchmarkSample:
    """Benchmark test sample across baseline, standard cleanup, and assistive filter."""

    id: str
    profile: ProfileType
    profile_name: str
    description: str
    reference: str
    baseline_raw: str


BENCHMARK_PROFILES: list[BenchmarkSample] = [
    # -------------------------------------------------------------------------
    # Profile A: Phoneme slips (hand-written; the rule-based helper cannot repair them)
    # -------------------------------------------------------------------------
    BenchmarkSample(
        id="slip_voice_cracked",
        profile="A",
        profile_name="Phoneme slips (hand-written, not recognizer output)",
        description="Acoustic slurring and phoneme distortion from TORGO corpus",
        reference="When he speaks, his voice is just a bit cracked and quivers a trifle.",
        baseline_raw="When Epic is light, it does a bit crack and quivers are dripple.",
    ),
    BenchmarkSample(
        id="slip_winter_ooze",
        profile="A",
        profile_name="Phoneme slips (hand-written, not recognizer output)",
        description="Prolonged vowels and severe articulatory imprecision",
        reference="Except in the winter when the ooze or snow or ice prevents,",
        baseline_raw="Again, in the winter window, and not our age perpents.",
    ),
    BenchmarkSample(
        id="slip_grandfather",
        profile="A",
        profile_name="Phoneme slips (hand-written, not recognizer output)",
        description="Consonant weakening and syllable reduction",
        reference="You wished to know all about my grandfather.",
        baseline_raw="You would do not know about it, my grandpa.",
    ),
    BenchmarkSample(
        id="slip_patient_garden",
        profile="A",
        profile_name="Phoneme slips (hand-written, not recognizer output)",
        description="Phonetic drift and consonant weakening",
        reference="The patient walked slowly in the garden.",
        baseline_raw="de payshent wahked slowleh een de gahden.",
    ),
    # -------------------------------------------------------------------------
    # Profile B: Stuttering & Cluttering
    # -------------------------------------------------------------------------
    BenchmarkSample(
        id="stutter_syllables",
        profile="B",
        profile_name="Stuttering & Cluttering",
        description="Articulatory tremors and multi-syllable repetitions",
        reference="Please open the settings menu and configure audio devices.",
        baseline_raw="pl- please op- open the set- settings menu and con- configure aud- audio dev- devices.",
    ),
    BenchmarkSample(
        id="stutter_sound_blocks",
        profile="B",
        profile_name="Stuttering & Cluttering",
        description="Initial sound prolongations and involuntary articulatory blocks",
        reference="The team will present the project update tomorrow.",
        baseline_raw="th- th- the team will p- p- present the pr- project up- update tomorrow.",
    ),
    BenchmarkSample(
        id="cluttering_rapid_spurts",
        profile="B",
        profile_name="Stuttering & Cluttering",
        description="Rapid syllable cluttering and repeated prefix phonemes",
        reference="Can you send me the report before the client meeting?",
        baseline_raw="c- can you s- send me the re- report be- before the cl- client meeting?",
    ),
    # -------------------------------------------------------------------------
    # Profile C: Breath Pauses / Spasms (>1.2s gaps)
    # -------------------------------------------------------------------------
    BenchmarkSample(
        id="pause_fragmented_syllables",
        profile="C",
        profile_name="Breath Pauses & Spasms (>1.2s)",
        description="Prolonged breath pauses interrupting syllable boundaries",
        reference="I need to schedule a doctor appointment for tomorrow morning.",
        baseline_raw="I need to skeh- ... schedule a doc- ... doctor appointment for tomorrow mor- ... morning.",
    ),
    BenchmarkSample(
        id="pause_intra_sentence_spasms",
        profile="C",
        profile_name="Breath Pauses & Spasms (>1.2s)",
        description="Laryngeal spasms and intra-clause breath pauses exceeding 1.2s with broken syllables",
        reference="We must deploy the critical security patch immediately.",
        baseline_raw="We must dep- ... deploy the crit- ... critical security patch im- ... immediately.",
    ),
    BenchmarkSample(
        id="pause_respiratory_gaps",
        profile="C",
        profile_name="Breath Pauses & Spasms (>1.2s)",
        description="Respiratory fatigue causing syllable gaps across verb and noun phrases",
        reference="The physician recommended taking medication after dinner.",
        baseline_raw="The phys- ... physician rec- ... recommended taking med- ... medication after din- ... dinner.",
    ),
    # -------------------------------------------------------------------------
    # Profile D: Control Group (Typical Fluent Speech)
    # -------------------------------------------------------------------------
    BenchmarkSample(
        id="control_business_email",
        profile="D",
        profile_name="Control Group (Fluent Speech)",
        description="Standard professional business dictation",
        reference="Please find attached the quarterly financial summary for your review.",
        baseline_raw="Please find attached the quarterly financial summary for your review.",
    ),
    BenchmarkSample(
        id="control_casual_chat",
        profile="D",
        profile_name="Control Group (Fluent Speech)",
        description="Casual colloquial speech with informal contractions",
        reference="Hey yeah cool, gonna hop on the call in a second.",
        baseline_raw="Hey yeah cool, gonna hop on the call in a second.",
    ),
    BenchmarkSample(
        id="control_lexical_reduplication",
        profile="D",
        profile_name="Control Group (Fluent Speech)",
        description="Valid lexical reduplication ('so-so') indicating nuance",
        reference="The performance was so-so, but honestly I think we can fix it.",
        baseline_raw="The performance was so-so, but honestly I think we can fix it.",
    ),
    BenchmarkSample(
        id="control_rhetorical_repetition",
        profile="D",
        profile_name="Control Group (Fluent Speech)",
        description="Intentional rhetorical repetition for strong emphatic negation",
        reference="No, no, no, that is definitely not what we agreed on yesterday.",
        baseline_raw="No, no, no, that is definitely not what we agreed on yesterday.",
    ),
    BenchmarkSample(
        id="control_colloquial_farewell",
        profile="D",
        profile_name="Control Group (Fluent Speech)",
        description="Informal doubled farewell idiom ('bye-bye')",
        reference="Bye-bye, see you tomorrow at the office.",
        baseline_raw="Bye-bye, see you tomorrow at the office.",
    ),
]

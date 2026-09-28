from pathlib import Path
from collections import Counter
import json
import re
import ollama


# =========================================================
# CONFIG
# =========================================================

MODEL_NAME = "qwen3:8b"

# Tốc độ narration trung bình
WORDS_PER_MINUTE = 130

# Cho phép lệch khoảng ±15%
MIN_WORD_RATIO = 0.85
MAX_WORD_RATIO = 1.15

# Số lần retry nếu AI sinh output không đạt
MAX_RETRIES = 5


# =========================================================
# LOAD PROMPT
# =========================================================

def load_prompt() -> str:
    """
    Đọc system prompt cho AI Script Generator.
    """

    prompt_path = Path(
        "src/ai/prompts/script_prompt.txt"
    )

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy prompt file: {prompt_path}"
        )

    return prompt_path.read_text(
        encoding="utf-8"
    )


# =========================================================
# WORD COUNT
# =========================================================

def count_script_words(script_data: dict) -> int:
    """
    Đếm tổng số từ trong toàn bộ narration.
    """

    script_lines = script_data.get(
        "script",
        []
    )

    if not isinstance(script_lines, list):
        return 0

    full_text = " ".join(
        str(line)
        for line in script_lines
    )

    return len(
        full_text.split()
    )


# =========================================================
# SENTENCE NORMALIZER
# =========================================================

def normalize_sentence(sentence: str) -> str:
    """
    Chuẩn hóa sentence để detect duplicate/repetition.
    """

    sentence = sentence.lower().strip()

    sentence = re.sub(
        r"[^\w\s]",
        "",
        sentence
    )

    sentence = re.sub(
        r"\s+",
        " ",
        sentence
    )

    return sentence


# =========================================================
# REPETITION CHECK
# =========================================================

def check_repetition(
    script_data: dict,
) -> tuple[bool, str]:
    """
    Detect việc AI lặp sentence để padding độ dài.
    """

    script = script_data.get(
        "script",
        []
    )

    if not script:
        return (
            False,
            "Script is empty."
        )

    normalized = [
        normalize_sentence(sentence)
        for sentence in script
    ]

    counts = Counter(
        normalized
    )

    # ---------------------------------------------
    # Không cho một câu xuất hiện quá 2 lần
    # ---------------------------------------------

    repeated = {
        sentence: count
        for sentence, count in counts.items()
        if count > 2
    }

    if repeated:
        return (
            False,
            f"Repeated sentences detected: {repeated}"
        )

    # ---------------------------------------------
    # Check tỷ lệ câu unique
    # ---------------------------------------------

    total_sentences = len(
        normalized
    )

    unique_sentences = len(
        set(normalized)
    )

    unique_ratio = (
        unique_sentences
        / total_sentences
    )

    # Ít nhất 85% câu phải unique
    if unique_ratio < 0.85:
        return (
            False,
            f"Too much repetition. "
            f"Unique sentence ratio: "
            f"{unique_ratio:.2%}"
        )

    return (
        True,
        "Repetition check passed."
    )


# =========================================================
# INTERNAL ID CHECK
# =========================================================

def contains_internal_character_id(
    script_data: dict,
) -> bool:
    """
    Kiểm tra narration có lộ internal ID HUSKY_01 không.
    """

    script_lines = script_data.get(
        "script",
        []
    )

    full_text = " ".join(
        str(line)
        for line in script_lines
    )

    return (
        "HUSKY_01"
        in full_text
    )


# =========================================================
# STAGE DIRECTION CHECK
# =========================================================

def contains_stage_direction(
    script_data: dict,
) -> bool:
    """
    Kiểm tra camera/edit direction
    không nên xuất hiện trong narration.
    """

    script_lines = script_data.get(
        "script",
        []
    )

    full_text = " ".join(
        str(line).lower()
        for line in script_lines
    )

    banned_phrases = [
        "screen goes black",
        "screen went black",
        "fade out",
        "fade to black",
        "cut to",
        "camera pans",
        "camera zooms",
        "zoom in",
        "zoom out",
    ]

    for phrase in banned_phrases:

        if phrase in full_text:
            return True

    return False


# =========================================================
# VALIDATOR
# =========================================================

def validate_script(
    script_data: dict,
    duration_minutes: int,
) -> tuple[bool, str]:
    """
    Validate:
    - structure
    - hook
    - narration length
    - repetition
    - internal character ID
    - camera/edit directions
    """

    # -----------------------------------------------------
    # Title
    # -----------------------------------------------------

    if not script_data.get(
        "title"
    ):
        return (
            False,
            "Missing title."
        )

    # -----------------------------------------------------
    # Hook
    # -----------------------------------------------------

    if not script_data.get(
        "hook"
    ):
        return (
            False,
            "Missing hook."
        )

    # -----------------------------------------------------
    # Script
    # -----------------------------------------------------

    script = script_data.get(
        "script"
    )

    if not isinstance(
        script,
        list
    ):
        return (
            False,
            "Script must be a list."
        )

    if not script:
        return (
            False,
            "Script is empty."
        )

    # -----------------------------------------------------
    # Check từng sentence
    # -----------------------------------------------------

    for index, sentence in enumerate(
        script,
        start=1,
    ):

        if not isinstance(
            sentence,
            str
        ):
            return (
                False,
                f"Script item {index} "
                f"must be a string."
            )

        if not sentence.strip():
            return (
                False,
                f"Script item {index} "
                f"is empty."
            )

    # -----------------------------------------------------
    # Hook phải giống sentence đầu
    # -----------------------------------------------------

    hook = script_data.get(
        "hook",
        ""
    ).strip()

    first_sentence = script[
        0
    ].strip()

    if hook != first_sentence:
        return (
            False,
            "Hook must be exactly "
            "the first sentence "
            "of the script."
        )

    # -----------------------------------------------------
    # Không được lộ internal ID
    # -----------------------------------------------------

    if contains_internal_character_id(
        script_data
    ):
        return (
            False,
            'Narration contains internal ID "HUSKY_01".'
        )

    # -----------------------------------------------------
    # Không camera/edit direction
    # -----------------------------------------------------

    if contains_stage_direction(
        script_data
    ):
        return (
            False,
            "Narration contains "
            "camera/editing directions."
        )

    # -----------------------------------------------------
    # Repetition QA
    # -----------------------------------------------------

    repetition_valid, repetition_message = (
        check_repetition(
            script_data
        )
    )

    if not repetition_valid:
        return (
            False,
            repetition_message
        )

    # -----------------------------------------------------
    # Calculate expected length
    # -----------------------------------------------------

    target_words = (
        duration_minutes
        * WORDS_PER_MINUTE
    )

    min_words = int(
        target_words
        * MIN_WORD_RATIO
    )

    max_words = int(
        target_words
        * MAX_WORD_RATIO
    )

    actual_words = count_script_words(
        script_data
    )

    # -----------------------------------------------------
    # Too short
    # -----------------------------------------------------

    if actual_words < min_words:
        return (
            False,
            f"Script too short: "
            f"{actual_words} words. "
            f"Expected {min_words}-{max_words}."
        )

    # -----------------------------------------------------
    # Too long
    # -----------------------------------------------------

    if actual_words > max_words:
        return (
            False,
            f"Script too long: "
            f"{actual_words} words. "
            f"Expected {min_words}-{max_words}."
        )

    # -----------------------------------------------------
    # PASS
    # -----------------------------------------------------

    return (
        True,
        f"Script valid: "
        f"{actual_words} words."
    )


# =========================================================
# GENERATE SCRIPT
# =========================================================

def generate_script(
    content: dict,
) -> dict:
    """
    Generate narration bằng Qwen3 local qua Ollama.

    Nếu output không đạt QA:
    - sai JSON
    - quá ngắn
    - quá dài
    - hook sai
    - lộ HUSKY_01
    - có camera direction
    - repetition quá nhiều

    thì tự feedback và retry.
    """

    system_prompt = load_prompt()

    # -----------------------------------------------------
    # Duration
    # -----------------------------------------------------

    duration = int(
        content["duration"]
    )

    target_words = (
        duration
        * WORDS_PER_MINUTE
    )

    min_words = int(
        target_words
        * MIN_WORD_RATIO
    )

    max_words = int(
        target_words
        * MAX_WORD_RATIO
    )

    # Trung bình khoảng 10 từ/câu
    target_sentences = max(
        12,
        round(
            target_words / 10
        )
    )

    # -----------------------------------------------------
    # Convert content → JSON text
    # -----------------------------------------------------

    content_text = json.dumps(
        content,
        ensure_ascii=False,
        indent=2,
    )

    correction_message = ""

    # =====================================================
    # RETRY LOOP
    # =====================================================

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        print()
        print(
            f"AI generation attempt "
            f"{attempt}/{MAX_RETRIES}"
        )

        # -------------------------------------------------
        # User Prompt
        # -------------------------------------------------

        user_prompt = f"""
Here is the video content specification:

{content_text}

STRICT LENGTH REQUIREMENTS:

Target duration:
{duration} minutes.

Target narration length:
approximately {target_words} words.

Acceptable narration length:
between {min_words} and {max_words} words.

Target sentence count:
approximately {target_sentences} short spoken sentences.

IMPORTANT:

- The COMPLETE narration MUST contain at least {min_words} words.
- Aim for approximately {target_words} words.
- Write approximately {target_sentences} short spoken sentences.
- Do NOT return a summary.
- Do NOT stop after only a few events.
- Develop the story fully.
- Add setup, reactions, escalating problems, awkward moments, comedic details, and a proper ending.
- Each item in the script array should normally contain one spoken sentence.
- The FIRST item in the script array MUST be exactly identical to the hook field.
- Never write the internal ID "HUSKY_01" inside the actual narration.
- Refer to the main character naturally as "the husky", "Husky", or "he".
- HUSKY_01 is already a dog.
- Do not randomly introduce "his dog".
- Do not introduce unrelated pets or characters unless the supplied content requires them.
- Keep the comedy grounded in the original situation.
- Do not repeat sentences just to reach the target word count.
- Do not repeat the same ending multiple times.
- Every new sentence should add new action, reaction, information, or comedy.
- Do not include camera directions or editing directions.
- Do not write phrases such as "screen goes black", "cut to", "fade out", or "zoom in".

{correction_message}

Generate the COMPLETE narration now.

Return ONLY valid JSON.
"""

        # -------------------------------------------------
        # Call Ollama
        # -------------------------------------------------

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            format="json",
            think=False,
        )

        raw_text = response[
            "message"
        ][
            "content"
        ]

        # -------------------------------------------------
        # Parse JSON
        # -------------------------------------------------

        try:

            script_data = json.loads(
                raw_text
            )

        except json.JSONDecodeError:

            print(
                "Invalid JSON returned by AI."
            )

            correction_message = """
Your previous response was NOT valid JSON.

Return ONLY valid JSON.

Do not include markdown.
Do not include code fences.
Do not include explanations.
"""

            continue

        # -------------------------------------------------
        # Validate
        # -------------------------------------------------

        valid, message = validate_script(
            script_data,
            duration,
        )

        print(
            message
        )

        # =================================================
        # PASS
        # =================================================

        if valid:

            actual_words = (
                count_script_words(
                    script_data
                )
            )

            estimated_duration = round(
                actual_words
                / WORDS_PER_MINUTE,
                2,
            )

            script_data[
                "actual_word_count"
            ] = actual_words

            script_data[
                "estimated_duration_minutes"
            ] = estimated_duration

            return script_data

        # =================================================
        # FAIL → FEEDBACK
        # =================================================

        actual_words = (
            count_script_words(
                script_data
            )
        )

        # -------------------------------------------------
        # Too short
        # -------------------------------------------------

        if actual_words < min_words:

            missing_words = max(
                0,
                target_words
                - actual_words,
            )

            correction_message = f"""
Your previous script FAILED validation.

Reason:
{message}

Your previous narration contained:
{actual_words} words.

You are still missing approximately:
{missing_words} words.

Rewrite the FULL script from beginning to end.

STRICT REQUIREMENTS:

- Do NOT make it shorter than the previous version.
- Add NEW story events.
- Add NEW Husky reactions.
- Add awkward details.
- Add escalating work-from-home problems.
- Add new comedic beats.
- Add a proper ending.
- Do NOT repeat existing sentences.
- Do NOT repeat the ending.
- Every new sentence should move the story forward.
- The final narration MUST contain at least {min_words} words.
- Aim for approximately {target_words} words.
- Aim for approximately {target_sentences} short sentences.
- The hook MUST be exactly identical to the first script sentence.
- Do NOT use "HUSKY_01" inside the narration.
- Do NOT add camera or editing directions.
- Do NOT return a summary.
"""

        # -------------------------------------------------
        # Too long
        # -------------------------------------------------

        elif actual_words > max_words:

            extra_words = (
                actual_words
                - target_words
            )

            correction_message = f"""
Your previous script FAILED validation.

Reason:
{message}

Your previous narration contained:
{actual_words} words.

It is approximately:
{extra_words} words too long.

Rewrite the FULL script.

STRICT REQUIREMENTS:

- Keep the same story.
- Remove unnecessary repetition.
- Remove duplicated jokes.
- Keep the strongest story beats.
- The final narration MUST contain no more than {max_words} words.
- Aim for approximately {target_words} words.
- Keep sentences short.
- The hook MUST be exactly identical to the first script sentence.
- Do NOT use "HUSKY_01" inside the narration.
- Do NOT add camera or editing directions.
"""

        # -------------------------------------------------
        # Semantic / structure / repetition fail
        # -------------------------------------------------

        else:

            correction_message = f"""
Your previous script FAILED validation.

Reason:
{message}

Rewrite the FULL script from beginning to end.

STRICT REQUIREMENTS:

- Keep the narration between {min_words} and {max_words} words.
- Aim for approximately {target_words} words.
- Do NOT copy or repeat sentences just to increase word count.
- Do NOT repeat the same ending.
- Every new sentence should add new information, action, reaction, or comedy.
- If more length is needed, create NEW story beats instead of repeating existing ones.
- The hook field MUST be exactly identical to the first sentence in the script array.
- Never use the internal ID "HUSKY_01" inside narration.
- The main character IS the husky.
- Do not introduce another dog unless explicitly required.
- Do not introduce unrelated pets or characters.
- Do not include camera directions.
- Do not include editing directions.
- Keep the story coherent and focused.
"""

    # =====================================================
    # ALL RETRIES FAILED
    # =====================================================

    raise ValueError(
        f"AI failed to generate "
        f"a valid {duration}-minute "
        f"script after "
        f"{MAX_RETRIES} attempts."
    )


# =========================================================
# SAVE SCRIPT
# =========================================================

def save_script(
    script_data: dict,
    project_folder: Path,
) -> None:
    """
    Save output thành:

    02_script/
        script.json
        script.txt
    """

    script_folder = (
        project_folder
        / "02_script"
    )

    script_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------
    # Save JSON
    # -----------------------------------------------------

    json_path = (
        script_folder
        / "script.json"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            script_data,
            f,
            ensure_ascii=False,
            indent=4,
        )

    # -----------------------------------------------------
    # Save TXT narration
    # -----------------------------------------------------

    txt_path = (
        script_folder
        / "script.txt"
    )

    script_lines = (
        script_data.get(
            "script",
            []
        )
    )

    txt_content = "\n".join(
        script_lines
    )

    txt_path.write_text(
        txt_content,
        encoding="utf-8",
    )
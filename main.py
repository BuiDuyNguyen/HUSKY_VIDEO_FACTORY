from pathlib import Path
import json

from src.ingest.content_parser import (
    parse_content_file,
    validate_content,
)

from src.ai.script_generator import (
    generate_script,
    save_script,
)


# =========================================================
# CONFIG
# =========================================================

INPUT_FOLDER = Path(
    "input/content"
)

PROJECT_FOLDER = Path(
    "projects"
)


# =========================================================
# SAVE CONTENT JSON
# =========================================================

def save_content_json(
    content: dict,
    project_folder: Path,
) -> Path:
    """
    Save standardized content vào:

    projects/<video_name>/01_content/content.json
    """

    content_folder = (
        project_folder
        / "01_content"
    )

    content_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        content_folder
        / "content.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            content,
            f,
            ensure_ascii=False,
            indent=4,
        )

    return output_path


# =========================================================
# PROCESS ONE VIDEO
# =========================================================

def process_video(
    file_path: Path,
) -> None:
    """
    Chạy pipeline cho một content file.
    """

    print()
    print("=" * 70)
    print(
        f"PROCESSING: {file_path.name}"
    )
    print("=" * 70)

    # -----------------------------------------------------
    # STEP 1 — INGEST
    # -----------------------------------------------------

    print()
    print(
        "[1/3] Reading content..."
    )

    content = parse_content_file(
        file_path
    )

    # -----------------------------------------------------
    # STEP 2 — VALIDATE INPUT
    # -----------------------------------------------------

    print(
        "[2/3] Validating content..."
    )

    validate_content(
        content
    )

    # -----------------------------------------------------
    # Create project folder
    # -----------------------------------------------------

    project_name = (
        file_path.stem
    )

    project_folder = (
        PROJECT_FOLDER
        / project_name
    )

    project_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    # -----------------------------------------------------
    # Save canonical content.json
    # -----------------------------------------------------

    content_path = save_content_json(
        content,
        project_folder,
    )

    print(
        f"Content saved → {content_path}"
    )

    # -----------------------------------------------------
    # STEP 3 — AI SCRIPT
    # -----------------------------------------------------

    print()
    print(
        "[3/3] Generating AI script..."
    )

    script_data = generate_script(
        content
    )

    save_script(
        script_data,
        project_folder,
    )

    print()
    print(
        "SCRIPT SUCCESS"
    )

    print(
        f"Words: "
        f"{script_data['actual_word_count']}"
    )

    print(
        f"Estimated duration: "
        f"{script_data['estimated_duration_minutes']} min"
    )

    print()
    print(
        f"PROJECT COMPLETE → "
        f"{project_folder}"
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # Check input folder
    # -----------------------------------------------------

    if not INPUT_FOLDER.exists():

        print(
            f"Input folder không tồn tại: "
            f"{INPUT_FOLDER}"
        )

        return

    # -----------------------------------------------------
    # Find TXT files
    # -----------------------------------------------------

    txt_files = sorted(
        INPUT_FOLDER.glob(
            "*.txt"
        )
    )

    if not txt_files:

        print(
            "Không tìm thấy file content "
            "trong input/content."
        )

        return

    print()
    print(
        "HUSKY VIDEO FACTORY"
    )

    print(
        f"Found {len(txt_files)} job(s)."
    )

    # -----------------------------------------------------
    # Process jobs
    # -----------------------------------------------------

    success_count = 0
    failed_count = 0

    for file_path in txt_files:

        try:

            process_video(
                file_path
            )

            success_count += 1

        except Exception as e:

            failed_count += 1

            print()
            print(
                "FAILED"
            )

            print(
                f"File: {file_path.name}"
            )

            print(
                f"Error: {e}"
            )

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    print()
    print("=" * 70)
    print(
        "PIPELINE SUMMARY"
    )
    print("=" * 70)

    print(
        f"Success: {success_count}"
    )

    print(
        f"Failed : {failed_count}"
    )

    print("=" * 70)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
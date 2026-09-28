from pathlib import Path


ALLOWED_FIELDS = {
    "TITLE",
    "IDEA",
    "DURATION",
    "LANGUAGE",
    "TONE",
    "AUDIENCE",
    "NOTES",
}


def parse_content_file(file_path: str) -> dict:
    """
    Đọc file content dạng TXT và chuyển thành dictionary.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    text = file_path.read_text(encoding="utf-8")

    result = {}

    current_field = None
    current_lines = []

    for raw_line in text.splitlines():

        line = raw_line.strip()

        # Kiểm tra xem dòng hiện tại có phải HEADER hay không
        if line.endswith(":"):
            possible_field = line[:-1].strip().upper()

            if possible_field in ALLOWED_FIELDS:

                # Lưu field trước đó
                if current_field is not None:
                    result[current_field] = "\n".join(
                        current_lines
                    ).strip()

                current_field = possible_field.lower()
                current_lines = []

                continue

        # Nếu đang nằm trong một field
        if current_field is not None:
            current_lines.append(raw_line)

    # Lưu field cuối cùng
    if current_field is not None:
        result[current_field] = "\n".join(
            current_lines
        ).strip()

    return result


def validate_content(content: dict) -> None:

    required_fields = [
        "title",
        "idea",
        "duration",
        "language",
        "tone",
    ]

    missing_fields = []

    for field in required_fields:
        if not content.get(field):
            missing_fields.append(field)

    if missing_fields:
        raise ValueError(
            f"Thiếu field bắt buộc: {missing_fields}"
        )

    # duration phải là số
    try:
        duration = int(content["duration"])
    except ValueError:
        raise ValueError(
            f"DURATION phải là số phút. "
            f"Giá trị hiện tại: {content['duration']}"
        )

    if duration <= 0:
        raise ValueError(
            "DURATION phải lớn hơn 0."
        )

    # Convert luôn thành int
    content["duration"] = duration
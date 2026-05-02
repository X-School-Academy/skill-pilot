import sys
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import image_service
import llm_service
import tts_service


TEXT_INPUT = "my new password `abracadabra` should be updated and I should be logged in automatically"
TEMP_OUTPUT_DIR = Path(__file__).resolve().parents[3] / ".skillpilot" / "temp"


def _copy_generated_file(source: str, target_name: str) -> Path:
    source_path = Path(source)
    assert source_path.is_file()
    assert source_path.stat().st_size > 0

    TEMP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = TEMP_OUTPUT_DIR / target_name
    shutil.copyfile(source_path, target)

    assert target.is_file()
    assert target.stat().st_size > 0
    return target


def test_llm_get_text():
    result = llm_service.llm_get_text(
        [
            {
                "role": "user",
                "content": (
                    f"Check how many character a are in this string: '{TEXT_INPUT}'. "
                    "Then reply with exactly this prefix and the number only once: "
                    "'The total number of a is:'"
                ),
            }
        ],
    )
    print(f"llm_get_text raw output:\n{result}")

    assert "The total number of a is:" in result


def test_llm_get_tts():
    result = tts_service.text_to_speech_file(
        "Skill Pilot test audio. Count the letter a in abracadabra.",
    )
    output_path = _copy_generated_file(result, f"test_llm_get_tts{Path(result).suffix or '.wav'}")
    print(f"tts audio output: {output_path}")

    assert output_path.suffix.lower() in {".mp3", ".wav", ".opus", ".aac", ".flac"}


def test_llm_get_image():
    result = image_service.generate_image_file(
        "A simple clean test image of the word Skill Pilot on a white card.",
        size="1024x1024",
    )
    output_path = _copy_generated_file(result, f"test_llm_get_image{Path(result).suffix or '.png'}")
    print(f"image output: {output_path}")

    assert output_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}


def test_llm_get_json():
    result = llm_service.llm_get_json(
        [
            {
                "role": "user",
                "content": (
                    f"Check how many character a are in this string: '{TEXT_INPUT}'. "
                    'Return JSON only in this shape: {"input":"...","count":number,"message":"The total number of a is: N"}'
                ),
            }
        ]
    )
    print(f"llm_get_json raw output:\n{result}")

    assert isinstance(result.get("count"), int)
    assert isinstance(result.get("input"), str)
    assert result["input"] == TEXT_INPUT
    assert isinstance(result.get("message"), str)
    assert result["message"].startswith("The total number of a is:")


def test_llm_stream():
    chunks = list(
        llm_service.llm_stream(
            (
                f"Check how many character a are in this string: '{TEXT_INPUT}'. "
                "Then reply with exactly this prefix and the number only once: "
                "'The total number of a is:'"
            )
        )
    )

    assert chunks[-1] == b"[-DONE-]"
    streamed_text = b"".join(chunk for chunk in chunks if chunk not in {b"[-DONE-]", b"[-ERROR-]"}).decode(
        "utf-8",
        errors="replace",
    )
    print(f"llm_stream raw output:\n{streamed_text}")
    assert "The total number of a is:" in streamed_text

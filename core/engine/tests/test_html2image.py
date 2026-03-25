import sys
from pathlib import Path

import pytest

ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from workflow.video_utils.html2image import capture_image


@pytest.mark.anyio
async def test_capture_image():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          margin: 0;
          width: 320px;
          height: 240px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgb(12, 34, 56);
          color: white;
          font-family: sans-serif;
        }
        .card {
          padding: 16px 24px;
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.14);
        }
      </style>
    </head>
    <body>
      <div class="card">Skill Pilot</div>
    </body>
    </html>
    """

    image_path = await capture_image(
        html_code=html,
        view_width=320,
        view_height=240,
        timeout=20,
        retries=1,
    )

    assert image_path is not None

    print(image_path)

    path = Path(image_path)
    try:
        assert path.exists()
        assert path.is_file()
        assert path.suffix == ".png"
        assert path.stat().st_size > 0
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    finally:
        if path.exists():
            path.unlink()

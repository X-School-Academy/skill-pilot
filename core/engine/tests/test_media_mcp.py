import subprocess
import json
import os


def test_text_to_image():
    request = {
        "server_id": "media",
        "tool_name": "text_to_image",
        "arguments": {
            "prompt": "A serene mountain landscape at sunset with golden light",
            "width": 624,
            "height": 624,
        },
    }

    result = subprocess.run(
        ["core/bin/tool-cli", "request", json.dumps(request)],
        capture_output=True,
        text=True,
        cwd="/Users/frankhe/myworks/skill-pilot-ai",
    )

    print("--- stdout ---")
    print(result.stdout)
    if result.stderr:
        print("--- stderr ---")
        print(result.stderr)

    assert result.returncode == 0, f"tool-cli failed: {result.stderr}"

    output = result.stdout.strip()
    assert output, "No output returned from tool-cli"

    response = json.loads(output)
    assert response, "Empty response from tool"

    # Save raw response for inspection
    os.makedirs(".skillpilot/tests", exist_ok=True)
    with open(".skillpilot/tests/test_text_to_image_output.json", "w") as f:
        json.dump(response, f, indent=2)

    # Response should contain a URL to the generated image
    response_str = json.dumps(response)
    assert any(kw in response_str for kw in ["http", ".png", ".jpg", "url", "image"]), (
        f"Response does not contain an image URL: {response_str}"
    )

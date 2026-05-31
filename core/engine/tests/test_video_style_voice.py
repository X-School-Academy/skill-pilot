from workflow.video_creator import VideoCreatorWorkflow


def test_build_video_style_uses_configured_tts_voice(monkeypatch):
    monkeypatch.setattr(
        "workflow.video_creator.get_tts_provider",
        lambda provider_id: {"id": "skill-pilot", "voice": "alloy"},
    )

    style = VideoCreatorWorkflow._build_video_style("1920x1080", theme="tech")

    assert style.voice_name == "alloy"


def test_build_video_style_keeps_explicit_voice(monkeypatch):
    monkeypatch.setattr(
        "workflow.video_creator.get_tts_provider",
        lambda provider_id: {"id": "skill-pilot", "voice": "alloy"},
    )

    style = VideoCreatorWorkflow._build_video_style(
        "1920x1080",
        theme="tech",
        voice_name="nova",
    )

    assert style.voice_name == "nova"

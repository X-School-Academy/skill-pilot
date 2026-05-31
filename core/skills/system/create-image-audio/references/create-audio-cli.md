# create-audio CLI Usage

Use this CLI when the user asks for text-to-speech audio. It sends the request to the running Skill Pilot engine through the local socket, so the CLI process does not read `config/.env`.

The engine selects the default TTS provider from `config/ai_providers.json5` at `default.tts`.

## Command

```bash
core/bin/create-audio --format mp3 --voice alloy --text "Welcome to Skill Pilot. This short narration was generated from plain text."
```

## Arguments

- `--text`: the plain text to synthesize.
- `--format`: the output audio format, such as `mp3`, `wav`, `opus`, `aac`, `flac`, or `pcm`. Defaults to `mp3`.
- `--voice`: optional TTS voice id. When omitted, the configured provider default voice is used.

## Text Guidance

- Use plain text without Markdown formatting unless the user specifically wants the punctuation read aloud.
- Keep the text as close to the user's requested wording as possible.
- Ask for confirmation before materially rewriting user-provided narration.

## Output

On success, the CLI prints the generated audio file path to stdout.

On failure, it prints an error to stderr and exits non-zero.

## Examples

```bash
core/bin/create-audio --format wav --text "This is a clear test of the text to speech system."
```

```bash
core/bin/create-audio --voice alloy --text "Your daily briefing is ready."
```

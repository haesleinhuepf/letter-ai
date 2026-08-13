from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from .documents import extract_text, read_text, write_docx
from .llm import LLMSettings, LetterLLM

ARCHIVE_DIR = Path.home() / ".letter-ai"
TYPE_PREFIXES = {
    "support letter": "supportletter",
    "recommendation letter": "recommendationletter",
    "letter of intent": "letterofintent",
    "review report": "reviewreport",
    "other": "other",
}


def _parse_json(response: str) -> dict[str, object]:
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"The LLM returned invalid JSON: {response}") from error
    if not isinstance(value, dict):
        raise RuntimeError("The LLM returned JSON in an unexpected format.")
    return value


def _classify_and_summarize(llm: LetterLLM, text: str) -> tuple[str, str]:
    response = llm.complete([
        {
            "role": "system",
            "content": (
                "You analyze application letters. Return only JSON with keys "
                "type and summary. type must be exactly one of: support letter, "
                "recommendation letter, letter of intent, review report, other. "
                "summary must be a JSON "
                "array of concise bullet point strings. Ignore addresses, dates, "
                "page numbers, headers, footers, greetings, and signatures when "
                "summarizing the main content."
            ),
        },
        {"role": "user", "content": text},
    ])
    result = _parse_json(response)
    letter_type = str(result.get("type", "")).strip().lower()
    if letter_type not in TYPE_PREFIXES:
        raise RuntimeError(f"The LLM returned unsupported letter type: {letter_type!r}")
    summary = result.get("summary")
    if isinstance(summary, list):
        summary_text = "\n".join(f"- {str(item).strip()}" for item in summary if str(item).strip())
    else:
        summary_text = str(summary or "").strip()
    if not summary_text:
        raise RuntimeError("The LLM returned an empty summary.")
    return letter_type, summary_text


def _next_archive_paths(letter_type: str, archive_dir: Path) -> tuple[Path, Path]:
    prefix = TYPE_PREFIXES[letter_type]
    index = 1
    while (archive_dir / f"{prefix}{index}.txt").exists() or (archive_dir / f"{prefix}{index}_summary.txt").exists():
        index += 1
    return archive_dir / f"{prefix}{index}.txt", archive_dir / f"{prefix}{index}_summary.txt"


def read_command(input_path: Path, archive_dir: Path, llm: LetterLLM) -> None:
    text = read_text(input_path) if input_path.suffix.lower() == ".txt" else extract_text(input_path)
    if not text:
        raise RuntimeError(f"No body text found in {input_path}.")
    letter_type, summary = _classify_and_summarize(llm, text)
    archive_dir.mkdir(parents=True, exist_ok=True)
    letter_path, summary_path = _next_archive_paths(letter_type, archive_dir)
    letter_path.write_text(text + "\n", encoding="utf-8")
    summary_path.write_text(summary + "\n", encoding="utf-8")
    print(f"Type: {letter_type}")
    print(f"Letter: {letter_path}")
    print(f"Summary: {summary_path}")


def _examples(letter_type: str, archive_dir: Path) -> list[tuple[str, str]]:
    prefix = TYPE_PREFIXES[letter_type]
    examples: list[tuple[str, str]] = []
    for summary_path in sorted(archive_dir.glob(f"{prefix}*_summary.txt")):
        stem = summary_path.name.removesuffix("_summary.txt")
        letter_path = archive_dir / f"{stem}.txt"
        if letter_path.exists():
            examples.append((summary_path.read_text(encoding="utf-8").strip(), letter_path.read_text(encoding="utf-8").strip()))
    return examples


def _draft(llm: LetterLLM, letter_type: str, request: str, examples: list[tuple[str, str]]) -> str:
    messages: list[dict[str, str]] = [{
        "role": "system",
        "content": (
            "Write a polished letter. Preserve the facts from the final request, "
            "do not invent credentials or achievements, and return only the letter "
            "body without commentary or markdown."
        ),
    }]
    for summary, letter in examples:
        messages.append({"role": "user", "content": f"Example summary ({letter_type}):\n{summary}"})
        messages.append({"role": "assistant", "content": letter})
    messages.append({"role": "user", "content": request})
    return llm.complete(messages)


def write_command(input_path: Path, template: Path | None, output: Path, archive_dir: Path, llm: LetterLLM) -> None:
    request = read_text(input_path)
    if not request:
        raise RuntimeError(f"The request file {input_path} is empty.")
    letter_type, _ = _classify_and_summarize(llm, request)
    selected_template = template or archive_dir / "default-template.docx"
    if not selected_template.exists():
        selected_template = None
    letter = _draft(llm, letter_type, request, _examples(letter_type, archive_dir))
    settings = llm.settings
    attribution = (
        "This letter was AI-generated from a list of bullet points using https://github.com/haesleinhuepf/letter-ai "
        f" and the large language model {settings.model} hosted at {settings.base_url}."
    )
    write_docx(letter + "\n\n" + attribution, output, selected_template)
    print(f"Type: {letter_type}")
    print(f"Output: {output}")

    # open the document in the default application if possible
    try:
        if sys.platform == "win32":
            import os
            os.startfile(output)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["open", output])
        else:
            import subprocess
            subprocess.run(["xdg-open", output])
    except Exception as error:
        print(f"Warning: Could not open the generated letter: {error}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="letter-ai")
    parser.add_argument("--archive-dir", type=Path, default=ARCHIVE_DIR, help="Letter archive directory (default: ~/.letter-ai)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    read_parser = subparsers.add_parser("read", help="Summarize and archive a DOCX or TXT letter")
    read_parser.add_argument("input", type=Path)

    write_parser = subparsers.add_parser("write", help="Draft a letter from a text request")
    write_parser.add_argument("input", type=Path)
    write_parser.add_argument("--template", type=Path, help="DOCX template to populate")
    write_parser.add_argument("--output", type=Path, default=Path("generated-letter.docx"), help="Output DOCX path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        llm = LetterLLM()
        if args.command == "read":
            read_command(args.input, args.archive_dir, llm)
        else:
            write_command(args.input, args.template, args.output, args.archive_dir, llm)
    except Exception as error:
        print(f"letter-ai: error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

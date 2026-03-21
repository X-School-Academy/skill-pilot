import re
import subprocess
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from llm_service import llm_get_text

limit_cache: Dict[str, Dict[str, int]] = {}


def _limit_key() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")


def _check_limit(ip: str, key: str, limit: int = 500) -> bool:
    date_key = _limit_key()
    if date_key not in limit_cache:
        limit_cache.clear()
        limit_cache[date_key] = {}
    if key not in limit_cache[date_key]:
        limit_cache[date_key][key] = 0
    limit_cache[date_key][key] += 1
    return limit_cache[date_key][key] <= limit


def _regex_from_string(expr: str) -> re.Pattern:
    if not expr.startswith("/"):
        return re.compile(expr)
    last = expr.rfind("/")
    pattern = expr[1:last]
    flags_str = expr[last + 1 :]
    flags = 0
    if "i" in flags_str:
        flags |= re.IGNORECASE
    if "m" in flags_str:
        flags |= re.MULTILINE
    if "s" in flags_str:
        flags |= re.DOTALL
    return re.compile(pattern, flags)


def _parse_meta(meta: str) -> Dict[str, Any]:
    if not meta:
        return {}
    try:
        import json

        return json.loads(meta)
    except Exception:
        try:
            loaded = yaml.safe_load(meta)
            return loaded if isinstance(loaded, dict) else {}
        except Exception:
            return {}


def _popen_kwargs() -> Dict[str, Any]:
    import os

    if os.name == "nt":
        return {"creationflags": 0x08000000}
    return {}


def _run_command(cmd: List[str], timeout: float) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            **_popen_kwargs(),
        )
    except subprocess.TimeoutExpired:
        raise TimeoutError("Timeout")

    output = (result.stderr or "") + (result.stdout or "")
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, output=output)
    return output.strip()


def execute_code_impl(lang: str, meta: str, source: str, client_ip: str) -> Dict[str, Any]:
    codes = {"lang": lang, "meta": meta, "source": source}

    meta_obj = _parse_meta(meta)

    if meta_obj.get("codeRegex"):
        try:
            if not re.search(_regex_from_string(meta_obj["codeRegex"]), source):
                return {
                    "codes": codes,
                    "status": 0,
                    "result": meta_obj.get("codeRegexMsg")
                    or "Error: Please follow the instruction of the task!",
                }
        except Exception:
            return {"codes": codes, "status": 0, "result": "Error: codeRegex invalid."}

    target_lang = "dart"
    target_ext = "dart"
    max_time = 4

    match lang:
        case "javascript":
            target_lang = "node"
            target_ext = "js"
        case "typescript":
            target_lang = "ts-node"
            target_ext = "ts"
            max_time = 10
        case "python":
            target_lang = "python3"
            target_ext = "py"
        case "php":
            target_lang = "php"
            target_ext = "php"
        case "java":
            target_lang = "java"
            target_ext = "java"
            max_time = 8
        case "kotlin":
            target_lang = "kotlin"
            target_ext = "kts"
            max_time = 40
        case "swift":
            target_lang = "swift"
            target_ext = "swift"
        case "rust":
            target_lang = "rustc"
            target_ext = "rs"
        case "json":
            target_lang = "json"
            target_ext = "json"
        case "markdown":
            target_lang = "markdown"
            target_ext = "md"
        case "c":
            target_lang = "gcc"
            target_ext = "c"
            max_time = 2
        case "cpp" | "c++":
            target_lang = "g++"
            target_ext = "cpp"
            max_time = 2
        case "objc" | "objective-c":
            target_lang = "gcc"
            target_ext = "m"
            max_time = 2
        case "go":
            target_lang = "go"
            target_ext = "go"
            max_time = 2
        case _:
            target_lang = "dart"
            target_ext = "dart"

    status = 1
    result = "OK"
    target_source = source

    if meta_obj.get("testcase_code"):
        testcase_code = re.sub(r"\n?\\```.*\n?", "", str(meta_obj.get("testcase_code")))
        target_source = re.sub(r"\s+main\s*\(", " code_main (", target_source)
        target_source = f"{target_source}\n{testcase_code}"

    if target_lang == "kotlin" and not meta_obj.get("rawCode"):
        if not re.search(r"fun\s+main\s*\(", target_source):
            target_source = f"fun main() {{\n{target_source}\n}}"
    elif target_ext == "dart" and not meta_obj.get("rawCode"):
        if not re.search(r"void\s+main\s*\(", target_source):
            target_source = f"void main() {{\n{target_source}\n}}"
    elif target_ext == "rs" and not meta_obj.get("rawCode"):
        if not re.search(r"fn\s+main\s*\(", target_source):
            target_source = f"fn main() {{\n{target_source}\n}}"
    elif target_lang == "java" and not meta_obj.get("rawCode"):
        if not re.search(r"void\s+main\s*\(", target_source):
            target_source = (
                "public class HelloWorld {\n"
                "  public static void main(String[] args) {\n"
                f"{target_source}\n"
                "  }\n"
                "}"
            )
    elif target_ext == "c" and not meta_obj.get("rawCode"):
        if not re.search(r"\s+main\s*\(", target_source):
            target_source = (
                "#include <stdio.h>\n"
                "int main() {\n"
                f"{target_source}\n"
                "  return 0;\n"
                "}"
            )
    elif target_ext == "cpp" and not meta_obj.get("rawCode"):
        if not re.search(r"\s+main\s*\(", target_source):
            target_source = (
                "#include <iostream>\n"
                "int main() {\n"
                f"{target_source}\n"
                "  return 0;\n"
                "}"
            )
    elif target_ext == "m" and not meta_obj.get("rawCode"):
        if not re.search(r"\s+main\s*\(", target_source):
            target_source = (
                "#import <Foundation/Foundation.h>\n"
                "int main(int argc, const char * argv[]) {\n"
                "  NSAutoreleasePool* pool = [[NSAutoreleasePool alloc] init];\n"
                f"{target_source}\n"
                "  [pool drain];\n"
                "  return 0;\n"
                "}"
            )
    elif target_ext == "go" and not meta_obj.get("rawCode"):
        if not re.search(r"\s+main\s*\(", target_source):
            target_source = (
                "package main\n"
                "import \"fmt\"\n"
                "func main() {\n"
                f"{target_source}\n"
                "}"
            )
    elif target_lang == "php" and not meta_obj.get("rawCode"):
        if "<?php" not in target_source:
            target_source = "<?php\n" + target_source
    elif target_lang in {"json", "markdown"}:
        if meta_obj.get("api") == "chat":
            output = llm_get_text([{"role": "user", "content": target_source}], provider_id=None, client_id=client_ip)
            return {"codes": codes, "status": 1, "result": output}
        if meta_obj.get("api") == "image":
            return {"codes": codes, "status": 1, "result": "[]"}
        return {"codes": codes, "status": 1, "result": target_source}

    if not _check_limit(client_ip, f"other-{client_ip}"):
        return {"codes": codes, "status": 0, "result": "Daily limit reached!"}

    import os

    tmp_base = Path(os.getenv("TMPDIR", tempfile.gettempdir()))

    file_id = uuid.uuid4().hex
    target_file = f"{file_id}.{target_ext}"
    temp_dir = tempfile.TemporaryDirectory(prefix="codes-", dir=str(tmp_base))
    temp_path = Path(temp_dir.name) / target_file
    binary_path = Path(temp_dir.name) / (file_id + (".exe" if os.name == "nt" else ""))

    try:
        temp_path.write_text(target_source, encoding="utf-8", errors="replace")

        try:
            if target_ext in {"c", "cpp", "rs"}:
                if target_ext == "c":
                    compile_cmd = ["gcc", str(temp_path), "-lm", "-o", str(binary_path)]
                elif target_ext == "cpp":
                    compile_cmd = ["g++", "-std=c++11", str(temp_path), "-lm", "-o", str(binary_path)]
                else:
                    compile_cmd = ["rustc", str(temp_path), "-o", str(binary_path)]
                _run_command(compile_cmd, max_time)
                result = _run_command([str(binary_path)], max_time)
            elif target_ext == "m":
                compile_cmd = ["gcc", str(temp_path), "-std=c11", "-o", str(binary_path)]
                result = _run_command(compile_cmd, max_time)
                result = _run_command([str(binary_path)], max_time)
                lines = [
                    line
                    for line in result.split("\n")
                    if "autorelease called without pool for object" not in line
                ]
                result = "\n".join(lines)
            else:
                if target_lang == "ts-node":
                    cmd = ["ts-node", "--swc", str(temp_path)]
                elif target_lang == "go":
                    cmd = ["go", "run", str(temp_path)]
                else:
                    cmd = [target_lang, str(temp_path)]
                result = _run_command(cmd, max_time)

            if meta_obj.get("outputRegex") and status == 1:
                try:
                    if not re.search(_regex_from_string(meta_obj["outputRegex"]), result):
                        return {
                            "codes": codes,
                            "status": 0,
                            "result": meta_obj.get("outputRegexMsg")
                            or "Error: The output is not as expected!",
                        }
                except Exception:
                    return {"codes": codes, "status": 0, "result": "Error: meta.outputRegex invalid."}
        except TimeoutError:
            status = 0
            result = "Timeout!"
        except subprocess.CalledProcessError as e:
            status = 0
            result = e.output or "Error!"

            if target_lang in {"python3", "ts-node", "node"}:
                result = result.replace(str(temp_path), "in your source code")
            elif target_lang == "java":
                result = re.sub(r"[a-z0-9.-]{10,}java:[0-9:]+", "in your source code", result)
            elif target_lang == "kotlin":
                result = re.sub(r"[a-z0-9.-]{10,}kts:[0-9:]+", "in your source code", result)
            elif target_lang == "swift":
                result = re.sub(r"[a-z0-9.-]{10,}swift:[0-9:]+", "in your source code", result)

            result = result.replace(target_file, "in your source code")
        except Exception:
            status = 0
            result = "Error!"
    finally:
        try:
            temp_dir.cleanup()
        except Exception:
            pass

    result = result.replace(str(temp_path), "Your source code")

    if not result:
        result = "Syntax is OK!" if status == 1 else "Error"

    if meta_obj.get("aiCheck_detail") and status:
        request_text = (
            "I want you to act as a coding instructor in a school, please think step by step to complete the request below:\n\n"
            "1. Review the task that was assigned to a student below.\n"
            "2. Examine the code submitted by the student.\n"
            "3. Assign a score to the code on a scale of 0 to 10. please note:\n"
            "   - A score of 0 means the instructions were not followed.\n"
            "   - A score of 10 means the student followed the instructions exactly.\n"
            "4. Only provide the score.\n"
            "5. Do not explain the reason for the score you've given.\n\n"
            "The task was assigned to a student:\n\n"
            f"{meta_obj.get('aiCheck_detail')}\n\n"
            "The code is submitted by the student:\n\n"
            f"```{lang}\n{source}\n```\n"
        )
        try:
            score_text = llm_get_text([{"role": "user", "content": request_text}], provider_id=None, client_id=client_ip)
            score_match = re.search(r"\d+", score_text or "")
            if score_match:
                score = int(score_match.group(0))
                if score < 9:
                    status = 0
                    result += (
                        f"\n\nThe score of your code is {score} out of 10.\n\n"
                        "It does not seem to meet the requirements - by AI code checker."
                    )
        except Exception:
            pass

    return {"codes": codes, "status": status, "result": result}

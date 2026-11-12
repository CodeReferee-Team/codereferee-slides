"""index.html의 발표자 노트로 script.md의 슬라이드별 대본을 다시 만든다.

대본의 원본은 index.html의 <aside class="notes">다. 발표자 창도 여기서 읽는다.
script.md에서 아래 두 표시 사이만 덮어쓰고, 머리말과 부록(예상 질문 등)은 그대로 둔다.

    <!-- 대본 자동 생성 시작 -->
    <!-- 대본 자동 생성 끝 -->

함께 검사하는 것:
- 각 슬라이드의 [→] 개수가 화면 단계(data-step) 수와 같은지
- 시간 표기 (m:ss~m:ss)가 있는지
- 대본 전체 글자 수와 예상 읽기 시간

사용법 (레포 루트에서):
    python tools/sync_script.py           # script.md 갱신
    python tools/sync_script.py --check   # 고치지 않고 검사만. 맞지 않으면 종료 코드 1
"""

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
SCRIPT = ROOT / "script.md"
START = "<!-- 대본 자동 생성 시작 -->"
END = "<!-- 대본 자동 생성 끝 -->"

SECTION = re.compile(r'<section class="slide[^"]*" id="([^"]+)" data-title="([^"]+)">(.*?)</section>', re.S)
NOTES = re.compile(r'<aside class="notes">(.*?)</aside>', re.S)
STEP = re.compile(r'data-step="(\d+)"')
PLAN = re.compile(r"\((\d+):(\d\d)~(\d+):(\d\d)\)")
NOT_SPOKEN = re.compile(r"\(\d+:\d\d~\d+:\d\d\)|\[→\]|\(이 장은.*?\)|시간이 모자라면 이 장은 넘어갑니다\.")
CHARS_PER_MIN = (300, 350)


def read_slides():
    text = INDEX.read_text(encoding="utf-8")
    slides = []
    for sid, title, body in SECTION.findall(text):
        m = NOTES.search(body)
        notes = html.unescape(m.group(1)).strip() if m else ""
        steps = max((int(s) for s in STEP.findall(body)), default=0)
        slides.append({"id": sid, "title": html.unescape(title), "notes": notes, "steps": steps})
    if not slides:
        sys.exit("index.html에서 슬라이드를 찾지 못했다")
    return slides


def check(slides):
    problems = []
    for i, s in enumerate(slides, 1):
        arrows = s["notes"].count("[→]")
        if arrows != s["steps"]:
            problems.append(f"{i}장 {s['title']}: [→] {arrows}개, 화면 단계 {s['steps']}개")
        if not s["notes"]:
            problems.append(f"{i}장 {s['title']}: 대본이 비어 있다")
        elif not PLAN.search(s["notes"]):
            problems.append(f"{i}장 {s['title']}: 시간 표기 (m:ss~m:ss)가 없다")
    return problems


def render(slides):
    out = [START, ""]
    for i, s in enumerate(slides, 1):
        out += [f"## {i}. {s['title']}", "", s["notes"], ""]
    out.append(END)
    return "\n".join(out)


def main():
    check_only = "--check" in sys.argv
    slides = read_slides()
    problems = check(slides)

    spoken = sum(len(NOT_SPOKEN.sub("", s["notes"]).strip()) for s in slides)
    slow, fast = (spoken / c for c in CHARS_PER_MIN)
    print(f"슬라이드 {len(slides)}장, 대본 {spoken:,}자, 읽기 {fast:.1f}~{slow:.1f}분 (분당 {CHARS_PER_MIN[1]}~{CHARS_PER_MIN[0]}자)")
    for p in problems:
        print("확인 필요:", p)

    current = SCRIPT.read_text(encoding="utf-8")
    if START not in current or END not in current:
        sys.exit(f"script.md에 '{START}'와 '{END}' 표시가 없다")
    head, rest = current.split(START, 1)
    _, tail = rest.split(END, 1)
    updated = head + render(slides) + tail

    if check_only:
        stale = updated != current
        if stale:
            print("script.md가 index.html 대본과 다르다. python tools/sync_script.py 로 맞춘다")
        sys.exit(1 if (stale or problems) else 0)

    if updated != current:
        SCRIPT.write_text(updated, encoding="utf-8", newline="\n")
        print("script.md를 갱신했다")
    else:
        print("script.md는 이미 최신이다")


if __name__ == "__main__":
    main()

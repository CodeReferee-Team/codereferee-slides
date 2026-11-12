"""script.md의 대본을 index.html의 발표자 노트에 넣는다.

대본은 script.md에서 고친다. 발표자 창은 index.html의 <aside class="notes">를 읽으므로,
이 스크립트가 script.md의 "## N. 제목" 아래 문단을 N번째 슬라이드의 노트로 옮긴다.
script.md에서 아래 두 표시 사이만 읽는다. 머리말과 부록(예상 질문 등)은 대본이 아니다.

    <!-- 대본 시작 -->
    <!-- 대본 끝 -->

함께 검사하는 것:
- script.md의 대본 수와 슬라이드 수가 같은지
- 각 대본의 [→] 개수가 그 슬라이드의 화면 단계(data-step) 수와 같은지
- 시간 표기 (m:ss~m:ss)가 있는지
- 대본 전체 글자 수와 예상 읽기 시간

사용법 (레포 루트에서):
    python tools/sync_script.py           # index.html 발표자 노트 갱신
    python tools/sync_script.py --check   # 고치지 않고 검사만. 맞지 않으면 종료 코드 1
"""

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
SCRIPT = ROOT / "script.md"
START = "<!-- 대본 시작 -->"
END = "<!-- 대본 끝 -->"

SECTION = re.compile(r'<section class="slide[^"]*" id="([^"]+)" data-title="([^"]+)">.*?</section>', re.S)
NOTES = re.compile(r'(<aside class="notes">)(.*?)(</aside>)', re.S)
STEP = re.compile(r'data-step="(\d+)"')
HEADING = re.compile(r"^## (\d+)\.\s*(.+?)\s*$", re.M)
PLAN = re.compile(r"\(\d+:\d\d~\d+:\d\d\)")
NOT_SPOKEN = re.compile(r"\(\d+:\d\d~\d+:\d\d\)|\[→\]|\(이 장은.*?\)|시간이 모자라면 이 장은 넘어갑니다\.")
CHARS_PER_MIN = (300, 350)


def read_script():
    text = SCRIPT.read_text(encoding="utf-8")
    if START not in text or END not in text:
        sys.exit(f"script.md에 '{START}'와 '{END}' 표시가 없다")
    body = text.split(START, 1)[1].split(END, 1)[0]
    heads = list(HEADING.finditer(body))
    notes = []
    for i, h in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        notes.append({"no": int(h.group(1)), "title": h.group(2), "text": body[h.end():end].strip()})
    return notes


def main():
    check_only = "--check" in sys.argv
    page = INDEX.read_text(encoding="utf-8")
    slides = list(SECTION.finditer(page))
    notes = read_script()

    errors, warnings = [], []
    if len(notes) != len(slides):
        errors.append(f"script.md 대본 {len(notes)}개, 슬라이드 {len(slides)}장. 개수가 같아야 한다")
    for i, n in enumerate(notes, 1):
        if n["no"] != i:
            errors.append(f"script.md {i}번째 대본의 번호가 {n['no']}이다. 1부터 차례로 매긴다")
    if errors:
        for e in errors:
            print("오류:", e)
        sys.exit(1)

    out, pos, spoken = [], 0, 0
    for i, (m, n) in enumerate(zip(slides, notes), 1):
        sec = m.group(0)
        title = html.unescape(m.group(2))
        steps = max((int(s) for s in STEP.findall(sec)), default=0)
        arrows = n["text"].count("[→]")
        if n["title"] != title:
            warnings.append(f"{i}장: script.md 제목 '{n['title']}', 슬라이드 제목 '{title}'")
        if arrows != steps:
            warnings.append(f"{i}장 {title}: [→] {arrows}개, 화면 단계 {steps}개")
        if not PLAN.search(n["text"]):
            warnings.append(f"{i}장 {title}: 시간 표기 (m:ss~m:ss)가 없다")
        spoken += len(NOT_SPOKEN.sub("", n["text"]).strip())
        new_sec = NOTES.sub(lambda a: a.group(1) + html.escape(n["text"], quote=False) + a.group(3), sec, count=1)
        if new_sec == sec and not NOTES.search(sec):
            warnings.append(f"{i}장 {title}: 슬라이드에 발표자 노트 자리가 없다")
        out.append(page[pos:m.start()] + new_sec)
        pos = m.end()
    updated = "".join(out) + page[pos:]

    slow, fast = (spoken / c for c in CHARS_PER_MIN)
    print(f"슬라이드 {len(slides)}장, 대본 {spoken:,}자, 읽기 {fast:.1f}~{slow:.1f}분 (분당 {CHARS_PER_MIN[1]}~{CHARS_PER_MIN[0]}자)")
    for w in warnings:
        print("확인 필요:", w)

    if check_only:
        if updated != page:
            print("index.html 발표자 노트가 script.md와 다르다. python tools/sync_script.py 로 맞춘다")
        sys.exit(1 if (updated != page or warnings) else 0)

    if updated != page:
        INDEX.write_text(updated, encoding="utf-8", newline="")
        print("index.html 발표자 노트를 script.md 대본으로 갱신했다")
    else:
        print("index.html 발표자 노트는 이미 script.md와 같다")


if __name__ == "__main__":
    main()

# 운영체제 환경변수 값을 읽기 위해 os 모듈을 가져온다.
import os

# 현재 날짜와 시간을 저장하기 위해 datetime을 가져온다.
from datetime import datetime

# HTML 문서를 분석하기 위해 BeautifulSoup을 가져온다.
from bs4 import BeautifulSoup

# .env 파일에 저장된 환경변수를 읽기 위해 load_dotenv를 가져온다.
from dotenv import load_dotenv

# Playwright 비동기 API를 사용한다.
from playwright.async_api import async_playwright

# Streamlit 환경에서 asyncio 이벤트 루프를 별도 스레드에서 실행하기 위해 가져온다.
from concurrent.futures import ThreadPoolExecutor

# models.py에 정의된 FaqItem 데이터 클래스를 가져온다.
from model.models import FaqItem


# .env 파일을 읽어서 os.getenv()로 사용할 수 있게 한다.
load_dotenv()


# 무공해차통합누리집(ev.or.kr)에서 수소전기차 관련 FAQ를 수집하는 크롤러이다.
# 실제 FAQ 페이지는 nportal 서브도메인 경로에 있으며,
# JavaScript goPage() 함수를 통해 페이지네이션을 처리한다.
class FaqCrawler:
    SOURCE_SITE = "ev.or.kr"

    # 실제 FAQ 페이지 URL (www 경로는 nportal/main.do 로 리디렉션되므로 사용하지 않는다)
    FAQ_URL = "https://ev.or.kr/nportal/partcptn/initFaqAction.do"

    def crawl(self, max_pages: int = 5) -> list[FaqItem]:
        """ev.or.kr nportal FAQ 페이지를 순차 수집해 FaqItem 리스트로 반환한다.

        페이지당 10개 항목이며 goPage() JS 함수로 이동한다.
        빈 페이지가 나오거나 max_pages에 도달하면 중단한다."""
        all_items: list[FaqItem] = []
        seen_q: set[str] = set()

        for page_no in range(1, max_pages + 1):
            html  = self._get_html(page_no)
            items = self._parse(html)
            if not items:
                break
            for item in items:
                if item.question not in seen_q:
                    seen_q.add(item.question)
                    all_items.append(item)

        return all_items

    # ── 내부 헬퍼 메서드들 ────────────────────────────────────────────────

    def _get_html(self, page_no: int) -> str:
        """Playwright를 별도 스레드에서 실행해 해당 FAQ 페이지 HTML을 가져온다."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_playwright, page_no)
            return future.result()

    def _run_playwright(self, page_no: int) -> str:
        """Windows ProactorEventLoop 위에서 async_playwright를 실행한다."""
        import asyncio
        loop = asyncio.ProactorEventLoop()
        return loop.run_until_complete(self._async_get_html(page_no))

    async def _async_get_html(self, page_no: int) -> str:
        """ev.or.kr FAQ 페이지를 비동기로 가져온다.

        1페이지: FAQ_URL로 직접 이동 후 .board_faq 요소 로드 대기
        2+ 페이지: goPage('statsList', 10, N) JS 함수를 실행해 이동"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page    = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
                )
            )

            await page.goto(self.FAQ_URL, wait_until="networkidle", timeout=60000)

            # .board_faq 요소가 로드될 때까지 대기 (최대 10초)
            try:
                await page.wait_for_selector(".board_faq", timeout=10000)
            except Exception:
                await browser.close()
                return ""

            # 2페이지 이후: JavaScript goPage() 함수로 페이지 이동
            if page_no > 1:
                try:
                    # 현재 첫 번째 FAQ 항목 텍스트 저장 (변경 감지용)
                    prev_first = await page.evaluate("""
                        () => {
                            const el = document.querySelector('.board_faq .faq_title');
                            return el ? el.textContent.trim() : '';
                        }
                    """)
                    await page.evaluate(f"goPage('statsList', 10, {page_no})")
                    # 콘텐츠 변경 대기: 첫 번째 항목 텍스트가 바뀔 때까지 최대 5초
                    for _ in range(10):
                        await page.wait_for_timeout(500)
                        curr_first = await page.evaluate("""
                            () => {
                                const el = document.querySelector('.board_faq .faq_title');
                                return el ? el.textContent.trim() : '';
                            }
                        """)
                        if curr_first and curr_first != prev_first:
                            break
                    else:
                        # 변경이 없으면 마지막 페이지 도달로 간주
                        await browser.close()
                        return ""
                except Exception:
                    await browser.close()
                    return ""

            html = await page.content()
            await browser.close()
        return html

    def _parse(self, html: str) -> list[FaqItem]:
        """ev.or.kr FAQ HTML에서 Q&A 쌍을 추출한다.

        기본 파서: div.board_faq → .faq_title(질문) + .faq_con(답변)
        폴백 파서: dl/dt/dd 또는 ul/li 아코디언"""
        if not html:
            return []

        soup  = BeautifulSoup(html, "lxml")
        now   = datetime.now()
        pairs = self._parse_board_faq(soup) or self._parse_dl(soup) or self._parse_accordion(soup)

        return [
            FaqItem(
                source_site=self.SOURCE_SITE,
                category=cat,
                question=q.strip(),
                answer=a.strip(),
                crawled_at=now,
            )
            for cat, q, a in pairs
            if q.strip()
        ]

    def _parse_board_faq(self, soup: BeautifulSoup) -> list[tuple[str, str, str]]:
        """ev.or.kr nportal FAQ 전용 파서.

        구조: <div class="board_faq">
                <div class="faq_title">
                  Q <span class="faq_badge">카테고리</span> 질문?
                </div>
                <div class="faq_con">A 답변</div>
              </div>
        반환 형식: (category, question, answer) 튜플 리스트"""
        result: list[tuple[str, str, str]] = []
        seen:   set[str]                   = set()

        for div in soup.select("div.board_faq"):
            title_el = div.select_one(".faq_title")
            con_el   = div.select_one(".faq_con")
            badge_el = div.select_one(".faq_badge")

            if not title_el:
                continue

            category = badge_el.get_text(strip=True) if badge_el else ""

            # "Q " 접두어와 배지 텍스트를 제거하여 순수 질문 텍스트만 추출한다.
            q_raw = title_el.get_text(separator=" ", strip=True)
            q = q_raw.replace("Q ", "", 1).replace(category, "", 1).strip()

            # "A " 접두어 제거
            a_raw = con_el.get_text(separator=" ", strip=True) if con_el else ""
            a = a_raw[2:].strip() if a_raw.startswith("A ") else a_raw.strip()

            if q and len(q) > 5 and q not in seen:
                seen.add(q)
                result.append((category, q, a))

        return result

    def _parse_dl(self, soup: BeautifulSoup) -> list[tuple[str, str, str]]:
        """<dl><dt>질문</dt><dd>답변</dd> 패턴 폴백 파서."""
        result: list[tuple[str, str, str]] = []
        for dl in soup.select("dl"):
            dts = dl.find_all("dt", recursive=False)
            dds = dl.find_all("dd", recursive=False)
            for dt, dd in zip(dts, dds):
                q = dt.get_text(separator=" ", strip=True)
                a = dd.get_text(separator=" ", strip=True)
                if q and len(q) > 5:
                    result.append(("", q, a))
        return result

    def _parse_accordion(self, soup: BeautifulSoup) -> list[tuple[str, str, str]]:
        """ul>li 아코디언 구조 폴백 파서."""
        Q_SELS = [".faq_q", ".q_tit", ".board_q", ".question", "strong"]
        A_SELS = [".faq_a", ".a_cont", ".board_a", ".answer", "p"]
        result: list[tuple[str, str, str]] = []
        seen:   set[str]                   = set()

        for container in soup.select("ul.faq_list, ul.faq-list, .faq_wrap ul, .board_list ul"):
            for li in container.find_all("li", recursive=False):
                q_el = next((li.select_one(s) for s in Q_SELS if li.select_one(s)), None)
                a_el = next((li.select_one(s) for s in A_SELS if li.select_one(s)), None)
                if q_el:
                    q = q_el.get_text(separator=" ", strip=True)
                    a = a_el.get_text(separator=" ", strip=True) if a_el else ""
                    if q and len(q) > 5 and q not in seen:
                        seen.add(q)
                        result.append(("", q, a))
        return result


# 현대자동차(hyundai.com) 수소전기차(넥쏘) FAQ를 수집하는 크롤러이다.
# FaqCrawler 와 동일한 구조를 따르며, 수소 관련 키워드를 포함한 항목만 반환한다.
class HyundaiFaqCrawler:
    SOURCE_SITE = "hyundai.com"

    # 현대 고객지원 FAQ 페이지 (카테고리·페이지 파라미터 없이 진입)
    BASE_URL = "https://www.hyundai.com/kr/ko/e/customer/center/faq"

    # 수소 관련 키워드 — 질문 또는 답변에 하나라도 있으면 저장한다.
    H2_KEYWORDS = {"수소", "넥쏘", "nexo", "연료전지", "수소전기", "fcev", "수소차", "수소충전"}

    def crawl(self, max_pages: int = 6) -> list[FaqItem]:
        """현대 FAQ 페이지를 수집해 수소 관련 FaqItem 리스트로 반환한다.

        페이지별로 Playwright를 실행해 아코디언 항목을 펼친 뒤 Q&A를 추출하고
        수소 관련 키워드를 포함한 항목만 필터링해 반환한다."""
        all_items: list[FaqItem] = []

        for page_no in range(1, max_pages + 1):
            html  = self._get_html(page_no)
            items = self._parse(html)
            if not items:
                break
            all_items.extend(items)

        return [item for item in all_items if self._is_h2_related(item)]

    def _is_h2_related(self, item: "FaqItem") -> bool:
        """질문+답변 전문에 수소 관련 키워드가 있으면 True."""
        text = (item.question + " " + item.answer).lower()
        return any(kw in text for kw in self.H2_KEYWORDS)

    def _get_html(self, page_no: int) -> str:
        """Playwright를 별도 스레드에서 실행해 해당 FAQ 페이지 HTML을 가져온다."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._run_playwright, page_no)
            return future.result()

    def _run_playwright(self, page_no: int) -> str:
        """Windows ProactorEventLoop 위에서 async_playwright를 실행한다."""
        import asyncio
        loop = asyncio.ProactorEventLoop()
        return loop.run_until_complete(self._async_get_html(page_no))

    async def _async_get_html(self, page_no: int) -> str:
        """현대 FAQ 페이지를 비동기로 가져온다.

        페이지 이동: JS 페이지네이션 버튼 클릭 후 networkidle 대기
        아코디언:   aria-expanded=false 버튼을 모두 클릭해 답변을 펼침"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page    = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
                )
            )

            await page.goto(self.BASE_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(1500)

            # 2페이지 이후: 페이지 번호 버튼 클릭으로 이동한다.
            if page_no > 1:
                try:
                    # 정확한 숫자 텍스트를 가진 페이지 버튼을 클릭한다.
                    btn = page.locator(
                        f"[class*='pagination'] button, [class*='paging'] button, "
                        f"[class*='page'] button"
                    ).filter(has_text=str(page_no))
                    if await btn.count() > 0:
                        await btn.first.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        await page.wait_for_timeout(800)
                    else:
                        # 페이지 버튼이 없으면 마지막 페이지 도달로 간주한다.
                        await browser.close()
                        return ""
                except Exception:
                    await browser.close()
                    return ""

            # 아코디언 항목을 모두 클릭해 답변을 펼친다.
            # aria-expanded=false 버튼이 있으면 클릭, 없으면 공통 패턴으로 시도한다.
            try:
                await page.evaluate("""
                    Array.from(document.querySelectorAll(
                        'button[aria-expanded="false"], '
                        '.faq-item button, .c-accordion__button, '
                        '[class*="faq"] button, [class*="accordion"] button'
                    )).forEach(el => { try { el.click(); } catch(e) {} });
                """)
                await page.wait_for_timeout(800)
            except Exception:
                pass

            html = await page.content()
            await browser.close()
        return html

    def _parse(self, html: str) -> list[FaqItem]:
        """현대 FAQ HTML에서 Q&A 쌍을 추출한다.

        1순위: aria-expanded 아코디언 패턴 (button + sibling panel)
        2순위: 일반 DL/DT/DD 또는 [카테고리]질문? 텍스트 분리 패턴"""
        if not html:
            return []

        soup  = BeautifulSoup(html, "lxml")
        now   = datetime.now()
        pairs = self._parse_aria_accordion(soup) or self._parse_text_inline(soup)

        return [
            FaqItem(
                source_site=self.SOURCE_SITE,
                category="",
                question=q.strip(),
                answer=a.strip(),
                crawled_at=now,
            )
            for q, a in pairs
            if q.strip()
        ]

    def _parse_aria_accordion(self, soup: BeautifulSoup) -> list[tuple[str, str]]:
        """aria 기반 아코디언 FAQ 파싱.
        button[aria-expanded] + 형제/부모 내 panel div 구조를 처리한다."""
        result: list[tuple[str, str]] = []
        seen:   set[str]              = set()

        for btn in soup.find_all("button", attrs={"aria-expanded": True}):
            q = btn.get_text(separator=" ", strip=True)
            if not q or len(q) <= 5 or q in seen:
                continue

            # 답변은 aria-controls 속성이 가리키는 id에 있거나,
            # 버튼의 부모 컨테이너 내 다음 형제 div에 있다.
            a = ""
            ctrl_id = btn.get("aria-controls")
            if ctrl_id:
                panel = soup.find(id=ctrl_id)
                if panel:
                    a = panel.get_text(separator=" ", strip=True)
            if not a:
                parent = btn.parent
                if parent:
                    siblings = [
                        s for s in parent.find_all(["div", "p"], recursive=False)
                        if s != btn
                    ]
                    if siblings:
                        a = siblings[0].get_text(separator=" ", strip=True)

            seen.add(q)
            result.append((q, a))

        return result

    def _parse_text_inline(self, soup: BeautifulSoup) -> list[tuple[str, str]]:
        """[카테고리]질문? 답변 형식의 인라인 텍스트 FAQ 파싱.
        현대 FAQ 목록은 확장 후 Q와 A가 같은 블록에 있는 경우가 있다."""
        result: list[tuple[str, str]] = []
        seen:   set[str]              = set()

        # [카테고리]질문? 로 시작하는 텍스트 노드를 가진 요소를 찾는다.
        import re
        pattern = re.compile(r"^\s*\[[^\]]+\]")

        for el in soup.find_all(["div", "li", "p"]):
            text = el.get_text(separator=" ", strip=True)
            if not pattern.match(text):
                continue
            # 첫 번째 '?' 위치로 Q/A 분리
            q_end = text.find("?")
            if q_end == -1:
                continue
            q = text[: q_end + 1].strip()
            a = text[q_end + 1:].strip()
            if q and len(q) > 5 and q not in seen:
                seen.add(q)
                result.append((q, a))

        return result


# ── 모듈 레벨 통합 수집 함수 ─────────────────────────────────────────────────

def crawl_all_faqs() -> list[FaqItem]:
    """ev.or.kr 과 hyundai.com 두 소스에서 FAQ를 수집하고 중복 제거 후 반환한다.

    중복 판정 기준: question 텍스트(공백 정규화 + 소문자 비교).
    수집 실패한 소스는 조용히 건너뛰고 나머지 소스의 결과만 반환한다."""
    import re as _re

    all_items: list[FaqItem] = []

    for crawler in (FaqCrawler(), HyundaiFaqCrawler()):
        try:
            all_items.extend(crawler.crawl())
        except Exception as exc:
            print(f"[crawl_all_faqs] {crawler.SOURCE_SITE} 수집 실패: {exc}")

    # 질문 정규화 후 중복 제거 (먼저 추가된 항목 우선)
    seen:   set[str]        = set()
    result: list[FaqItem]   = []
    for item in all_items:
        key = _re.sub(r"\s+", " ", item.question).strip().lower()
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


if __name__ == "__main__":
    items = crawl_all_faqs()
    print(f"수집된 FAQ: {len(items)}개")
    for idx, item in enumerate(items[:5], 1):
        print(f"\n[{idx}] ({item.source_site}) Q: {item.question[:80]}")
        print(f"      A: {item.answer[:120]}")

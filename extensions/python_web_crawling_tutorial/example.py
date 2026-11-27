"""離線示範：robots.txt 判讀、每主機速率限制、ETag 條件請求快取（標準函式庫）。"""
import urllib.robotparser

ROBOTS = """
User-agent: *
Disallow: /admin/
Disallow: /search
Crawl-delay: 5

User-agent: bms-report-bot
Allow: /public/energy/
Disallow: /
Crawl-delay: 10
""".splitlines()

UA = "bms-report-bot"


class FakeServer:
    """模擬伺服器：資料沒變時回 304，並統計傳輸位元組。"""
    def __init__(self):
        self.version = 1
        self.bytes_sent = 0

    def get(self, path, if_none_match=None):
        etag = f'"v{self.version}"'
        if if_none_match == etag:
            self.bytes_sent += 120                       # 只有標頭
            return 304, etag, None
        body = f"<table><tr><td>{path}</td><td>{self.version * 1000} kWh</td></tr></table>"
        self.bytes_sent += 120 + 48_000                  # 假設完整頁面約 48 KB
        return 200, etag, body


class Crawler:
    def __init__(self, robots_lines, server):
        self.rp = urllib.robotparser.RobotFileParser()
        self.rp.parse(robots_lines)
        self.server = server
        self.cache: dict[str, tuple[str, str]] = {}
        self.clock = 0.0                                  # 模擬時鐘（秒）
        self.next_allowed = 0.0

    def fetch(self, path):
        if not self.rp.can_fetch(UA, path):
            return f"{path}: robots.txt 不允許，跳過"
        delay = self.rp.crawl_delay(UA) or 1
        if self.clock < self.next_allowed:
            self.clock = self.next_allowed                # 等到允許的時間
        self.next_allowed = self.clock + delay
        etag = self.cache.get(path, (None, None))[0]
        status, new_etag, body = self.server.get(path, etag)
        if status == 200:
            self.cache[path] = (new_etag, body)
        return f"t={self.clock:>4.0f}s {path}: {status}{'（沿用快取）' if status == 304 else ''}"


if __name__ == "__main__":
    srv = FakeServer()
    c = Crawler(ROBOTS, srv)
    for p in ["/public/energy/2026-11", "/public/energy/2026-11", "/admin/users",
              "/public/energy/2026-10", "/search?q=kwh"]:
        print(c.fetch(p))
    srv.version = 2                                       # 伺服器資料更新
    print(c.fetch("/public/energy/2026-11"))
    print(f"總傳輸量約 {srv.bytes_sent / 1000:.1f} KB；若每次都完整下載約 {4 * 48.12:.1f} KB")
    print("請求時建議帶 User-Agent 與聯絡方式，例如：", f"{UA}/1.0 (+mailto:ops@example.com)")

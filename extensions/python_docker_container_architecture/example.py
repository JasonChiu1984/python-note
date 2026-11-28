"""產生多階段 Dockerfile 並做靜態檢查：非 root、辨識未以 digest 固定的基底、無秘密、層順序利於快取（標準函式庫）。"""
import re

DOCKERFILE = """\
FROM python:3.13-slim AS build
WORKDIR /src
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv export --frozen -o requirements.txt
COPY src ./src
RUN pip wheel --no-cache-dir -r requirements.txt -w /wheels && pip wheel --no-deps . -w /wheels

FROM python:3.13-slim
RUN useradd --create-home --uid 10001 app
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
USER app
HEALTHCHECK --interval=30s --timeout=3s CMD python -m bmsgateway.health || exit 1
ENTRYPOINT ["python", "-m", "bmsgateway"]
"""

BAD = """\
FROM python:latest
COPY . /app
RUN pip install -r /app/requirements.txt
ENV DB_PASSWORD=Bms2026
CMD python /app/main.py
"""


def lint(text):
    issues, lines = [], text.splitlines()
    froms = [l for l in lines if l.startswith("FROM")]
    if any(not re.search(r"@sha256:[0-9a-f]{64}(?:\s|$)", f) for f in froms):
        issues.append("基底映像未用 digest 固定（標籤可變動）")
    if not any(l.startswith("USER ") and "root" not in l for l in lines):
        issues.append("沒有切換為非 root 使用者")
    if not any(l.startswith("HEALTHCHECK") for l in lines):
        issues.append("沒有 HEALTHCHECK")
    if any(re.search(r"(PASSWORD|TOKEN|SECRET)=", l) for l in lines if l.startswith(("ENV", "ARG"))):
        issues.append("ENV/ARG 不應放秘密；可能出現在設定、歷史或建置證明")
    copy_all = next((i for i, l in enumerate(lines) if l.startswith("COPY . ")), None)
    install = next((i for i, l in enumerate(lines) if "pip install" in l), None)
    if copy_all is not None and install is not None and copy_all < install:
        issues.append("先 COPY 全部原始碼再安裝相依，任何程式改動都會讓安裝層快取失效")
    if any(l.startswith("CMD ") and not l.startswith("CMD [") for l in lines):
        issues.append("CMD 使用 shell 形式；確認 shell 會轉送 SIGTERM 或改用 exec 形式")
    return issues


if __name__ == "__main__":
    for name, text in (("多階段範本", DOCKERFILE), ("常見寫法", BAD)):
        found = lint(text)
        print(f"{name}：{'沒有發現問題' if not found else ''}")
        for i in found:
            print("  -", i)

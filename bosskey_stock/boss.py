"""老板模式 — 模拟 Docker build 日志"""

import random
from datetime import datetime

_PACKAGES = [
    "requests", "click", "pyyaml", "jinja2", "numpy",
    "pandas", "scipy", "flask", "fastapi", "psutil",
    "httpx", "orjson", "pydantic", "uvicorn", "celery",
]


class BossGenerator:
    """生成循环滚动的 Docker build 伪日志。"""

    def __init__(self):
        self._start = datetime.now()
        self._lines = self._build_log()

    def _build_log(self):
        lines = []
        total = random.randint(10, 20)
        for i in range(total):
            step = i + 1
            r = random.random()
            if r < 0.05:
                lines.append(
                    f"Step {step}/{total} : WARNING: package X has requirement Y, "
                    "but you'll have incompatible version Z"
                )
            elif r < 0.25:
                pkg = random.choice(_PACKAGES)
                ver = f"{random.randint(1,5)}.{random.randint(0,9)}.{random.randint(0,9)}"
                lines.append(
                    f"Step {step}/{total} : RUN pip install --no-cache-dir {pkg}=={ver}"
                )
            elif r < 0.4:
                lines.append(
                    f"Step {step}/{total} : RUN apt-get update && apt-get install -y "
                    f"{random.choice(['git', 'curl', 'vim', 'build-essential', 'libpq-dev'])}"
                )
            elif r < 0.6:
                lines.append(f"Step {step}/{total} : COPY . /app")
            elif r < 0.8:
                lines.append(f"Step {step}/{total} : WORKDIR /app")
            else:
                base = random.choice(["3.10", "3.11", "3.12"])
                lines.append(f"Step {step}/{total} : FROM python:{base}-slim")

        # 重复若干次供循环滚动
        return lines * 5

    def reset(self):
        self._start = datetime.now()
        self._lines = self._build_log()

    def render(self):
        elapsed = datetime.now() - self._start
        elapsed_str = f"{elapsed.seconds // 60:02d}:{elapsed.seconds % 60:02d}"
        # 每秒滚 2 行
        offset = (elapsed.seconds * 2) % len(self._lines)
        window = self._lines[offset : offset + 15]
        if len(window) < 15:
            window += self._lines[: 15 - len(window)]

        lines = [f"$ docker build -t app:latest ."]
        for l in window:
            lines.append(l)
        lines.append("")
        lines.append(f"Running time: {elapsed_str}")
        return "\n".join(lines)

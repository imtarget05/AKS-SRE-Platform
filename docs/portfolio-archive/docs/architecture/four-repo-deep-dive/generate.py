"""Generate the four-repo architecture boards as editable SVG files.

Run: python3 docs/architecture/four-repo-deep-dive/generate.py
The boards distinguish implemented boundaries from planned release gates.
"""

from html import escape
from pathlib import Path


OUT = Path(__file__).resolve().parent
W, H = 2400, 1350
INK = "#10263b"
MUTED = "#52677a"
LINE = "#bed0df"
BG = "#f4f8fc"
WHITE = "#ffffff"
RETAIL = "#2369c9"
OPS = "#c86426"
QUAN = "#178a70"
PLATFORM = "#6650aa"
AI = "#17879a"
RED = "#bf3f49"


class Svg:
    def __init__(self, title: str, description: str, width: int = W, height: int = H):
        self.width = width
        self.height = height
        self.items = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
            f"<title>{escape(title)}</title><desc>{escape(description)}</desc>",
            '<defs><filter id="shadow" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="8" stdDeviation="14" flood-color="#17344c" flood-opacity=".10"/></filter>',
            '<marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M2,2 L10,6 L2,10" fill="none" stroke="#71889b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></marker>',
            '<marker id="arrow-red" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M2,2 L10,6 L2,10" fill="none" stroke="#bf3f49" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></marker>',
            '</defs><style>text{font-family:Arial,Helvetica,sans-serif} .title{font-weight:700;letter-spacing:-1px} .label{font-weight:700} .eyebrow{font-weight:700;letter-spacing:2px}</style>',
        ]
        self.rect(0, 0, width, height, BG, radius=0)
        self.rect(0, 0, width, 18, INK, radius=0)

    def add(self, raw: str):
        self.items.append(raw)

    def rect(self, x, y, w, h, fill, stroke="none", radius=18, sw=2, dash=None, shadow=False):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        extra += ' filter="url(#shadow)"' if shadow else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>')

    def text(self, x, y, value, size=23, color=INK, weight=400, anchor="start", klass=""):
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}" class="{klass}">{escape(str(value))}</text>')

    def lines(self, x, y, values, size=22, color=MUTED, gap=30, weight=400):
        for i, value in enumerate(values):
            self.text(x, y + i * gap, value, size, color, weight)

    def rule(self, x1, y1, x2, y2, color=LINE, sw=2, dash=None, arrow=False, red=False):
        marker = ' marker-end="url(#arrow-red)"' if red else (' marker-end="url(#arrow)"' if arrow else "")
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"{d}{marker}/>')

    def path(self, d, color=LINE, sw=2, dash=None, arrow=False):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        extra += ' marker-end="url(#arrow)"' if arrow else ""
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"{extra}/>')

    def pill(self, x, y, label, fill, fg, w=None, h=38, size=17):
        w = w or (len(label) * size * 0.59 + 30)
        self.rect(x, y, w, h, fill, radius=h / 2, sw=0)
        self.text(x + w / 2, y + h / 2 + size * .35, label, size, fg, 700, "middle")
        return w

    def panel(self, x, y, w, h, accent, eyebrow, title, subtitle=None):
        self.rect(x, y, w, h, WHITE, "#dce6ef", 26, 2, shadow=True)
        self.rect(x, y, 12, h, accent, radius=6, sw=0)
        self.text(x + 40, y + 48, eyebrow, 19, accent, 700, klass="eyebrow")
        self.text(x + 40, y + 101, title, 35, INK, 700, klass="title")
        if subtitle:
            self.text(x + 40, y + 138, subtitle, 20, MUTED)

    def tile(self, x, y, w, h, title, detail, accent, fill="#f8fbfe", dashed=False, title_size=23):
        self.rect(x, y, w, h, fill, accent if dashed else "#d9e5ee", 15, 2, "8 6" if dashed else None)
        self.rect(x, y, 7, h, accent, radius=3, sw=0)
        self.text(x + 22, y + 36, title, title_size, INK, 700)
        if isinstance(detail, str):
            detail = [detail]
        self.lines(x + 22, y + 69, detail, 19, MUTED, 25)

    def header(self, number, title, subtitle):
        self.text(60, 75, f"ARCHITECTURE  /  {number}", 19, PLATFORM, 700, klass="eyebrow")
        self.text(60, 139, title, 52, INK, 700, klass="title")
        self.text(62, 181, subtitle, 23, MUTED)
        self.rule(60, 207, 2340, 207, "#d2dfe9", 2)

    def footer(self, text):
        self.rule(60, 1300, 2340, 1300, "#d2dfe9", 2)
        self.text(60, 1330, text, 17, MUTED)
        self.text(2340, 1330, "Senior Engineering Portfolio  •  2026-10-24", 17, MUTED, anchor="end")

    def write(self, filename):
        self.add("</svg>")
        (OUT / filename).write_text("\n".join(self.items) + "\n", encoding="utf-8")


def landscape():
    s = Svg("Four repository architecture and data ownership", "Three business bounded contexts, a shared platform, and a read-only Agent Hub with explicit truth and authority boundaries.")
    s.header("01", "Bốn repo · một kiến trúc có ranh giới", "Mỗi domain giữ dữ liệu chuẩn và quyền ghi của mình; platform triển khai, Agent Hub chỉ điều tra.")

    cols = [(60, RETAIL, "RETAIL FINANCE", "Java 17 / Spring Boot", "Ledger & đối soát"),
            (840, OPS, "OPSBRIDGE / FLASHSALE", ".NET 10 / C#", "Đơn hàng, tồn và vận hành"),
            (1620, QUAN, "QUẢN LÝ KHO", "Python 3.11 / FastAPI", "Lô hàng, FEFO và duyệt phiếu")]
    for x, accent, eye, tech, title in cols:
        s.panel(x, 236, 720, 770, accent, eye, title, tech)

    # Retail: balance and ledger changes are inside one MySQL transaction.
    x = 60
    s.tile(x + 35, 410, 650, 82, "POS / staff / partner statement", ["JWT + outlet scope; dữ liệu đối soát"], RETAIL)
    s.tile(x + 35, 523, 650, 94, "Spring API + service boundary", ["Auth theo object · idempotency · audit"], RETAIL)
    s.tile(x + 35, 648, 650, 112, "MySQL · nguồn sự thật ledger", ["Account + transaction + balance commit", "Một lỗi giữa chừng → rollback toàn bộ"], RETAIL, "#edf5ff")
    s.tile(x + 35, 791, 650, 108, "Python reconciliation", ["So khớp settled feed và partner input", "Kết quả điều tra không tự ghi tiền"], RETAIL)
    for y1, y2 in [(492, 523), (617, 648), (760, 791)]: s.rule(x + 360, y1, x + 360, y2 - 7, RETAIL, 3, arrow=True)
    s.pill(x + 35, 929, "Kafka / RabbitMQ / Redis: CHƯA ở core path", "#fff4e9", OPS, 645, 42, 18)

    # OpsBridge and FlashSale remain separate contexts and databases.
    x = 840
    s.tile(x + 35, 410, 650, 82, "Khách đặt hàng / FactoryFlow webhook", ["Hai contract; không ghi chéo DB"], OPS)
    s.tile(x + 35, 523, 305, 96, "FlashSale Order API", ["Reserve; xử lý đơn"], OPS)
    s.tile(x + 380, 523, 305, 96, "OpsBridge API", ["Ingest; reconcile"], OPS)
    s.tile(x + 35, 651, 305, 110, "Redis + RabbitMQ", ["Fast-fail; at-least-once", "Retry / DLQ / idempotency"], OPS, "#fff7f0")
    s.tile(x + 380, 651, 305, 110, "Inbox + outbox", ["Webhook → commit → publish", "Broker down: outbox pending"], OPS, "#fff7f0")
    s.tile(x + 35, 793, 305, 104, "PostgreSQL FlashSale", ["Stock / order / payment", "SOURCE OF TRUTH"], OPS)
    s.tile(x + 380, 793, 305, 104, "PostgreSQL OpsBridge", ["Supplier recon / staff review", "OWNED DB"], OPS)
    s.rule(x + 355, 515, x + 355, 905, "#b7c9d8", 2, "9 7")
    s.rule(x + 185, 619, x + 185, 645, OPS, 3, arrow=True)
    s.rule(x + 530, 619, x + 530, 645, OPS, 3, arrow=True)
    s.rule(x + 185, 761, x + 185, 787, OPS, 3, arrow=True)
    s.rule(x + 530, 761, x + 530, 787, OPS, 3, arrow=True)
    s.pill(x + 35, 929, "Versioned contract · không truy vấn chéo bảng", "#fff4e9", OPS, 650, 42, 18)

    # Warehouse; AI is only an input to a human decision.
    x = 1620
    s.tile(x + 35, 410, 650, 82, "Flutter / warehouse staff", ["Maker, checker và branch scope"], QUAN)
    s.tile(x + 35, 523, 650, 94, "FastAPI · canonical API", ["Xác thực + kiểm quyền branch/location"], QUAN)
    s.tile(x + 35, 648, 305, 112, "Inventory service", ["Nhập lô · FEFO", "Kiểm kê · movement"], QUAN, "#edf9f4")
    s.tile(x + 380, 648, 305, 112, "Maker → checker", ["AI risk: advisory only", "Checker duyệt có quyền"], QUAN, "#edf9f4")
    s.tile(x + 35, 791, 650, 108, "PostgreSQL · nguồn sự thật tồn kho", ["Voucher + balance + audit / outbox", "Approval chỉ post một lần"], QUAN)
    s.rule(x + 360, 492, x + 360, 517, QUAN, 3, arrow=True)
    s.path(f"M{x+360} 617 V632 H{x+185} V643", QUAN, 3, arrow=True)
    s.path(f"M{x+360} 617 V632 H{x+530} V643", QUAN, 3, arrow=True)
    s.rule(x + 185, 760, x + 185, 785, QUAN, 3, arrow=True)
    s.rule(x + 530, 760, x + 530, 785, QUAN, 3, arrow=True)
    s.pill(x + 35, 929, "AI không tự approve / ghi tồn", "#e8f7f3", QUAN, 650, 42, 18)

    # Shared, distinct planes. Dashed hub edge means contract/WIP, not production integration.
    s.panel(60, 1040, 1090, 228, AI, "INVESTIGATION PLANE · WIP", "Agent Hub: chứng cứ → đề xuất", "Read adapters có scope · verifier deterministic · trích nguồn · human decision")
    s.tile(98, 1194, 1000, 52, "READ-ONLY · không có tool post ledger, approve kho hoặc kubectl apply", [], AI, "#e9f7f8", title_size=20)
    s.panel(1190, 1040, 1150, 228, PLATFORM, "PLATFORM PLANE · KIND VERIFIED", "AKS-SRE-Platform: golden path", "Terraform/OIDC · Argo CD · Envoy Gateway · policy · observability · backup")
    s.tile(1228, 1194, 1070, 52, "Kind: FlashSale + Quan Synced/Healthy  |  Azure runtime: PARTIAL", [], PLATFORM, "#f2effa", title_size=20)
    s.footer("Nguồn sự thật = database của domain. Đường nét đứt / WIP là hợp đồng hoặc gate chưa chứng minh runtime.")
    s.write("01-system-landscape.svg")


def flow_row(s, y, color, label, subtitle, steps, failure, gate):
    s.rect(60, y, 2280, 300, WHITE, "#dce6ef", 24, 2, shadow=True)
    s.rect(60, y, 12, 300, color, radius=6, sw=0)
    s.text(98, y + 43, label, 29, color, 700)
    s.text(98, y + 78, subtitle, 20, MUTED)
    start, gap, width = 98, 28, 420
    for i, (title, detail) in enumerate(steps):
        xx = start + i * (width + gap)
        s.tile(xx, y + 104, width, 99, title, detail, color, "#f8fbfd", title_size=21)
        if i < 4:
            s.rule(xx + width + 2, y + 153, xx + width + gap - 7, y + 153, color, 3, arrow=True)
    s.rect(98, y + 226, 1740, 51, "#fff5f4", radius=12, sw=0)
    s.text(118, y + 259, failure, 19, RED, 700)
    s.pill(1860, y + 231, gate, "#e9f1fb", color, 444, 41, 17)


def transaction_flows():
    s = Svg("Transactions, invariants, and failure recovery", "Three end-to-end flows show where business invariants are enforced and what remains to prove under failure.")
    s.header("02", "Giao dịch đúng khi retry, cạnh tranh và lỗi", "Đường liền: luồng nghiệp vụ; dải đỏ: trạng thái phải kiểm sau fault injection.")
    flow_row(s, 239, RETAIL, "01  RETAIL FINANCE · không double-post", "Tiền chỉ đổi sau một commit MySQL; outlet được kiểm ở service/query boundary.", [
        ("Request + key", ["POS / outlet / payload"]),
        ("Auth + scope", ["JWT → account outlet"]),
        ("TX boundary", ["Account / posting / audit"]),
        ("MySQL commit", ["Unique key + balance"]),
        ("Reconcile", ["Settled feed ↔ partner"]),
    ], "FAIL giữa các write → rollback; retry cùng key → cùng effect; khác payload → conflict.", "MySQL IT · CI GREEN")
    flow_row(s, 565, OPS, "02  FLASHSALE · không oversell", "OpsBridge nhận contract riêng; không ghi trực tiếp stock / order của FlashSale.", [
        ("50 khách / 10 suất", ["Order API + reserve outbox"]),
        ("Redis fast-fail", ["Lua reserve; không là truth"]),
        ("RabbitMQ", ["At-least-once; retry / DLQ"]),
        ("Worker + outbox", ["Order/event cùng DB TX"]),
        ("PostgreSQL", ["Atomic stock + order"]),
    ], "QUEUE/WORKER lỗi → kiểm reserve, DB, redelivery và DLQ; 50/10 cần 10/40/0 ở DB.", "CI + k6 · FAULT GATE")
    flow_row(s, 891, QUAN, "03  QUẢN LÝ KHO · không duyệt sai lô / chi nhánh", "AI chỉ phân tích phiếu canonical; checker có quyền mới tạo effect.", [
        ("Nhập lô / phiếu", ["Flutter → FastAPI"]),
        ("Branch guard", ["Scope + canonical voucher"]),
        ("Rules", ["FEFO / kiểm kê / variance"]),
        ("Human checker", ["Maker ≠ checker; AI advice"]),
        ("PostgreSQL", ["Movement + balance + audit"]),
    ], "REPLAY / 2 checker / AI timeout → một lần post; fallback rule; không truy cập chéo branch.", "DB JOURNEY · CI GREEN")
    s.footer("Các nhãn gate mô tả bằng chứng theo repo; fault matrix Ops và live cloud cần đối chiếu artifact exact-SHA trước khi claim.")
    s.write("02-transaction-and-failure-flows.svg")


def platform():
    s = Svg("Platform golden path and SRE recovery", "A release path from source to cluster with explicit cloud safety gates, observability, rollback, and measured recovery limits.")
    s.header("03", "Platform engineering · release và vận hành", "Một golden path dùng lại cho FlashSale và QuanLyKho; trạng thái Kind và Azure được tách rõ.")

    stages = [
        (60, "01  SOURCE + CI", "Workload owns", ["Code / migration / probes", "DB integration · k6 · policy", "Exact SHA + raw evidence"]),
        (650, "02  RELEASE CONTRACT", "Gate còn mở", ["Digest pinning: cần proof", "Quan migration: verified Kind", "Rollback exact ref: cần proof"]),
        (1240, "03  GITOPS CONTROL", "Platform owns", ["Argo AppProject / ref", "Namespace / policy", "Sync, drift, health gate"]),
        (1830, "04  RUNTIME", "Platform + workload", ["Envoy Gateway route", "FlashSale + Quan pods", "DB truth + business metrics"]),
    ]
    for x, title, owner, lines in stages:
        s.rect(x, 257, 510, 279, WHITE, "#dce6ef", 23, 2, "10 7" if x == 650 else None, shadow=True)
        s.rect(x, 257, 510, 12, PLATFORM, radius=6, sw=0)
        s.text(x + 29, 314, title, 27, PLATFORM, 700)
        s.text(x + 29, 350, owner, 19, MUTED, 700)
        s.rule(x + 29, 373, x + 480, 373, "#dce6ef")
        for j, line in enumerate(lines):
            s.text(x + 29, 415 + j * 37, "•  " + line, 21, INK)
    for x in (570, 1160, 1750): s.rule(x, 397, x + 73, 397, PLATFORM, 4, "9 7" if x in (570, 1160) else None, arrow=True)

    # Release safety and operations are lateral controls, not magical boxes in the request path.
    s.panel(60, 581, 700, 370, PLATFORM, "FOUNDATION + CHANGE SAFETY", "Terraform / OIDC / state", "Cloud apply requires a reviewed saved plan and protected environment")
    s.lines(100, 756, ["• State owner, subscription, quota and budget", "• Workload identity; no long-lived secret shortcut", "• Policy: non-root, limits, namespace, route", "• Push to main does not authorize cloud apply"], 21, INK, 37)

    s.panel(850, 581, 700, 370, PLATFORM, "OBSERVE + RESPOND", "Signals → SLO → on-call", "Prometheus / Grafana / alert rules are configuration, not an SLO proof")
    s.lines(890, 756, ["• API p95, errors; durable order / approval", "• Alert fire + resolve; trace to business ID", "• Runbook links to exact release and dashboard", "• Rollback checks data, not only pod health"], 21, INK, 37)

    s.panel(1640, 581, 700, 370, PLATFORM, "BACKUP + RECOVER", "Restore is a data decision", "Kind snapshot drill measured a five-order post-snapshot loss")
    s.lines(1680, 756, ["• Restore to isolated DB; verify invariant", "• RTO 0.787 s in a local synthetic drill", "• RPO: 5 delta orders lost / 4 s window", "• WAL / PITR needed for lower data loss"], 21, INK, 37)

    s.rect(60, 997, 1090, 268, "#eaf7f1", "#b8dfcb", 23, 2)
    s.pill(98, 1027, "KIND · DEMONSTRATED", "#d0efdd", "#126c50", 352, 42, 20)
    s.text(98, 1103, "FlashSale + Quan: Argo Synced / Healthy", 27, INK, 700)
    s.lines(98, 1143, ["Envoy host routing + Alembic migration được ghi trong STATUS.", "Drill là local synthetic; không suy ra SLA khách hàng."], 21, MUTED, 32)

    s.rect(1190, 997, 1150, 268, "#fff1e8", "#f0cbb6", 23, 2)
    s.pill(1228, 1027, "AZURE AKS · PARTIAL", "#f9dec7", "#9b4c20", 350, 42, 20)
    s.text(1228, 1103, "Cluster evidence ≠ ứng dụng production ready", 27, INK, 700)
    s.lines(1228, 1143, ["OIDC / bootstrap và GitOps runtime còn gate chưa đóng.", "Cần ACR pull, Argo sync, rollout, rollback, restore và cost."], 21, MUTED, 32)
    s.footer("Solid = đã có local/Kind evidence được ghi; Azure partial và SLO/DR production cần gate riêng, exact SHA và môi trường.")
    s.write("03-platform-and-sre.svg")


def agent_hub():
    s = Svg("Agent Hub trust and evidence architecture", "Read-only investigation design with per-domain authorization, evidence provenance, deterministic verification, abstention, and a human decision boundary. This remains work in progress.")
    s.header("04", "Agent Hub · AI chỉ điều tra, con người quyết định", "Contract thiết kế theo ADR 023; kết nối runtime toàn bộ bốn nguồn chưa được chứng minh.")

    s.panel(60, 247, 610, 718, AI, "SOURCES · OWNER RECHECKS AUTH", "Đọc qua API có scope", "Không có đường đọc raw DB chéo domain")
    sources = [
        (RETAIL, "Retail Finance", "Settled feed · outlet scope"),
        (OPS, "FlashSale / OpsBridge", "Order timeline · outbox / DLQ"),
        (QUAN, "QuanLyKho", "Canonical voucher · branch scope"),
        (PLATFORM, "AKS-SRE-Platform", "Alert · Argo status · runbook"),
    ]
    for i, (accent, title, detail) in enumerate(sources):
        y = 429 + i * 113
        s.tile(96, y, 538, 89, title, [detail], accent, "#f7fbfd", title_size=23)
    s.pill(96, 894, "Allowlist GET · 401/403/404 từ nguồn", "#e7f5f8", AI, 538, 42, 18)

    s.panel(736, 247, 925, 718, AI, "INVESTIGATION PIPELINE · WIP", "Chứng cứ trước, suy luận sau", "Hub DB chỉ lưu runs, evidence, quyết định và audit")
    pipe = [
        ("01  Identity + scope", "Danh tính từ server; không tin client scope"),
        ("02  Evidence envelope", "service · entity · version · SHA-256 · expiry"),
        ("03  Deterministic verifier", "Ledger / stock / FEFO / maker-checker invariants"),
        ("04  Critic + proposal", "Citation đủ → đề xuất; thiếu → abstain"),
    ]
    for i, (title, detail) in enumerate(pipe):
        y = 427 + i * 116
        s.tile(775, y, 846, 88, title, [detail], AI, "#f0fafb", title_size=23)
        if i < 3: s.rule(1198, y + 89, 1198, y + 111, AI, 3, arrow=True)
    s.pill(775, 906, "Token, scope và evidence hash gắn cùng một investigation run", "#e7f5f8", AI, 846, 41, 18)

    s.panel(1727, 247, 613, 718, RED, "AUTHORITY BOUNDARY", "Không tự thực thi", "Người có thẩm quyền dùng hệ thống sở hữu action")
    s.tile(1764, 429, 538, 100, "Proposal + unknowns", ["Read-only checks; source citations"], AI, "#f0fafb")
    s.rule(2033, 530, 2033, 571, AI, 3, arrow=True)
    s.tile(1764, 577, 538, 104, "Human decision", ["Accept / reject giả thuyết", "Run được ghi nhận, không đổi dữ liệu"], AI, "#f0fafb")
    s.rule(2033, 682, 2033, 723, RED, 3, arrow=True, red=True)
    s.tile(1764, 730, 538, 114, "Owner UI / CLI", ["Người có quyền thực hiện tại domain", "Theo policy, audit và approval riêng"], RED, "#fff3f2")
    s.pill(1764, 894, "HUB WRITE TOOL = FORBIDDEN", "#fff1ef", RED, 538, 42, 18)

    s.path("M670 605 H730", AI, 4, "9 7", arrow=True)
    s.path("M1661 605 H1720", AI, 4, "9 7", arrow=True)

    s.rect(60, 1005, 2280, 261, WHITE, "#dce6ef", 22, 2)
    s.text(96, 1054, "Khi thiếu bằng chứng hoặc source từ chối", 29, RED, 700)
    s.lines(96, 1096, ["Cross-scope → 403/404. Tool timeout / source conflict / không có citation → abstained + unknowns.",
                      "Agent Hub hiện là WIP trong monorepo; demo Kind và test synthetic không chứng minh tích hợp production."], 22, INK, 38)
    s.pill(96, 1194, "Không gắn nhãn PRODUCTION READY", "#fff1ef", RED, 453, 42, 18)
    s.footer("Ranh giới đọc/ghi là policy tại domain service. Đường nét đứt là contract WIP, không phải luồng production đã chạy.")
    s.write("04-agent-hub-governance.svg")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    landscape()
    transaction_flows()
    platform()
    agent_hub()
    print("Generated 4 SVG architecture boards in", OUT)

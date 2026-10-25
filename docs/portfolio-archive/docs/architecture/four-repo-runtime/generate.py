"""Generate the canonical runtime-flow and approved-Agent execution diagrams.

Run from any directory: python3 docs/architecture/four-repo-runtime/generate.py
"""

import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "four-repo-deep-dive"))
import generate as base  # noqa: E402
from generate import AI, BG, INK, LINE, MUTED, OPS, PLATFORM, QUAN, RED, RETAIL, Svg  # noqa: E402

base.OUT = HERE


W, H = 2800, 1700


def heading(s, eyebrow, title, subtitle):
    s.text(70, 70, eyebrow, 20, PLATFORM, 700, klass="eyebrow")
    s.text(70, 138, title, 57, INK, 700, klass="title")
    s.text(72, 184, subtitle, 24, MUTED)
    s.rule(70, 213, W - 70, 213, "#c9d9e5", 2)


def node(s, x, y, w, h, title, details, color, fill="#fff", title_size=25):
    s.rect(x, y, w, h, fill, "#d6e2eb", 17, 2)
    s.rect(x, y, 8, h, color, radius=4, sw=0)
    s.text(x + 23, y + 37, title, title_size, INK, 700)
    if isinstance(details, str):
        details = [details]
    for i, detail in enumerate(details):
        s.text(x + 23, y + 70 + i * 28, detail, 20, MUTED)


def lane(s, y, color, title, subtitle):
    s.rect(60, y, 2680, 232, "#ffffff", "#dce6ef", 23, 2)
    s.rect(60, y, 13, 232, color, radius=6, sw=0)
    s.text(91, y + 44, title, 28, color, 700)
    s.text(704, y + 44, subtitle, 21, MUTED)


def hop(s, x1, x2, y, color):
    s.rule(x1, y, x2 - 9, y, color, 4, arrow=True)


def runtime_topology():
    s = Svg(
        "Four-repository end-to-end runtime topology",
        "A horizontal flow map of client requests, service-owned processing, databases, outcomes, shared platform and the proposed approval-gated Agent executor.",
        W, H,
    )
    heading(s, "SYSTEM FLOW / 01", "Luồng hệ thống: request → xử lý → dữ liệu → kết quả", "Bốn repo, bốn ranh giới ghi. Mũi tên liền là runtime domain; nhánh Agent được đánh dấu target.")

    # Column labels align all four real business flows.
    for x, name in [(85, "ACTOR / SOURCE"), (490, "API + AUTH"), (970, "BUSINESS / ASYNC"), (1870, "SYSTEM OF RECORD"), (2360, "RESULT / PROJECTION")]:
        s.text(x, 249, name, 17, MUTED, 700, klass="eyebrow")

    rows = [
        (270, RETAIL, "RETAIL FINANCE", "Giao dịch tiền và đối soát theo outlet"),
        (523, OPS, "FLASHSALE", "Bán hữu hạn dưới tải · đơn và tồn chuẩn thuộc PostgreSQL"),
        (776, OPS, "OPSBRIDGE", "Webhooks / supplier reconciliation · DB riêng, contract versioned"),
        (1029, QUAN, "QUẢN LÝ KHO", "Nhập lô → FEFO → kiểm kê → checker; AI tư vấn"),
    ]
    for y, c, title, subtitle in rows:
        lane(s, y, c, title, subtitle)

    # Retail lane.
    y = 343
    node(s, 85, y, 310, 126, "POS / partner", ["JWT user; settlement file", "outlet cụ thể"], RETAIL, "#f4f9ff")
    node(s, 490, y, 380, 126, "Spring Boot API", ["Object-level outlet guard", "Idempotency key"], RETAIL, "#f4f9ff")
    node(s, 970, y, 790, 126, "Ledger transaction", ["Account + posting + balance + audit", "Một MySQL commit hoặc rollback"], RETAIL, "#edf5ff")
    node(s, 1870, y, 390, 126, "MySQL ledger", ["Nguồn sự thật tiền", "Unique key / version"], RETAIL, "#e8f2ff")
    node(s, 2360, y, 350, 126, "Python recon", ["Settled feed ↔ partner", "Exception / audit"], RETAIL, "#f4f9ff")
    for a, b in [(395, 490), (870, 970), (1760, 1870), (2260, 2360)]: hop(s, a, b, y + 63, RETAIL)

    # FlashSale order path: Redis and broker are transport/gates, PG is authoritative.
    y = 596
    node(s, 85, y, 310, 126, "Khách mua", ["50 request / 10 suất", "Synthetic load case"], OPS, "#fff8f2")
    node(s, 490, y, 380, 126, "Order API", ["Auth + request key", "Reserve event/outbox"], OPS, "#fff8f2")
    node(s, 970, y, 240, 126, "Redis", ["Lua fast-fail", "Không là truth"], OPS, "#fff3e9")
    node(s, 1243, y, 240, 126, "RabbitMQ", ["At-least-once", "Retry / DLQ"], OPS, "#fff3e9")
    node(s, 1516, y, 244, 126, "Order Worker", ["Idempotent", "ACK sau DB"], OPS, "#fff3e9")
    node(s, 1870, y, 390, 126, "PostgreSQL", ["Atomic stock + order", "Business outbox"], OPS, "#ffeddf")
    node(s, 2360, y, 350, 126, "Durable result", ["10 order / 40 reject", "Stock = 0 (CI case)"], OPS, "#fff8f2")
    for a, b in [(395, 490), (870, 970), (1210, 1243), (1483, 1516), (1760, 1870), (2260, 2360)]: hop(s, a, b, y + 63, OPS)

    # Separate OpsBridge bounded context and database.
    y = 849
    node(s, 85, y, 310, 126, "FactoryFlow", ["Signed webhook", "Event ID + schema"], OPS, "#fff8f2")
    node(s, 490, y, 380, 126, "OpsBridge API", ["HMAC + staff RBAC", "No FlashSale DB write"], OPS, "#fff8f2")
    node(s, 970, y, 790, 126, "Atomic webhook ingest", ["Validate contract; inbox + event + outbox", "Một PostgreSQL transaction trước HTTP 202"], OPS, "#fff3e9")
    node(s, 1870, y, 390, 126, "PostgreSQL riêng", ["Committed event/outbox", "Supplier reconciliation"], OPS, "#ffeddf")
    node(s, 2360, y, 350, 126, "Publish → review", ["RabbitMQ / DLQ", "Staff replay có audit"], OPS, "#fff8f2")
    for a, b in [(395, 490), (870, 970), (1760, 1870), (2260, 2360)]: hop(s, a, b, y + 63, OPS)

    # Warehouse lane.
    y = 1102
    node(s, 85, y, 310, 126, "Flutter staff", ["Maker / checker", "Branch assignment"], QUAN, "#f1faf6")
    node(s, 490, y, 380, 126, "FastAPI canonical", ["Branch + location guard", "Canonical voucher ID"], QUAN, "#f1faf6")
    node(s, 970, y, 790, 126, "Inventory + approval policy", ["FEFO, stocktake, maker ≠ checker", "AI score chỉ hỗ trợ quyết định"], QUAN, "#e9f8f1")
    node(s, 1870, y, 390, 126, "PostgreSQL", ["Voucher + balance", "Movement + audit/outbox"], QUAN, "#def4e9")
    node(s, 2360, y, 350, 126, "Posted stock", ["Một approval → một effect", "Trace theo branch"], QUAN, "#f1faf6")
    for a, b in [(395, 490), (870, 970), (1760, 1870), (2260, 2360)]: hop(s, a, b, y + 63, QUAN)

    # Control plane with observed Kind scope and the new Agent execution target.
    s.rule(60, 1288, 2740, 1288, "#c9d9e5", 2)
    s.text(70, 1331, "SHARED CONTROL PLANE", 19, PLATFORM, 700, klass="eyebrow")
    node(s, 70, 1361, 660, 214, "AKS-SRE-Platform · release", ["CI → image / migration → Argo CD", "Envoy Gateway routes FlashSale + Quan", "Kind proof; Azure app runtime partial"], PLATFORM, "#f3effa", 27)
    node(s, 800, 1361, 670, 214, "SRE · observe and recover", ["Prometheus / Grafana / alerts / runbooks", "Rollback + restore need exact revision/data check", "DR synthetic RPO: 5 delta orders lost"], PLATFORM, "#f3effa", 27)
    node(s, 1540, 1361, 1160, 214, "Agent Hub · APPROVED EXECUTION (ADR 024 TARGET)", ["Read evidence → proposed typed action → policy → human approval", "Agent executor → owner command API / Argo → verify post-state + receipt", "Current Hub remains read-only: execution gate NOT IMPLEMENTED"], AI, "#e7f7f8", 27)
    hop(s, 730, 800, 1468, PLATFORM)
    s.rule(1470, 1468, 1530, 1468, AI, 4, "10 7", arrow=True)
    s.pill(70, 1612, "SOLID = DOMAIN CODE PATH · RUNTIME SEE STATUS", "#e5eef7", RETAIL, 600, 40, 18)
    s.pill(696, 1612, "DASHED = AGENT EXECUTION TARGET", "#dff3f5", AI, 626, 40, 18)
    s.text(2730, 1642, "No cross-database writes · no production readiness claim", 18, MUTED, anchor="end")
    s.write("01-end-to-end-runtime-flow.svg")


def actor(s, x, label, color, subtitle):
    s.rect(x - 170, 273, 340, 108, "#fff", "#d7e4ed", 18, 2)
    s.rect(x - 170, 273, 340, 9, color, radius=4, sw=0)
    s.text(x, 319, label, 23, INK, 700, "middle")
    s.text(x, 351, subtitle, 18, MUTED, anchor="middle")
    s.rule(x, 381, x, 1241, "#b9cbd9", 2, "8 8")


def seq(s, y, x1, x2, label, color, reply=False):
    s.text((x1 + x2) / 2, y - 16, label, 21, color, 700, "middle")
    s.rule(x1, y, x2 - 11 if x2 > x1 else x2 + 11, y, color, 4, arrow=not reply)
    if reply:
        # For leftward response arrows draw a small matching arrowhead.
        s.add(f'<path d="M{x2+10},{y-8} L{x2},{y} L{x2+10},{y+8}" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round"/>')


def approved_execution():
    s = Svg(
        "Approval-gated Agent execution sequence",
        "Agent Hub proposes a typed action, receives a human approval bound to the exact intent, executes through a scoped owner API, and verifies the durable post-state.",
        W, H,
    )
    heading(s, "CONTROL FLOW / 02", "Agent có quyền thực thi — sau Human in the Loop", "Agent executor là thành phần có quyền hẹp; domain API và Argo kiểm tra lại trước khi đổi trạng thái.")

    people = [
        (215, "Operator / SRE", RETAIL, "trigger + approve"),
        (670, "Agent planner", AI, "evidence + intent"),
        (1125, "Policy engine", PLATFORM, "risk + scope"),
        (1580, "Approval service", OPS, "HITL + signed decision"),
        (2035, "Agent executor", AI, "scoped execution"),
        (2490, "Owner API / Argo", QUAN, "authoritative effect"),
    ]
    for x, name, color, subtitle in people:
        actor(s, x, name, color, subtitle)
    s.pill(2025, 225, "REJECT / EXPIRE / STALE → STOP", "#ffebe6", RED, 705, 38, 18)

    # Numbered sequence is deliberately linear until the owner command: approval is a gate,
    # not a later audit step. The owner returns a durable receipt, then Agent verifies it.
    seq(s, 425, 235, 650, "1  sự cố / task", RETAIL)
    seq(s, 518, 690, 2470, "2  GET evidence có scope + source version", AI)
    seq(s, 611, 690, 1105, "3  typed ActionIntent + hash", AI)
    seq(s, 704, 1145, 1560, "4  policy: role / scope / risk", PLATFORM)
    seq(s, 797, 1560, 235, "5  exact diff + impact + expiry", OPS, reply=True)
    seq(s, 890, 235, 1560, "6  APPROVE / REJECT · MFA · maker ≠ checker", OPS)
    seq(s, 983, 1600, 2015, "7  signed approval bound to intent hash", AI)
    seq(s, 1076, 2055, 2470, "8  command API · short-lived ID · idempotency", AI)
    seq(s, 1169, 2470, 2055, "9  durable receipt / version / audit", QUAN, reply=True)
    seq(s, 1257, 2015, 690, "10  re-read owner state → VERIFIED / UNKNOWN", AI, reply=True)

    # Two enforcement points and an approval-failure branch make the authority explicit.
    s.rect(77, 1300, 2646, 274, "#fff", "#dce6ef", 21, 2)
    s.text(112, 1354, "Command catalog: Agent thực thi hành động cụ thể, không chạy shell/SQL tùy ý", 30, INK, 700)
    catalog = [
        (RETAIL, "Retail", "Run recon; post adjustment", "chỉ sau dual control tại ledger"),
        (OPS, "OpsBridge", "Replay một DLQ event", "owner RBAC + audit + idempotency"),
        (QUAN, "QuanLyKho", "Post approved voucher", "branch + maker/checker + version"),
        (PLATFORM, "Platform", "Argo rollback một app", "revision + env gate + health"),
    ]
    for i, (color, domain, action, gate) in enumerate(catalog):
        x = 112 + i * 645
        s.rect(x, 1393, 607, 139, "#f7fbfd", "#dce6ef", 13, 2)
        s.rect(x, 1393, 8, 139, color, radius=4, sw=0)
        s.text(x + 23, 1431, domain, 23, color, 700)
        s.text(x + 23, 1472, action, 21, INK, 700)
        s.text(x + 23, 1505, gate, 18, MUTED)

    s.pill(77, 1605, "TARGET DESIGN · CURRENT AGENT HUB READ-ONLY", "#ffebe6", RED, 755, 45, 19)
    s.text(2722, 1637, "ADR 024 · implement/verify từng command family trước khi claim", 19, MUTED, anchor="end")
    s.write("02-agent-approved-execution.svg")


if __name__ == "__main__":
    HERE.mkdir(parents=True, exist_ok=True)
    runtime_topology()
    approved_execution()
    print("Generated 2 runtime-flow SVGs in", HERE)

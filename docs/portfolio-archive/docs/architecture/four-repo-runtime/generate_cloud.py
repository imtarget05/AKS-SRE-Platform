"""Render the observed Cloudflare/Azure split and the gated hybrid target."""

import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "four-repo-deep-dive"))
import generate as base  # noqa: E402

base.OUT = HERE
Svg = base.Svg
INK, MUTED, RETAIL, OPS, QUAN, PLATFORM, AI, RED = (
    base.INK, base.MUTED, base.RETAIL, base.OPS, base.QUAN, base.PLATFORM, base.AI, base.RED
)
CF = "#dc6b20"
AZ = "#1681bd"
W, H = 2800, 1700


def title(s, index, name, subtitle):
    s.text(65, 74, f"HYBRID ARCHITECTURE  /  {index}", 20, PLATFORM, 700, klass="eyebrow")
    s.text(65, 145, name, 57, INK, 700, klass="title")
    s.text(67, 191, subtitle, 24, MUTED)
    s.rule(65, 218, W - 65, 218, "#cbdbe6", 2)


def node(s, x, y, w, h, heading, lines, accent, fill="#ffffff", dashed=False, size=24):
    s.rect(x, y, w, h, fill, "#d8e3eb", 17, 2, "10 7" if dashed else None)
    s.rect(x, y, 8, h, accent, radius=4, sw=0)
    s.text(x + 24, y + 37, heading, size, INK, 700)
    for i, line in enumerate(lines):
        s.text(x + 24, y + 73 + 29 * i, line, 20, MUTED)


def arrow(s, x1, y1, x2, y2, color, dashed=False, red=False):
    s.rule(x1, y1, x2, y2, color, 4, "10 8" if dashed else None, arrow=True, red=red)


def as_is():
    s = Svg("Cloudflare and Azure observed state", "Public Cloudflare frontend and API proxy are separate from a live Azure AKS control plane. The business path to Modal is failing and no Cloudflare-to-AKS route exists.", W, H)
    title(s, "03 / AS-IS", "Cloudflare và Azure: hiện trạng quan sát được", "Read-only check 2026-10-24 18:44 ICT. Không nối hai cloud thành một runtime khi đường mạng chưa tồn tại.")

    s.panel(60, 266, 870, 1060, CF, "CLOUDFLARE EDGE", "Web hoạt động, API chưa chứng minh", "Hai đường yêu cầu tách biệt: tải giao diện và gọi API")
    node(s, 97, 579, 277, 135, "Người dùng", ["Browser / Flutter Web", "gửi request nghiệp vụ"], CF, "#fff8f0")
    node(s, 459, 477, 429, 150, "Workers Assets", ["Flutter Web static: HTTP 200", "version.json: eb446f8"], CF, "#fff2e5")
    node(s, 459, 710, 429, 180, "API Worker proxy", ["Root báo upstream configured", "Health local 200 ≠ origin ready", "Business API: timeout hôm nay"], CF, "#fff2e5")
    s.path("M374 615 H412 V552 H451", CF, 4, arrow=True)
    s.path("M374 676 H412 V800 H451", CF, 4, arrow=True)
    s.pill(97, 979, "OpsBridge Web: Pages config, deploy chưa verify", "#fff1e5", CF, 790, 48, 18)
    s.pill(97, 1044, "Workers AI / R2 / Access: thiết kế hoặc config", "#fff1e5", CF, 790, 48, 18)
    s.text(97, 1170, "Cloudflare Tunnel có YAML trong Quan base,", 21, MUTED)
    s.text(97, 1204, "nhưng overlay Argo local không chọn manifest đó.", 21, MUTED)

    s.panel(1000, 266, 790, 1060, RED, "DOCUMENTED ORIGIN · FAILED NOW", "Modal FastAPI + Neon PostgreSQL", "Đường production từng ghi trong QuanLyKho; trạng thái live đã đổi")
    node(s, 1038, 710, 714, 180, "Modal FastAPI", ["Canonical business API theo ADR", "URL documented: workspace disabled", "Worker upstream secret thực tế chưa verify"], RED, "#fff2f1")
    node(s, 1038, 948, 714, 160, "Neon PostgreSQL", ["Nguồn dữ liệu chuẩn của QuanLyKho", "Không kiểm tra DB trực tiếp hôm nay"], QUAN, "#f1faf6", dashed=True)
    s.rule(1395, 892, 1395, 937, RED, 4, "10 8", arrow=True)
    s.pill(1038, 1170, "UPSTREAM 404/DISABLED · API qua Worker timeout", "#ffebe8", RED, 714, 48, 18)
    s.rule(890, 800, 1026, 800, RED, 4, "10 8", arrow=True, red=True)

    s.panel(1860, 266, 880, 1060, AZ, "AZURE · LIVE CONTROL PLANE", "AKS chạy, business pods chưa chạy", "az aks list + kubectl đọc trực tiếp, không đổi tài nguyên")
    node(s, 1898, 449, 802, 139, "AKS aks-portfolio-dev", ["ProvisioningState: Succeeded", "Azure East Asia; control plane reachable"], AZ, "#eaf6fc")
    node(s, 1898, 627, 802, 139, "Argo CD control plane", ["argocd deployments Ready", "Application flashsale + quanlykho đăng ký"], AZ, "#eaf6fc")
    node(s, 1898, 805, 802, 160, "Application state", ["flashsale: OutOfSync / Missing", "quanlykho: OutOfSync / Missing", "Hai namespace chưa có business pods"], RED, "#fff2f1")
    node(s, 1898, 1003, 802, 135, "Gateway / Tunnel", ["Gateway API resource: chưa có", "cloudflared pod: chưa có trên AKS"], RED, "#fff2f1")
    for y1, y2 in [(588, 617), (766, 795), (965, 993)]:
        s.rule(2299, y1, 2299, y2, AZ, 3, arrow=True)
    s.pill(1898, 1182, "CLOUDFLARE → AKS: CHƯA CÓ LIVE ROUTE", "#ffebe8", RED, 802, 48, 18)

    s.rect(60, 1370, 2680, 243, "#ffffff", "#dce6ef", 22, 2)
    s.text(100, 1426, "Kết luận kiến trúc hiện tại", 30, INK, 700)
    s.text(100, 1477, "Cloudflare phục vụ Web; Worker API root/health không chứng minh giao dịch chạy. Azure chứng minh cluster/Argo, chưa chứng minh workload.", 23, INK)
    s.text(100, 1520, "Retail Finance không nằm trên đường Cloudflare này; OpsBridge Pages chỉ có config. Không được vẽ Tunnel → AKS như đường production đã chạy.", 23, INK)
    s.pill(100, 1551, "AS-IS · READ-ONLY OBSERVATION", "#e9f1f8", AZ, 580, 42, 18)
    s.write("03-cloudflare-azure-as-is.svg")


def target():
    s = Svg("Cloudflare and Azure target hybrid architecture", "Proposed hybrid traffic, release, data and approved-agent action paths with explicit gates before promotion.", W, H)
    title(s, "04 / TARGET", "Cloudflare Edge → Azure AKS · kiến trúc đích", "Đường nét đứt là tích hợp cần triển khai và kiểm chứng. Cloudflare giữ edge; Azure chạy business workloads và control plane.")

    s.panel(60, 265, 1035, 786, CF, "PUBLIC EDGE / CLOUDFLARE", "UI, identity edge và outbound tunnel", "Workers Assets hiện chạy; Access/Tunnel/Pages còn gate triển khai")
    node(s, 99, 568, 307, 134, "Browser", ["Quan staff / Ops staff", "JWT identity + session"], CF, "#fff8f0")
    node(s, 490, 458, 557, 136, "Workers Assets / Pages", ["Flutter Web live; Ops Web Pages config", "Static UI, không sở hữu DB"], CF, "#fff2e5")
    node(s, 490, 651, 557, 156, "Access + WAF · TARGET", ["Entra / staff policy + edge controls", "JWT vẫn do owner API kiểm lại"], CF, "#fff2e5", dashed=True)
    node(s, 490, 842, 557, 157, "cloudflared Tunnel · TARGET", ["Outbound tunnel, không public origin port", "Manifest có; AKS runtime chưa chứng minh"], CF, "#fff2e5", dashed=True)
    s.path("M406 604 H447 V526 H480", CF, 4, arrow=True)
    s.path("M406 665 H447 V729 H480", CF, 4, arrow=True)
    s.rule(769, 807, 769, 832, CF, 4, "10 8", arrow=True)

    s.panel(1170, 265, 1570, 786, AZ, "AZURE / AKS RUNTIME", "Gateway → owner APIs → dữ liệu chuẩn", "AKS/Argo control plane live; route và workloads cần triển khai")
    node(s, 1210, 842, 410, 157, "Envoy Gateway", ["HTTPRoute / namespace policy", "Gateway API chưa có trên AKS"], AZ, "#ecf7fc", dashed=True)
    node(s, 1705, 451, 493, 139, "FlashSale / OpsBridge", ["Order API + Worker / Ops API", "Redis + RabbitMQ; DB riêng"], OPS, "#fff6ef", dashed=True)
    node(s, 1705, 650, 493, 139, "QuanLyKho FastAPI", ["Branch scope + FEFO + approval", "AI advisory; canonical API"], QUAN, "#f0faf5", dashed=True)
    node(s, 1705, 842, 493, 157, "Agent Hub executor", ["Typed command sau HITL", "Recheck scope/version/idempotency"], AI, "#edf9fa", dashed=True)
    node(s, 2285, 451, 412, 338, "Domain data", ["FlashSale PostgreSQL stock/order", "OpsBridge PostgreSQL riêng", "Quan PostgreSQL inventory", "Placement/restore: release gate"], RETAIL, "#eef5fd", dashed=True)
    node(s, 2285, 842, 412, 157, "SRE / Argo", ["Prometheus, alert, runbook", "Rollback theo revision đã duyệt"], PLATFORM, "#f4f1fa", dashed=True)
    s.rule(1047, 919, 1199, 919, CF, 4, "10 8", arrow=True)
    s.path("M1620 919 H1658 V720 H1695", AZ, 4, "10 8", arrow=True)
    s.path("M1620 919 H1658 V521 H1695", AZ, 4, "10 8", arrow=True)
    s.rule(2198, 521, 2275, 521, OPS, 4, "10 8", arrow=True)
    s.rule(2198, 720, 2275, 720, QUAN, 4, "10 8", arrow=True)
    s.rule(2198, 919, 2275, 919, AI, 4, "10 8", arrow=True)

    s.rect(60, 1090, 2680, 223, "#ffffff", "#dce6ef", 21, 2)
    s.text(96, 1140, "Release plane · GitHub Actions → Azure", 27, PLATFORM, 700)
    stages = [
        (96, "CI exact SHA", "tests / k6 / scan"),
        (618, "Entra OIDC", "protected approval"),
        (1140, "ACR digest", "immutable image"),
        (1662, "Argo CD", "desired Git ref"),
        (2184, "AKS rollout", "health + rollback"),
    ]
    for i, (x, head, detail) in enumerate(stages):
        node(s, x, 1172, 455, 108, head, [detail], PLATFORM, "#f3f0fa", dashed=True, size=22)
        if i < len(stages) - 1:
            s.rule(x + 455, 1226, x + 512, 1226, PLATFORM, 3, "10 8", arrow=True)

    s.rect(60, 1350, 2680, 247, "#eaf8f9", "#bfe3e8", 21, 2)
    s.text(96, 1402, "Agent execution plane · ADR 024 target", 28, AI, 700)
    s.text(96, 1460, "Read evidence → ActionIntent hash → policy → HUMAN APPROVAL → Agent executor → owner command API / Argo → post-state verification", 23, INK)
    s.text(96, 1504, "Retail Java/MySQL là domain riêng; Ops DLQ replay pilot; Quan voucher theo maker/checker; Argo rollback theo approved revision.", 22, INK)
    s.pill(96, 1530, "Không có raw SQL / shell / terraform apply cho LLM", "#d7f0f3", AI, 830, 42, 18)
    s.text(2720, 1634, "TARGET ≠ CURRENT · Gate: tunnel, gateway, pods, CORS/auth, E2E, alert, restore, cost", 19, MUTED, anchor="end")
    s.write("04-cloudflare-azure-target.svg")


if __name__ == "__main__":
    HERE.mkdir(parents=True, exist_ok=True)
    as_is()
    target()
    print("Generated Cloudflare/Azure as-is and target diagrams")

.PHONY: help test-all test-retail test-ops test-quan test-platform clean status

help:
	@echo "Senior Engineering Portfolio - Unified Monorepo"
	@echo "Available commands:"
	@echo "  make test-all       - Run full verification across all 4 systems (Retail, Ops, Quan, Platform)"
	@echo "  make test-retail    - Test Retail Finance (Java 17 unit & Testcontainers integration tests)"
	@echo "  make test-ops       - Test OpsBridge / FlashSale (.NET 10 solution: 371 tests)"
	@echo "  make test-quan      - Test QuanLyKho (Python 3.11 FastAPI with isolated test Postgres)"
	@echo "  make test-platform  - Test AKS-SRE-Platform validation gates (14 gates, 47 assertions)"
	@echo "  make status         - Show current git status and active pair"

status:
	@git status -s
	@echo ""
	@head -n 30 STATUS.md

test-retail:
	@echo "===> [1/4] Testing Retail Finance Core Platform (Java 17)..."
	cd services/retail-finance/backend && mvn verify
	@echo "===> Testing Retail Finance Reconciliation (Python 3.11)..."
	cd services/retail-finance/reconciliation-service && python3 -m pytest tests -q

test-ops:
	@echo "===> [2/4] Testing OpsBridge / FlashSale (.NET 10)..."
	dotnet test services/opsbridge-flashsale/AzureFlashSale.slnx

test-quan:
	@echo "===> [3/4] Testing QuanLyKho (Python 3.11 / FastAPI)..."
	$(MAKE) -C services/quanlykho test-backend

test-platform:
	@echo "===> [4/4] Testing AKS-SRE-Platform Validation Gates..."
	cd platform/aks-sre-platform && .venv/bin/python tests/test_gates.py

test-all: test-retail test-ops test-quan test-platform
	@echo "===> [SUCCESS] All 4 portfolio systems passed full verification!"

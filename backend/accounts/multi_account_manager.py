"""
MULTI-ACCOUNT MANAGER SERVICE
V6.5 — Auto-distributes profits across ECN and Standard accounts.

When the primary ECN account reaches $600,000 (Exness ECN max),
excess funds are distributed to other accounts automatically.
All accounts use V6.5 as the default trading engine.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from django.utils import timezone

logger = logging.getLogger("accounts.multi_manager")


class MultiAccountManager:
    """
    Manages multiple MT5 trading accounts with auto-scaling.

    Flow:
    1. Primary ECN account trades with V6.5
    2. When balance hits $600K threshold → trigger distribution
    3. Excess is split across secondary accounts (ECN or Standard)
    4. All accounts use V6.5 as the default engine
    """

    def __init__(self):
        self._mt5_service = None

    @property
    def mt5_service(self):
        if self._mt5_service is None:
            from mcp_integration.services import MT5Service
            self._mt5_service = MT5Service()
        return self._mt5_service

    def get_all_accounts(self, user_id) -> List:
        """Get all trading accounts for a user."""
        from accounts.models import TradingAccount
        return list(TradingAccount.objects.filter(user_id=user_id, status="ACTIVE"))

    def get_primary_account(self, user_id):
        """Get the primary ECN account."""
        from accounts.models import TradingAccount
        return TradingAccount.objects.filter(
            user_id=user_id, is_primary=True, account_type="ECN", status="ACTIVE"
        ).first()

    def get_secondary_accounts(self, user_id) -> List:
        """Get all non-primary accounts that can receive distributions."""
        from accounts.models import TradingAccount
        return list(TradingAccount.objects.filter(
            user_id=user_id, is_primary=False, status__in=["ACTIVE", "SCALED"]
        ))

    def sync_account_balance(self, account) -> Dict:
        """Sync balance from MT5 to local model."""
        try:
            import asyncio
            from mcp_integration.services import MT5Service
            service = MT5Service()

            # Temporarily switch MT5 connection to this account
            loop = asyncio.new_event_loop()
            try:
                info = loop.run_until_complete(service.get_account_info())
                account.balance = Decimal(str(info.get("balance", 0)))
                account.equity = Decimal(str(info.get("equity", 0)))
                account.last_balance_check = timezone.now()
                account.save(update_fields=["balance", "equity", "last_balance_check"])
                return {"synced": True, "balance": float(account.balance), "equity": float(account.equity)}
            finally:
                loop.close()
        except Exception as e:
            logger.error("Balance sync failed for %s: %s", account.mt5_login, e)
            return {"synced": False, "error": str(e)}

    def check_and_scale(self, user_id) -> Dict:
        """
        Check if primary ECN needs scaling and distribute if so.

        Returns:
            Dict with scaling status and distribution details
        """
        primary = self.get_primary_account(user_id)
        if not primary:
            return {"scaled": False, "reason": "No primary ECN account found"}

        # Sync balance first
        self.sync_account_balance(primary)

        if not primary.needs_scaling():
            return {
                "scaled": False,
                "reason": f"Balance ${primary.balance} below threshold ${primary.scaling_threshold}",
                "balance": float(primary.balance),
                "threshold": float(primary.scaling_threshold),
                "remaining": float(primary.scaling_threshold - primary.balance),
            }

        # Calculate distribution
        dist_amount = primary.distribution_amount()
        if dist_amount <= 0:
            return {"scaled": False, "reason": "No excess balance to distribute"}

        # Get secondary accounts
        secondaries = self.get_secondary_accounts(user_id)
        if not secondaries:
            return {
                "scaled": False,
                "reason": "No secondary accounts to receive distribution",
                "excess_available": dist_amount,
            }

        # Distribute equally across secondary accounts
        per_account = round(dist_amount / len(secondaries), 2)

        distributions = []
        for sec in secondaries:
            distributions.append({
                "account": sec.mt5_login,
                "server": sec.mt5_server,
                "type": sec.account_type,
                "current_balance": float(sec.balance),
                "receives": per_account,
                "new_balance": float(sec.balance) + per_account,
            })

        logger.info(
            "SCALING: Primary ECN %s at $%s — distributing $%s across %d accounts ($%s each)",
            primary.mt5_login, primary.balance, dist_amount, len(secondaries), per_account,
        )

        return {
            "scaled": True,
            "primary": primary.mt5_login,
            "primary_balance_before": float(primary.balance),
            "distribution_total": dist_amount,
            "per_account": per_account,
            "accounts": distributions,
            "note": "V6.5 engine active on all accounts",
        }

    def create_account(self, user_id, mt5_login, mt5_password, mt5_server,
                       account_type="STANDARD", is_primary=False, **kwargs) -> Dict:
        """Register a new MT5 account for multi-account trading."""
        from accounts.models import TradingAccount

        # Validate no duplicate
        existing = TradingAccount.objects.filter(mt5_login=mt5_login, mt5_server=mt5_server).exists()
        if existing:
            return {"created": False, "error": f"Account {mt5_login}@{mt5_server} already registered"}

        account = TradingAccount.objects.create(
            user_id=user_id,
            mt5_login=mt5_login,
            mt5_password=mt5_password,
            mt5_server=mt5_server,
            account_type=account_type,
            is_primary=is_primary,
            trading_engine="v6.5",  # Always V6.5
            **kwargs,
        )

        logger.info("Created trading account: %s (%s) — V6.5 engine", mt5_login, account_type)

        return {
            "created": True,
            "account_id": str(account.id),
            "mt5_login": mt5_login,
            "account_type": account_type,
            "trading_engine": "v6.5",
        }

    def get_portfolio_summary(self, user_id) -> Dict:
        """Get total balance and position sizing across all accounts."""
        accounts = self.get_all_accounts(user_id)
        total_balance = sum(float(a.balance) for a in accounts)
        total_equity = sum(float(a.equity) for a in accounts)

        account_details = []
        for a in accounts:
            lots = a.get_lots_for_balance()
            account_details.append({
                "mt5_login": a.mt5_login,
                "account_type": a.account_type,
                "status": a.status,
                "is_primary": a.is_primary,
                "balance": float(a.balance),
                "equity": float(a.equity),
                "max_lots": lots,
                "trading_engine": a.trading_engine,
            })

        return {
            "total_accounts": len(accounts),
            "total_balance": total_balance,
            "total_equity": total_equity,
            "total_max_lots": max(0.01, round(total_balance / 100.0, 2)),
            "accounts": account_details,
            "trading_engine": "v6.5",
        }

"""
OdooXMLRPCClient — thin wrapper over stdlib xmlrpc.client.

Rules (enforced in AGENT.md):
- XML-RPC only. No psycopg2, no direct SQL, no ORM imports.
- Authentication is lazy: first call to .uid triggers authenticate().
- All public methods delegate to self.execute().
- call_method() is the escape hatch for custom Odoo business methods
  (e.g. button_confirm, message_post, activity_schedule).
"""

import xmlrpc.client
from functools import cached_property
from typing import Any

from core.config import settings


class OdooXMLRPCClient:
    def __init__(self) -> None:
        self._url = settings.odoo_url
        self._db = settings.odoo_db
        self._user = settings.odoo_user
        self._api_key = settings.odoo_api_key
        self._uid: int | None = None

    # ── Internal proxies ──────────────────────────────────────────────────────

    @cached_property
    def _common(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/common")

    @cached_property
    def _models(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/object")

    # ── Authentication ────────────────────────────────────────────────────────

    @property
    def uid(self) -> int:
        if self._uid is None:
            self._uid = self._common.authenticate(
                self._db, self._user, self._api_key, {}
            )
            if not self._uid:
                raise ConnectionError(
                    f"Odoo authentication failed for user='{self._user}' "
                    f"db='{self._db}' url='{self._url}'"
                )
        return self._uid

    # ── Core execute ──────────────────────────────────────────────────────────

    def execute(self, model: str, method: str, *args: Any, **kwargs: Any) -> Any:
        """Raw execute_kw — all other methods delegate here."""
        return self._models.execute_kw(
            self._db, self.uid, self._api_key,
            model, method, list(args), kwargs,
        )

    # ── CRUD helpers ──────────────────────────────────────────────────────────

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str],
        limit: int = 80,
        offset: int = 0,
        order: str = "id desc",
    ) -> list[dict]:
        return self.execute(
            model, "search_read", domain,
            fields=fields, limit=limit, offset=offset, order=order,
        )

    def search(self, model: str, domain: list, **kwargs: Any) -> list[int]:
        return self.execute(model, "search", domain, **kwargs)

    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict]:
        return self.execute(model, "read", ids, fields=fields)

    def create(self, model: str, values: dict) -> int:
        return self.execute(model, "create", values)

    def write(self, model: str, ids: list[int], values: dict) -> bool:
        return self.execute(model, "write", ids, values)

    def unlink(self, model: str, ids: list[int]) -> bool:
        return self.execute(model, "unlink", ids)

    def search_count(self, model: str, domain: list) -> int:
        return self.execute(model, "search_count", domain)

    # ── Business method call (button actions, message_post, etc.) ─────────────

    def call_method(
        self,
        model: str,
        method: str,
        ids: list[int],
        **kwargs: Any,
    ) -> Any:
        """
        Call any public Odoo method on a recordset.

        Usage:
            client.call_method("purchase.order", "button_confirm", [po_id])
            client.call_method(
                "era.ascp.pegging.ledger", "message_post",
                [ledger_id],
                body="<b>AI note</b>",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
        """
        return self.execute(model, method, ids, **kwargs)

    # ── Convenience: get single record ────────────────────────────────────────

    def get(self, model: str, record_id: int, fields: list[str]) -> dict | None:
        records = self.read(model, [record_id], fields)
        return records[0] if records else None

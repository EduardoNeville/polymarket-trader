"""
Market data utilities for fetching resolved markets and price history.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Tuple

import requests

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"


@dataclass
class FetchStats:
    markets_seen: int = 0
    markets_used: int = 0
    markets_skipped: int = 0
    price_history_calls: int = 0


def _parse_json_list(value):
    if value is None:
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def _resolve_binary_outcome(outcomes, outcome_prices) -> Optional[int]:
    if not outcomes or not outcome_prices:
        return None

    if len(outcomes) != len(outcome_prices):
        return None

    yes_index = None
    for idx, outcome in enumerate(outcomes):
        if str(outcome).strip().lower() == "yes":
            yes_index = idx
            break

    if yes_index is None:
        return None

    try:
        yes_price = float(outcome_prices[yes_index])
    except (TypeError, ValueError):
        return None

    if yes_price >= 0.99:
        return 1
    if yes_price <= 0.01:
        return 0
    return None


def _select_yes_token_id(outcomes, token_ids) -> Optional[str]:
    if not outcomes or not token_ids:
        return None

    if len(outcomes) != len(token_ids):
        return None

    for idx, outcome in enumerate(outcomes):
        if str(outcome).strip().lower() == "yes":
            return str(token_ids[idx])

    return None


def fetch_markets_page(
    *,
    limit: int = 100,
    offset: int = 0,
    closed: Optional[bool] = True,
    uma_resolution_status: Optional[str] = None,
    end_date_min: Optional[str] = None,
    end_date_max: Optional[str] = None,
    order: Optional[str] = None,
    ascending: Optional[bool] = None,
) -> List[Dict]:
    params: Dict[str, object] = {"limit": limit, "offset": offset}

    if closed is not None:
        params["closed"] = closed
    if uma_resolution_status:
        params["uma_resolution_status"] = uma_resolution_status
    if end_date_min:
        params["end_date_min"] = end_date_min
    if end_date_max:
        params["end_date_max"] = end_date_max
    if order:
        params["order"] = order
    if ascending is not None:
        params["ascending"] = ascending

    response = requests.get(f"{GAMMA_API_BASE}/markets", params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Unexpected response from markets endpoint")
    return data


def iter_markets(
    *,
    limit: int = 100,
    max_markets: Optional[int] = None,
    closed: Optional[bool] = True,
    uma_resolution_status: Optional[str] = None,
    end_date_min: Optional[str] = None,
    end_date_max: Optional[str] = None,
    order: Optional[str] = None,
    ascending: Optional[bool] = None,
) -> Iterable[Dict]:
    offset = 0
    total = 0

    while True:
        page = fetch_markets_page(
            limit=limit,
            offset=offset,
            closed=closed,
            uma_resolution_status=uma_resolution_status,
            end_date_min=end_date_min,
            end_date_max=end_date_max,
            order=order,
            ascending=ascending,
        )

        if not page:
            break

        for market in page:
            yield market
            total += 1
            if max_markets is not None and total >= max_markets:
                return

        offset += limit


def fetch_price_history(
    token_id: str,
    *,
    interval: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    fidelity: Optional[int] = None,
) -> List[Dict]:
    params: Dict[str, object] = {"market": token_id}

    if interval:
        params["interval"] = interval
    if start_ts is not None:
        params["startTs"] = start_ts
    if end_ts is not None:
        params["endTs"] = end_ts
    if fidelity is not None:
        params["fidelity"] = fidelity

    response = requests.get(
        f"{CLOB_API_BASE}/prices-history", params=params, timeout=30
    )
    response.raise_for_status()
    data = response.json()
    history = data.get("history")
    if not isinstance(history, list):
        return []
    return history


def build_backtest_points(
    market: Dict,
    history: List[Dict],
    *,
    outcome: Optional[int],
) -> List[Dict]:
    if not history:
        return []

    history_sorted = sorted(history, key=lambda item: item.get("t", 0))

    slug = market.get("slug") or str(market.get("id") or "unknown-market")
    question = market.get("question") or ""
    category = market.get("category") or "general"

    points: List[Dict] = []
    last_idx = len(history_sorted) - 1
    for idx, item in enumerate(history_sorted):
        ts = item.get("t")
        price = item.get("p")
        if ts is None or price is None:
            continue

        timestamp = datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
        point = {
            "timestamp": timestamp,
            "market_slug": slug,
            "question": question,
            "price": float(price),
            "outcome": outcome if idx == last_idx else None,
            "category": category,
        }
        points.append(point)

    return points


def fetch_resolved_backtest_data(
    *,
    limit: int = 100,
    max_markets: Optional[int] = None,
    uma_resolution_status: Optional[str] = None,
    end_date_min: Optional[str] = None,
    end_date_max: Optional[str] = None,
    interval: Optional[str] = "max",
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    fidelity: Optional[int] = None,
    pause_seconds: float = 0.0,
    allow_unresolved: bool = False,
) -> Tuple[List[Dict], FetchStats]:
    stats = FetchStats()
    backtest_points: List[Dict] = []

    for market in iter_markets(
        limit=limit,
        max_markets=max_markets,
        closed=True,
        uma_resolution_status=uma_resolution_status,
        end_date_min=end_date_min,
        end_date_max=end_date_max,
        order="closedTime",
        ascending=False,
    ):
        stats.markets_seen += 1

        outcomes = _parse_json_list(market.get("outcomes"))
        outcome_prices = _parse_json_list(market.get("outcomePrices"))
        token_ids = _parse_json_list(market.get("clobTokenIds"))

        if not outcomes or not token_ids:
            stats.markets_skipped += 1
            continue

        outcome_value = _resolve_binary_outcome(outcomes, outcome_prices)
        if outcome_value is None and not allow_unresolved:
            stats.markets_skipped += 1
            continue

        token_id = _select_yes_token_id(outcomes, token_ids)
        if not token_id:
            stats.markets_skipped += 1
            continue

        history = fetch_price_history(
            token_id,
            interval=interval,
            start_ts=start_ts,
            end_ts=end_ts,
            fidelity=fidelity,
        )
        stats.price_history_calls += 1
        if pause_seconds > 0:
            time.sleep(pause_seconds)

        points = build_backtest_points(market, history, outcome=outcome_value)
        if not points:
            stats.markets_skipped += 1
            continue

        backtest_points.extend(points)
        stats.markets_used += 1

    return backtest_points, stats

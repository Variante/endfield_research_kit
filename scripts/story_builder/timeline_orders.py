from __future__ import annotations

from .context import EXPORT_ROOT
from .timeline_recovery import (
    TimelineRecoveryConfig,
    default_order_out as timeline_recovery_order_out,
    discover_asset_maps as discover_timeline_asset_maps,
    recover_timeline_line_orders,
    timeline_order_is_current,
)


def recover_timeline_orders_for_build(mode: str, force: bool = False) -> None:
    if mode == "never":
        print("Timeline line-order recovery: skipped")
        return

    maps = discover_timeline_asset_maps(EXPORT_ROOT)
    order_out = timeline_recovery_order_out(EXPORT_ROOT)
    if not force and timeline_order_is_current(order_out, maps):
        print(f"Timeline line-order recovery: using {order_out}")
        return

    if mode == "auto" and not maps:
        print("Timeline line-order recovery: skipped (no AnimeStudio CLI AssetMaps found)")
        return

    print("Timeline line-order recovery: parsing Timeline assets...")
    try:
        recover_timeline_line_orders(
            TimelineRecoveryConfig(
                export_root=EXPORT_ROOT,
                maps=maps,
                order_out=order_out,
            )
        )
    except Exception as exc:
        if mode == "always":
            raise
        print(f"Timeline line-order recovery: skipped ({exc})")
        return

    from . import dialog_tree

    dialog_tree._DIALOG_TIMELINE_LINE_ORDER_CACHE = None
    dialog_tree._TIMELINE_TO_DIALOG_KEYS_CACHE = None

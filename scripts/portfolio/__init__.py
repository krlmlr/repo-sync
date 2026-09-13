"""Portfolio metrics: collection, scoring and rendering for the status dashboard.

The entry points are `scripts/collect_metrics.py` and `scripts/render_dashboard.py`;
everything they share lives here, so the two tools agree on the snapshot
without either of them owning it.
"""

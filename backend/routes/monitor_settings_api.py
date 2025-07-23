"""Flask blueprint providing CRUD endpoints for monitor thresholds.

URL prefix: /api/monitor-settings
"""
from flask import Blueprint, request, jsonify
from backend.data.data_locker import DataLocker  # type: ignore
from backend.core.alert_core.threshold_service import ThresholdService  # type: ignore

bp = Blueprint('monitor_settings', __name__, url_prefix='/api/monitor-settings')

# ------------------------------------------------------------------ #
# Liquidation Monitor (liquid_monitor)
# ------------------------------------------------------------------ #
@bp.route('/liquidation', methods=['GET', 'POST'])
def liquidation_settings():
    """GET → current config, POST → update threshold & snooze."""
    dl = DataLocker.get_instance()
    cfg = dl.system.get_var('liquid_monitor') or {}

    if request.method == 'GET':
        return jsonify(cfg)

    # Minimal validation
    data = request.get_json(silent=True) or {}
    cfg.update({
        'threshold_percent': float(data.get('threshold_percent', cfg.get('threshold_percent', 5.0))),
        'snooze_seconds': int(data.get('snooze_seconds', cfg.get('snooze_seconds', 300)))
    })
    dl.system.set_var('liquid_monitor', cfg)
    return jsonify({'success': True, 'config': cfg})

# ------------------------------------------------------------------ #
# Profit Monitor thresholds (uses ThresholdService rows)
# ------------------------------------------------------------------ #
@bp.route('/profit', methods=['GET', 'POST'])
def profit_settings():
    dl = DataLocker.get_instance()
    ts = ThresholdService(dl.db)

    if request.method == 'GET':
        # Fetch existing thresholds
        portfolio_th = ts.get_thresholds('TotalProfit', 'Portfolio', 'ABOVE')
        single_th = ts.get_thresholds('Profit', 'Position', 'ABOVE')
        return jsonify({
            'portfolio_low': getattr(portfolio_th, 'low', None),
            'portfolio_high': getattr(portfolio_th, 'high', None),
            'single_low': getattr(single_th, 'low', None),
            'single_high': getattr(single_th, 'high', None),
        })

    # Update / insert
    data = request.get_json(silent=True) or {}
    ts.set_threshold('TotalProfit', 'Portfolio',
                     data.get('portfolio_low'), data.get('portfolio_high'))
    ts.set_threshold('Profit', 'Position',
                     data.get('single_low'), data.get('single_high'))

    return jsonify({'success': True})
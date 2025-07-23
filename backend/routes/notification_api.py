"""Blueprint exposing notification endpoints for React header dropdown."""
from flask import Blueprint, jsonify, request
from backend.data.data_locker import DataLocker  # type: ignore
from backend.core.notification_service import NotificationService  # type: ignore

bp = Blueprint('notification_api', __name__, url_prefix='/api/notifications')

@bp.route('', methods=['GET'])
def list_notifications():
    status = request.args.get('status', 'all')
    dl = DataLocker.get_instance()
    svc = NotificationService(dl.db)
    return jsonify(svc.list(status=status))

@bp.route('/unread-count', methods=['GET'])
def unread_count():
    dl = DataLocker.get_instance()
    svc = NotificationService(dl.db)
    return jsonify({'count': svc.unread_count()})

@bp.route('/<notif_id>/read', methods=['POST'])
def mark_read(notif_id):
    dl = DataLocker.get_instance()
    svc = NotificationService(dl.db)
    svc.mark_read(notif_id)
    return jsonify({'success': True})

@bp.route('/mark_all_read', methods=['POST'])
def mark_all_read():
    dl = DataLocker.get_instance()
    svc = NotificationService(dl.db)
    svc.mark_all_read()
    return jsonify({'success': True})
from apps.coupons.models import UserCoupon


def release_locked_coupon(snapshot):
    """Release a locked coupon snapshot and return identifiers for logging."""
    if not snapshot or not snapshot.user_coupon:
        return '', ''
    if snapshot.user_coupon.status != UserCoupon.STATUS_LOCKED:
        return '', ''

    coupon_id = snapshot.user_coupon_id
    coupon_no = snapshot.user_coupon.coupon_no
    snapshot.user_coupon.status = UserCoupon.STATUS_UNUSED
    snapshot.user_coupon.locked_at = None
    snapshot.user_coupon.save(update_fields=['status', 'locked_at', 'used_at'])
    return coupon_id, coupon_no

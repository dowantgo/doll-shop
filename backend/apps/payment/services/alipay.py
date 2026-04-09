import os
import logging
from datetime import timedelta
from typing import Dict, Any

from django.utils import timezone

from .errors import PaymentError, PaymentConfigurationError, PaymentNetworkError, PaymentSignatureError

logger = logging.getLogger(__name__)


class AliPayService:
    def __init__(self):
        self._alipay = None
        self._appid = None
        self._private_key = None
        self._public_key = None

    def _load_config(self):
        if self._alipay is not None:
            return

        appid = (os.getenv('ALIPAY_APP_ID') or os.getenv('ALIPAY_APPID') or '').strip()
        private_key = (os.getenv('ALIPAY_PRIVATE_KEY') or '').strip()
        public_key = (os.getenv('ALIPAY_PUBLIC_KEY') or '').strip()

        if not appid:
            raise PaymentConfigurationError('ALIPAY_APP_ID 未配置')
        if not private_key:
            raise PaymentConfigurationError('ALIPAY_PRIVATE_KEY 未配置')
        if not public_key:
            raise PaymentConfigurationError('ALIPAY_PUBLIC_KEY 未配置')

        self._appid = appid
        self._private_key = private_key
        self._public_key = public_key
        self._init_alipay()

    def _init_alipay(self):
        try:
            from alipay import AliPay
        except ImportError as exc:
            raise PaymentConfigurationError('缺少 python-alipay-sdk，请执行: pip install python-alipay-sdk') from exc

        app_private_key = f"-----BEGIN RSA PRIVATE KEY-----\n{self._private_key}\n-----END RSA PRIVATE KEY-----"
        alipay_public_key = f"-----BEGIN PUBLIC KEY-----\n{self._public_key}\n-----END PUBLIC KEY-----"

        self._alipay = AliPay(
            appid=self._appid,
            app_notify_url=os.getenv('ALIPAY_NOTIFY_URL', 'http://localhost:8000/api/pay/notify/alipay/'),
            app_private_key_string=app_private_key,
            alipay_public_key_string=alipay_public_key,
            sign_type='RSA2',
            debug=(os.getenv('ALIPAY_DEBUG', 'True').lower() == 'true'),
        )
        logger.info('AliPay initialized. APPID=%s', self._appid)

    def _ensure_alipay(self):
        if self._alipay is None:
            self._load_config()

    def create_qr_code(self, out_trade_no: str, total_amount: float, subject: str, timeout: int = 15) -> Dict[str, Any]:
        self._ensure_alipay()

        expire_time = timezone.now() + timedelta(minutes=timeout)
        try:
            response = self._alipay.api_alipay_trade_precreate(
                subject=subject,
                out_trade_no=out_trade_no,
                total_amount=f'{total_amount:.2f}',
                timeout_express=f'{timeout}m',
            )
            logger.info('Alipay precreate response: %s', response)

            qr_code = response.get('qr_code', '')
            if not qr_code:
                msg = response.get('sub_msg') or response.get('msg') or str(response)
                if '验签' in msg or 'sign' in msg.lower():
                    raise PaymentSignatureError(msg)
                raise PaymentNetworkError(msg)

            return {
                'out_trade_no': out_trade_no,
                'qr_code': qr_code,
                'expire_time': expire_time.isoformat(),
            }

        except (PaymentSignatureError, PaymentNetworkError, PaymentConfigurationError):
            raise
        except Exception as exc:
            err = str(exc) or f'{type(exc).__name__}: {repr(exc)}'
            if '验签' in err or 'sign' in err.lower():
                raise PaymentSignatureError(err)
            if 'timeout' in err.lower() or 'timed out' in err.lower() or '拒绝' in err:
                raise PaymentNetworkError(err)
            raise PaymentError(err)

    def query_order(self, out_trade_no: str) -> Dict[str, Any]:
        self._ensure_alipay()
        try:
            response = self._alipay.api_alipay_trade_query(out_trade_no=out_trade_no)
            logger.info('Alipay query response: %s', response)
            return {
                'out_trade_no': out_trade_no,
                'trade_no': response.get('trade_no', ''),
                'trade_status': response.get('trade_status', ''),
                'total_amount': response.get('total_amount', ''),
                'paid_time': response.get('send_pay_date', ''),
            }
        except Exception as exc:
            raise PaymentNetworkError(str(exc) or repr(exc))

    def verify_notification(self, data: Dict[str, str]) -> bool:
        self._ensure_alipay()
        try:
            payload = dict(data or {})
            signature = payload.get('sign', '')
            if not signature:
                return False

            sign_type = payload.get('sign_type', 'RSA2')
            if sign_type != 'RSA2':
                return False

            payload.pop('sign', None)
            payload.pop('sign_type', None)
            return self._alipay.verify(payload, signature)
        except Exception as exc:
            logger.warning('Alipay notify verify exception: %s', exc)
            return False


alipay_service = AliPayService()

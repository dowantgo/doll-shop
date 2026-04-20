from dataclasses import dataclass
from typing import Dict, List

import requests
from django.conf import settings
from django.utils import timezone


@dataclass
class LogisticsResult:
    provider: str
    available: bool
    message: str
    traces: List[Dict]


class BaseLogisticsProvider:
    name = 'base'

    def query(self, order) -> LogisticsResult:
        raise NotImplementedError


class MockProvider(BaseLogisticsProvider):
    name = 'mock'

    def query(self, order) -> LogisticsResult:
        if not order.tracking_no:
            return LogisticsResult(
                provider=self.name,
                available=False,
                message='Order has not been shipped yet.',
                traces=[],
            )

        traces = []
        if order.shipped_at:
            traces.append(
                {
                    'time': order.shipped_at.isoformat(),
                    'location': 'Warehouse',
                    'status': 'Picked up',
                    'description': 'Package has been picked up by courier.',
                }
            )
        if order.shipping_status in ['in_transit', 'arrived', 'signed']:
            traces.append(
                {
                    'time': timezone.now().isoformat(),
                    'location': 'Transit Center',
                    'status': 'In transit',
                    'description': 'Package is in transit.',
                }
            )
        if order.shipping_status in ['arrived', 'signed']:
            traces.append(
                {
                    'time': timezone.now().isoformat(),
                    'location': 'Destination City',
                    'status': 'Arrived',
                    'description': 'Package has arrived at destination city.',
                }
            )
        if order.shipping_status == 'signed':
            traces.append(
                {
                    'time': timezone.now().isoformat(),
                    'location': 'Recipient Address',
                    'status': 'Signed',
                    'description': 'Package has been signed by recipient.',
                }
            )

        return LogisticsResult(
            provider=self.name,
            available=True,
            message='OK',
            traces=traces,
        )


class Kuaidi100Provider(BaseLogisticsProvider):
    name = 'kuaidi100'

    def query(self, order) -> LogisticsResult:
        if not order.tracking_no or not order.shipping_company:
            return LogisticsResult(self.name, False, 'Order has not been shipped yet.', [])

        key = getattr(settings, 'KUAIDI100_API_KEY', '')
        customer = getattr(settings, 'KUAIDI100_CUSTOMER', '')
        if not key or not customer:
            return LogisticsResult(self.name, False, 'Kuaidi100 config missing.', [])

        try:
            response = requests.get(
                'https://poll.kuaidi100.com/poll/query.do',
                params={
                    'customer': customer,
                    'key': key,
                    'com': order.shipping_company,
                    'num': order.tracking_no,
                },
                timeout=8,
            )
            payload = response.json()
            if str(payload.get('status', '')) != '200':
                return LogisticsResult(
                    self.name,
                    False,
                    payload.get('message') or 'Third-party query failed.',
                    [],
                )

            traces = []
            for row in payload.get('data', []):
                traces.append(
                    {
                        'time': row.get('ftime') or row.get('time') or '',
                        'location': row.get('areaCode') or '',
                        'status': row.get('status') or '',
                        'description': row.get('context') or '',
                    }
                )
            return LogisticsResult(self.name, True, 'OK', traces)
        except Exception as exc:
            return LogisticsResult(self.name, False, f'Third-party query error: {exc}', [])


def get_logistics_provider():
    provider = getattr(settings, 'LOGISTICS_PROVIDER', 'mock').lower().strip()
    if provider == 'kuaidi100':
        return Kuaidi100Provider()
    return MockProvider()

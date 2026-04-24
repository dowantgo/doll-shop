import logging

from django.core.cache import cache
from django.db.models import Case, ExpressionWrapper, F, FloatField, Value, When

from apps.products.cache_utils import get_feed_ttl, make_feed_cache_key
from apps.products.models import Product
from apps.products.serializers import ProductFeedSerializer

logger = logging.getLogger(__name__)


def _normalize_limit(raw_limit, default=10, maximum=50) -> int:
    try:
        return min(max(int(raw_limit or default), 1), maximum)
    except (TypeError, ValueError):
        return default


def _stats_key(feed_name: str, metric: str) -> str:
    return f'products:feed:stats:{feed_name}:{metric}'


def _record_cache_metric(feed_name: str, metric: str) -> None:
    try:
        cache.incr(_stats_key(feed_name, metric))
    except ValueError:
        cache.add(_stats_key(feed_name, metric), 1, None)
    except Exception as exc:
        logger.debug('product_feed_metric_failed feed=%s metric=%s error=%s', feed_name, metric, exc)


class ProductFeedService:
    """Centralized cache/query path for public product feed endpoints."""

    def __init__(self, *, request=None):
        self.request = request

    def get_top_sales(self, raw_limit=None):
        limit = _normalize_limit(raw_limit)
        return self._get_cached_feed(
            feed_name='top-sales',
            limit=limit,
            queryset_factory=lambda: (
                Product.objects.filter(status=True)
                .annotate(hot_score=ExpressionWrapper(F('sales') * Value(1.0), output_field=FloatField()))
                .prefetch_related('images')
                .order_by('-sales', '-created_at')[:limit]
            ),
        )

    def get_hot_feed(self, raw_limit=None):
        limit = _normalize_limit(raw_limit)
        hot_score_expr = ExpressionWrapper(
            F('sales') * Value(1.0)
            + Case(When(is_hot=True, then=Value(20.0)), default=Value(0.0), output_field=FloatField())
            + F('hot_sort_order') * Value(0.1),
            output_field=FloatField(),
        )
        return self._get_cached_feed(
            feed_name='hot-feed',
            limit=limit,
            queryset_factory=lambda: (
                Product.objects.filter(status=True)
                .annotate(hot_score=hot_score_expr)
                .prefetch_related('images')
                .order_by('-hot_score', '-sales', '-created_at')[:limit]
            ),
        )

    def _get_cached_feed(self, *, feed_name: str, limit: int, queryset_factory):
        cache_key = make_feed_cache_key(feed_name, limit)
        try:
            cached = cache.get(cache_key)
        except Exception as exc:
            cached = None
            logger.warning('product_feed_cache_get_failed feed=%s key=%s error=%s', feed_name, cache_key, exc)

        if cached is not None:
            _record_cache_metric(feed_name, 'hit')
            logger.info('product_feed_cache_hit feed=%s limit=%s key=%s', feed_name, limit, cache_key)
            return cached

        _record_cache_metric(feed_name, 'miss')
        queryset = queryset_factory()
        data = ProductFeedSerializer(queryset, many=True, context={'request': self.request}).data
        try:
            cache.set(cache_key, data, get_feed_ttl(feed_name))
        except Exception as exc:
            logger.warning('product_feed_cache_set_failed feed=%s key=%s error=%s', feed_name, cache_key, exc)
        logger.info('product_feed_cache_miss feed=%s limit=%s key=%s', feed_name, limit, cache_key)
        return data


def get_feed_cache_stats():
    stats = {}
    for feed_name in ('top-sales', 'hot-feed'):
        hit = int(cache.get(_stats_key(feed_name, 'hit')) or 0)
        miss = int(cache.get(_stats_key(feed_name, 'miss')) or 0)
        total = hit + miss
        stats[feed_name] = {
            'hit': hit,
            'miss': miss,
            'hit_rate': round(hit / total, 4) if total else 0,
        }
    return stats

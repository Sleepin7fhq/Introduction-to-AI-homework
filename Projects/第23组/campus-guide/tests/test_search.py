import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from guide_data import GuideError
from search_service import SearchProvider, SearchQuery, WebResult, WebSupplement, search_status


class SearchContractTests(unittest.TestCase):
    def test_switch_and_missing_provider(self):
        self.assertIn("已关闭", search_status(None))
        self.assertIn("已关闭", search_status({"SEARCH_ENABLED": False}))
        self.assertIn("暂不可用", search_status({"SEARCH_ENABLED": True}))
        self.assertIn("true 或 false", search_status({"SEARCH_ENABLED": "true"}))
        query = SearchQuery("测试学校", "测试校区", "测试建筑", "近期活动")
        with self.assertRaisesRegex(GuideError, "尚未配置"):
            WebSupplement(enabled=True).search(query, consent=True)

    def test_replaceable_provider_requires_switch_and_per_query_consent(self):
        query = SearchQuery("测试学校", "测试校区", "测试建筑", "近期活动")
        now = datetime.now(timezone.utc)
        result = WebResult("测试标题", "https://example.invalid/fixture", "测试摘要", now)
        provider = Mock(spec=SearchProvider)
        provider.search.return_value = [result]
        with self.assertRaisesRegex(GuideError, "已关闭"):
            WebSupplement(False, provider).search(query, consent=True)
        service = WebSupplement(True, provider)
        with self.assertRaisesRegex(GuideError, "本次联网"):
            service.search(query)
        provider.search.assert_not_called()
        self.assertEqual(service.search(query, consent=True), [result])
        provider.search.assert_called_once_with(query)
        self.assertIsNone(result.published_on)
        self.assertEqual(result.retrieved_at, now)

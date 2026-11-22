import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, Mock

from streamlit.testing.v1 import AppTest
from ai_service import NO_INFO, PARTIAL_INFO
from guide_data import GuideError, load_catalog
from search_service import parse_search_response, search_endpoint, search_guide, SearchAnswer, WebResult

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.now(timezone.utc)
URL = 'https://history.seu.edu.cn/example.htm'


def response(text='说明。[ref_1]', url=URL):
    return {'output': {'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}],
                       'search_info': {'search_results': [{'index': 1, 'title': '校史资料', 'url': url}]}}}


class LiveSearchTests(unittest.TestCase):
    def test_invalid_citation_claim_and_internal_explanation_are_removed(self):
        raw = ('2025年举办了羽毛球比赛。[ref_1]'
               '另有2023年活动[ref_无]（该信息未在当前知识库编号中出现，故不标引用）。\n'
               '没有证据的另一项活动。\n'
               '当前知识库没有其他记录。[ref_1]')
        answer = parse_search_response(response(raw), NOW)
        self.assertEqual(answer.text, '2025年举办了羽毛球比赛。')
        self.assertNotIn('ref_', answer.text)
        self.assertEqual(len(answer.sources), 1)
        for text in ['活动[ref_无]（不标引用）。', '活动[ref_1未闭合', '活动没有出处。']:
            with self.assertRaises(GuideError):
                parse_search_response(response(text), NOW)

    def test_missing_and_partial_answers_search_automatically_once(self):
        cfg = {'API_KEY':'test-only','BASE_URL':'https://dashscope.aliyuncs.com/compatible-mode/v1',
               'MODEL_NAME':'fixture-vision','SEARCH_ENABLED':True}
        for coverage, ids in [('none', []), ('partial', ['origin'])]:
            with self.subTest(coverage=coverage), patch('ai_service.read_settings', return_value=cfg), \
                    patch('ai_service.chat_json', side_effect=[{'coverage':'full','fact_ids':['origin']},
                                                              {'coverage':coverage,'fact_ids':ids}]), \
                    patch('search_service.search_guide') as search:
                search.return_value = SearchAnswer('已核实的活动信息。', (WebResult('校史资料',URL,'',NOW),), NOW)
                a = AppTest.from_file(str(ROOT/'app.py')).run()
                a.radio(key='mode').set_value('真实 API').run()
                a.button(key='generate').click().run()
                search.assert_not_called()
                a.chat_input[0].set_value('近年举办了哪些活动？').run()
                a.run()
                self.assertEqual(search.call_count, 1)
                self.assertEqual(search.call_args.args[2], '近年举办了哪些活动？')
                texts = [t.value for t in a.text]
                self.assertIn('已核实的活动信息。', texts)
                self.assertNotIn(NO_INFO, texts)
                self.assertNotIn(PARTIAL_INFO, texts)
                self.assertFalse(any('_turn_' in str(b.key) for b in a.button))
                self.assertFalse(a.exception)

    def test_automatic_search_failure_waits_for_manual_retry(self):
        cfg = {'API_KEY':'test-only','BASE_URL':'https://dashscope.aliyuncs.com/compatible-mode/v1',
               'MODEL_NAME':'fixture-vision','SEARCH_ENABLED':True}
        with patch('ai_service.read_settings', return_value=cfg), \
                patch('ai_service.chat_json', return_value={'coverage':'none','fact_ids':[]}), \
                patch('search_service.search_guide', side_effect=[GuideError('搜索超时'),
                      SearchAnswer('重试成功。', (WebResult('校史资料',URL,'',NOW),), NOW)]) as search:
            a = AppTest.from_file(str(ROOT/'app.py')).run()
            a.radio(key='mode').set_value('真实 API').run()
            a.button(key='generate').click().run()
            a.run()
            self.assertEqual(search.call_count, 1)
            button = next(b for b in a.button if b.label == '重试搜索')
            button.click().run()
            a.run()
            self.assertEqual(search.call_count, 2)
            self.assertIn('重试成功。', [t.value for t in a.text])
            self.assertFalse(a.exception)

    def test_grounding_and_duplicate_citations(self):
        result = parse_search_response(response('第一句。[ref_1]第二句。[ref_1]'), NOW)
        self.assertEqual(len(result.sources), 1)
        self.assertNotIn('[ref_', result.text)
        self.assertEqual(result.retrieved_at, NOW)
        self.assertIsNone(result.sources[0].published_on)
        for data in [response('没有检索证据'), response('不明来源[ref_8]'),
                     response(url='https://seu.edu.cn.evil.invalid/x'), response(url='javascript:alert(1)'),
                     {'output': {'choices': []}}, response(url='https://u:p@history.seu.edu.cn/x')]:
            with self.assertRaises(GuideError):
                parse_search_response(data, NOW)

    def test_endpoint_only_reuses_key_for_bailian(self):
        self.assertEqual(search_endpoint('https://dashscope.aliyuncs.com/compatible-mode/v1'),
                         'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')
        self.assertIn('workspace.cn-beijing.maas.aliyuncs.com', search_endpoint(
            'https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'))
        for base in ['https://evil.invalid/compatible-mode/v1', 'https://dashscope.aliyuncs.com.evil.invalid/compatible-mode/v1',
                     'https://dashscope.aliyuncs.com/wrong']:
            with self.assertRaises(GuideError):
                search_endpoint(base)

    @patch('search_service.requests.post')
    def test_search_request_and_no_source_fallback(self, post):
        cfg = {'API_KEY':'test-only','BASE_URL':'https://dashscope.aliyuncs.com/compatible-mode/v1',
               'MODEL_NAME':'fixture-vision','SEARCH_ENABLED':True}
        b = load_catalog(ROOT/'data/buildings.json')['A']
        resp = Mock(status_code=200)
        resp.__enter__ = Mock(return_value=resp)
        resp.__exit__ = Mock(return_value=False)
        post.return_value = resp
        resp.json.return_value = response()
        self.assertTrue(search_guide(cfg,b).sources)
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['model'],'qwen-plus')
        self.assertTrue(payload['parameters']['search_options']['forced_search'])
        self.assertTrue(payload['parameters']['search_options']['enable_source'])
        self.assertIn('中大院', payload['input']['messages'][1]['content'])
        resp.json.return_value = response('模型凭记忆回答，未检索到结果')
        with self.assertRaises(GuideError): search_guide(cfg,b)

    def test_ui_search_does_not_repeat_and_clears_on_building_change(self):
        cfg = {'API_KEY':'test-only','BASE_URL':'https://dashscope.aliyuncs.com/compatible-mode/v1',
               'MODEL_NAME':'fixture-vision','SEARCH_ENABLED':True}
        cards = load_catalog(ROOT/'data/buildings.json')
        with patch('ai_service.read_settings', return_value=cfg), patch('ai_service.chat_json',return_value={
                'coverage':'full','fact_ids':['origin','front']}), patch('search_service.search_guide') as search:
            search.return_value=SearchAnswer('联网测试补充', (WebResult('校史资料',URL,'',NOW),),NOW)
            a=AppTest.from_file(str(ROOT/'app.py')).run()
            a.radio(key='mode').set_value('真实 API').run()
            a.button(key='generate').click().run()
            key=next(b.key for b in a.button if str(b.key).startswith('web_'))
            a.button(key=key).click().run(); a.run()
            self.assertEqual(search.call_count,1)
            self.assertNotIn(key, [b.key for b in a.button])
            self.assertEqual(a.get('html')[0].proto.body.count(URL),1)
            self.assertIn('联网测试补充',[t.value for t in a.text])
            a.selectbox(key='manual').set_value('B').run()
            self.assertFalse(a.session_state.visit.web_answers)
            self.assertFalse(a.exception)

    def test_ui_failure_preserves_local_answer(self):
        cfg = {'API_KEY':'test-only','BASE_URL':'https://dashscope.aliyuncs.com/compatible-mode/v1',
               'MODEL_NAME':'fixture-vision','SEARCH_ENABLED':True}
        with patch('ai_service.read_settings', return_value=cfg), patch('ai_service.chat_json',return_value={
                'coverage':'full','fact_ids':['origin','front']}), patch('search_service.search_guide',side_effect=GuideError('搜索超时')) as search:
            a=AppTest.from_file(str(ROOT/'app.py')).run()
            a.radio(key='mode').set_value('真实 API').run(); a.button(key='generate').click().run()
            key=next(b.key for b in a.button if str(b.key).startswith('web_'))
            a.button(key=key).click().run(); a.run()
            self.assertEqual(search.call_count,1)
            self.assertTrue(a.session_state.visit.guides)
            self.assertFalse(a.session_state.visit.web_answers)
            self.assertTrue(any('搜索超时' in c.value for c in a.caption))
            self.assertFalse(a.button(key=key).disabled)
            self.assertFalse(a.exception)

#!/usr/bin/env python3
"""离线单元测试，覆盖 d-review 审查修复的 4 个点（无网络、无真实 codex 登录态）。

运行：python3 test_generate_image.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

_spec = importlib.util.spec_from_file_location(
    "gen", Path(__file__).with_name("generate_image.py")
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

LONG_B64 = "A" * 200  # 模拟一段足够长的 base64（>100 才被当作有效图）


class TestParseSse(unittest.TestCase):
    def test_single_line_data(self):
        text = 'data: {"a": 1}\n\ndata: {"b": 2}\n\n'
        self.assertEqual(gen.parse_sse(text), [{"a": 1}, {"b": 2}])

    def test_multiline_data_aggregated(self):
        # F3：一个事件块内多行 data 应聚合后再解析，而非逐行丢弃
        text = 'data: {"a":\ndata: 1}\n\ndata: {"b": 2}\n\n'
        self.assertEqual(gen.parse_sse(text), [{"a": 1}, {"b": 2}])

    def test_done_and_garbage_skipped(self):
        text = 'data: [DONE]\n\ndata: not-json\n\ndata: {"ok": true}\n\n'
        self.assertEqual(gen.parse_sse(text), [{"ok": True}])


class TestExtractImage(unittest.TestCase):
    def _final_event(self, result: str) -> str:
        return (
            'data: {"type":"response.output_item.done","item":'
            f'{{"type":"image_generation_call","result":"{result}"}}}}\n\n'
        )

    def _partial_event(self, b64: str) -> str:
        return (
            'data: {"type":"response.image_generation_call.partial_image",'
            f'"partial_image_b64":"{b64}"}}\n\n'
        )

    def test_returns_final(self):
        self.assertEqual(gen.extract_image_b64(self._final_event(LONG_B64)), LONG_B64)

    def test_failed_event_takes_priority_over_partial(self):
        # F2：先有 partial preview 再 response.failed，必须按失败处理，不返回 partial
        text = self._partial_event(LONG_B64) + (
            'data: {"type":"response.failed","response":{"error":{"message":"boom"}}}\n\n'
        )
        with self.assertRaises(SystemExit):
            gen.extract_image_b64(text)

    def test_partial_only_is_not_success(self):
        # F2：只有 partial、没有最终完成事件（如连接被截断）→ 失败，绝不写半成品
        with self.assertRaises(SystemExit):
            gen.extract_image_b64(self._partial_event(LONG_B64))

    def test_no_image_fails(self):
        with self.assertRaises(SystemExit):
            gen.extract_image_b64('data: {"type":"response.created"}\n\n')


class TestOpenaiSizeValidation(unittest.TestCase):
    def test_bad_size_rejected_before_network(self):
        # F4：openai 后端非法尺寸应在发请求前本地拒绝
        os.environ["OPENAI_API_KEY"] = "test-key"
        args = SimpleNamespace(
            images=[],
            background="auto",
            output_format="png",
            compression=None,
            size="123x123",  # 非 16 倍数，非法
            output="/tmp/should-not-be-written.png",
            overwrite=False,
        )
        # 若 validate_size 缺失，会进入网络调用而非 SystemExit
        with self.assertRaises(SystemExit):
            gen.run_openai(args)


class TestSaveTokensAtomic(unittest.TestCase):
    def test_merge_preserves_other_fields_and_perms(self):
        # F1：合并写回保留 codex 自有字段与未更新的 token，权限 0600
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            auth = home / "auth.json"
            auth.write_text(
                json.dumps(
                    {
                        "tokens": {"access_token": "old", "refresh_token": "r1"},
                        "OPENAI_API_KEY": "keep",
                        "auth_mode": "chatgpt",
                    }
                )
            )
            gen.save_tokens_merged(home, {"access_token": "new", "account_id": "acc"})
            data = json.loads(auth.read_text())
            self.assertEqual(data["tokens"]["access_token"], "new")
            self.assertEqual(data["tokens"]["refresh_token"], "r1")  # 未更新字段保留
            self.assertEqual(data["tokens"]["account_id"], "acc")
            self.assertEqual(data["OPENAI_API_KEY"], "keep")  # codex 自有字段保留
            self.assertEqual(data["auth_mode"], "chatgpt")
            self.assertEqual(stat.S_IMODE(auth.stat().st_mode), 0o600)

    def test_corrupt_file_not_overwritten(self):
        # F1：读不出当前内容时拒绝回写，不把损坏文件覆盖成缩水版
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            auth = home / "auth.json"
            auth.write_text("{ broken json")
            with self.assertRaises(SystemExit):
                gen.save_tokens_merged(home, {"access_token": "x"})
            self.assertEqual(auth.read_text(), "{ broken json")  # 原文件原样保留


if __name__ == "__main__":
    unittest.main(verbosity=2)

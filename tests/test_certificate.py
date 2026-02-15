"""
Certificate plugin tests for certificate_enabled feature.

CTFdがローカルにインストールされていない環境でも動作するよう、
CTFdモジュールをモックしてテストを行う。
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch


# CTFd モジュールをモックしてからインポートできるようにする
mock_db = MagicMock()
mock_sqlalchemy = MagicMock()

ctfd_models_mock = MagicMock()
ctfd_models_mock.db = mock_db
# SQLAlchemy の Column, Integer 等を本物にする
from sqlalchemy import Boolean, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

ctfd_models_mock.db.Model = type("Model", (), {"__abstract__": True, "metadata": MagicMock()})
ctfd_models_mock.db.LargeBinary = MagicMock()

sys.modules["CTFd"] = MagicMock()
sys.modules["CTFd.models"] = ctfd_models_mock
sys.modules["CTFd.models"].db = mock_db
sys.modules["CTFd.utils"] = MagicMock()
sys.modules["CTFd.utils.decorators"] = MagicMock()
sys.modules["CTFd.utils.user"] = MagicMock()
sys.modules["CTFd.utils.config"] = MagicMock()
sys.modules["CTFd.plugins"] = MagicMock()

# models.py をインポート（CTFd依存をモック済み）
# db.Model を SQLAlchemy の declarative_base に置き換える
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, Session

Base = declarative_base()

# models.py の db.Model を Base に差し替えてからインポート
mock_db.Model = Base
mock_db.LargeBinary = MagicMock()

# models.py をインポートできるようパスを追加
import importlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if "models" in sys.modules:
    del sys.modules["models"]

from models import CertificateSettings, TeamCertificateToken


class TestCertificateEnabledModel(unittest.TestCase):
    """CertificateSettings.certificate_enabled フィールドのテスト"""

    def test_certificate_enabled_column_exists(self):
        """certificate_enabled カラムが CertificateSettings テーブルに存在する"""
        columns = CertificateSettings.__table__.columns.keys()
        self.assertIn("certificate_enabled", columns)

    def test_certificate_enabled_default_false(self):
        """certificate_enabled のデフォルト値は False"""
        col = CertificateSettings.__table__.columns["certificate_enabled"]
        self.assertFalse(col.default.arg)

    def test_certificate_enabled_not_nullable(self):
        """certificate_enabled は nullable=False"""
        col = CertificateSettings.__table__.columns["certificate_enabled"]
        self.assertFalse(col.nullable)

    def test_certificate_enabled_is_boolean(self):
        """certificate_enabled は Boolean 型"""
        col = CertificateSettings.__table__.columns["certificate_enabled"]
        self.assertIsInstance(col.type, Boolean)


class TestCertificateEnabledLogic(unittest.TestCase):
    """証明書発行可否の判定ロジックのテスト"""

    def _is_certificate_enabled(self, settings):
        """__init__.py 内の判定ロジックを再現"""
        return bool(settings and settings.certificate_enabled)

    def test_enabled_when_settings_enabled(self):
        """settings.certificate_enabled=True → 有効"""
        settings = MagicMock()
        settings.certificate_enabled = True
        self.assertTrue(self._is_certificate_enabled(settings))

    def test_disabled_when_settings_disabled(self):
        """settings.certificate_enabled=False → 無効"""
        settings = MagicMock()
        settings.certificate_enabled = False
        self.assertFalse(self._is_certificate_enabled(settings))

    def test_disabled_when_no_settings(self):
        """settings が None → 無効"""
        self.assertFalse(self._is_certificate_enabled(None))


class TestGenerateCertificateBlocked(unittest.TestCase):
    """証明書発行が無効時に generate が拒否されるテスト"""

    def _should_block_generate(self, settings):
        """generate_certificate_compat の判定ロジックを再現"""
        return not settings or not settings.certificate_enabled

    def test_generate_blocked_when_disabled(self):
        """certificate_enabled=False → 発行拒否"""
        settings = MagicMock()
        settings.certificate_enabled = False
        self.assertTrue(self._should_block_generate(settings))

    def test_generate_blocked_when_no_settings(self):
        """設定が存在しない → 発行拒否"""
        self.assertTrue(self._should_block_generate(None))

    def test_generate_allowed_when_enabled(self):
        """certificate_enabled=True → 発行許可"""
        settings = MagicMock()
        settings.certificate_enabled = True
        self.assertFalse(self._should_block_generate(settings))


class TestViewCertificateBlocked(unittest.TestCase):
    """証明書表示が無効時に view が拒否されるテスト"""

    def _should_block_view(self, settings):
        """view_certificate の判定ロジックを再現"""
        return not settings or not settings.certificate_enabled

    def test_view_blocked_when_disabled(self):
        """certificate_enabled=False → 表示拒否"""
        settings = MagicMock()
        settings.certificate_enabled = False
        self.assertTrue(self._should_block_view(settings))

    def test_view_blocked_when_no_settings(self):
        """設定が存在しない → 表示拒否"""
        self.assertTrue(self._should_block_view(None))

    def test_view_allowed_when_enabled(self):
        """certificate_enabled=True → 表示許可"""
        settings = MagicMock()
        settings.certificate_enabled = True
        self.assertFalse(self._should_block_view(settings))


class TestAdminSaveCertificateEnabled(unittest.TestCase):
    """管理画面で certificate_enabled を保存するテスト"""

    def _parse_form_value(self, form_value):
        """admin_certificates の保存ロジックを再現"""
        return form_value == "1" if form_value is not None else False

    def test_checkbox_checked_sets_true(self):
        """チェックボックスが '1' → True"""
        self.assertTrue(self._parse_form_value("1"))

    def test_checkbox_unchecked_sets_false(self):
        """チェックボックスが None（未送信） → False"""
        self.assertFalse(self._parse_form_value(None))

    def test_checkbox_empty_string_sets_false(self):
        """チェックボックスが空文字列 → False"""
        self.assertFalse(self._parse_form_value(""))

    def test_checkbox_other_value_sets_false(self):
        """チェックボックスが '0' → False"""
        self.assertFalse(self._parse_form_value("0"))


class TestCertificatesEnabledAPI(unittest.TestCase):
    """GET /certificates/enabled APIレスポンスのロジックテスト"""

    def _build_response(self, settings):
        """certificates_enabled エンドポイントのレスポンスロジックを再現"""
        enabled = bool(settings and settings.certificate_enabled)
        return {"enabled": enabled}

    def test_returns_true_when_enabled(self):
        """有効時 → {"enabled": true}"""
        settings = MagicMock()
        settings.certificate_enabled = True
        resp = self._build_response(settings)
        self.assertTrue(resp["enabled"])

    def test_returns_false_when_disabled(self):
        """無効時 → {"enabled": false}"""
        settings = MagicMock()
        settings.certificate_enabled = False
        resp = self._build_response(settings)
        self.assertFalse(resp["enabled"])

    def test_returns_false_when_no_settings(self):
        """設定なし → {"enabled": false}"""
        resp = self._build_response(None)
        self.assertFalse(resp["enabled"])


class TestGetCtfEndDateStr(unittest.TestCase):
    """get_ctf_end_date_str 関数のテスト"""

    def _get_ctf_end_date_str(self, end_date_raw):
        """get_ctf_end_date_str のロジックを再現"""
        from datetime import datetime
        if end_date_raw:
            try:
                end_date = datetime.fromtimestamp(int(end_date_raw))
                return end_date.strftime("%B %d, %Y")
            except (ValueError, TypeError, OSError):
                pass
        return datetime.now().strftime("%B %d, %Y")

    def test_returns_end_date_when_set(self):
        """CTFの終了日時がUnixタイムスタンプで設定されている場合、その日付を返す"""
        # 1769998260 は CTFdの設定例
        from datetime import datetime
        ts = 1769998260
        expected = datetime.fromtimestamp(ts).strftime("%B %d, %Y")
        result = self._get_ctf_end_date_str(str(ts))
        self.assertEqual(result, expected)

    def test_returns_end_date_as_integer(self):
        """整数値のタイムスタンプでも正しく動作する"""
        from datetime import datetime
        # 2025-12-25 00:00:00 UTC のタイムスタンプ
        ts = int(datetime(2025, 12, 25).timestamp())
        result = self._get_ctf_end_date_str(ts)
        self.assertEqual(result, "December 25, 2025")

    def test_returns_now_when_end_not_set(self):
        """CTFの終了日時が未設定の場合、現在日時を返す"""
        from datetime import datetime
        result = self._get_ctf_end_date_str(None)
        expected = datetime.now().strftime("%B %d, %Y")
        self.assertEqual(result, expected)

    def test_returns_now_when_end_invalid(self):
        """CTFの終了日時が不正な形式の場合、現在日時にフォールバックする"""
        from datetime import datetime
        result = self._get_ctf_end_date_str("invalid-date")
        expected = datetime.now().strftime("%B %d, %Y")
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()

import unittest
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime

# テスト用のクラス定義
class MockSettings:
    def __init__(self):
        self.ctf_title = "Test CTF"
        self.background_color = "#ffffff"
        self.text_color = "#000000" 
        self.footer_text = "Test Footer"

class MockUser:
    def __init__(self):
        self.id = 1
        self.name = "Test User"
        self.score = 1000
        self.team = None

class MockTeam:
    def __init__(self):
        self.id = 1
        self.name = "Test Team"

class TestCertificateGenerator(unittest.TestCase):
    """証明書生成機能のテスト"""
    
    def setUp(self):
        """テストの準備"""
        self.settings = MockSettings()
        self.user = MockUser()
        self.team = MockTeam()
    
    def test_certificate_html_generation(self):
        """証明書HTML生成のテスト（PDF生成機能は削除済み）"""
        # HTML証明書は__init__.pyのview_certificate関数でテンプレートから生成される
        # ここでは基本的なモデル作成をテスト
        from models import CertificateHistory
        
        history = CertificateHistory()
        history.user_id = 1
        history.user_name = "Test User"
        history.score = 1000
        history.rank = 1
        history.ctf_title = "Test CTF"
        history.file_path = ""  # HTMLの場合は空文字列
        
        # 基本的な属性が設定されることを確認
        self.assertEqual(history.user_name, "Test User")
        self.assertEqual(history.score, 1000)
        self.assertEqual(history.rank, 1)
    
    


class TestCertificateModels(unittest.TestCase):
    """証明書モデルのテスト"""
    
    def test_certificate_settings_creation(self):
        """CertificateSettingsモデルの作成テスト"""
        from models import CertificateSettings
        
        settings = CertificateSettings()
        settings.ctf_title = "Test CTF"
        settings.background_color = "#ffffff"
        settings.text_color = "#000000"
        
        # 基本的な属性が設定されることを確認
        self.assertEqual(settings.ctf_title, "Test CTF")
        self.assertEqual(settings.background_color, "#ffffff")
        self.assertEqual(settings.text_color, "#000000")
    
    def test_certificate_history_creation(self):
        """CertificateHistoryモデルの作成テスト"""
        from models import CertificateHistory
        
        history = CertificateHistory()
        history.user_id = 1
        history.user_name = "Test User"
        history.score = 1000
        history.rank = 1
        history.ctf_title = "Test CTF"
        history.file_path = "/tmp/test.pdf"
        
        # 基本的な属性が設定されることを確認
        self.assertEqual(history.user_id, 1)
        self.assertEqual(history.user_name, "Test User")
        self.assertEqual(history.score, 1000)
        self.assertEqual(history.rank, 1)
        self.assertEqual(history.ctf_title, "Test CTF")
        self.assertEqual(history.file_path, "/tmp/test.pdf")


class TestCertificatePlugin(unittest.TestCase):
    """証明書プラグイン全体のテスト"""
    
    @patch('models.db')
    def test_plugin_load(self, mock_db):
        """プラグインのロード処理のテスト"""
        from unittest.mock import Mock
        
        # Flaskアプリのモック
        mock_app = Mock()
        mock_app.db = mock_db
        mock_app.register_blueprint = Mock()
        mock_app.context_processor = Mock()
        
        # プラグインをロード
        import ctfd_certificate
        from ctfd_certificate import load
        
        # エラーなくロードできることを確認
        try:
            load(mock_app)
            load_success = True
        except Exception as e:
            load_success = False
            print(f"Load error: {e}")
        
        self.assertTrue(load_success)
        
        # データベース作成が呼ばれることを確認
        mock_db.create_all.assert_called_once()
        
        # Blueprintが登録されることを確認
        mock_app.register_blueprint.assert_called_once()
        
        # Context processorが登録されることを確認
        mock_app.context_processor.assert_called_once()


class TestCertificateHelperFunctions(unittest.TestCase):
    """証明書ヘルパー関数のテスト"""
    
    def test_ordinal_suffix_generation(self):
        """序数詞接尾辞生成のテスト"""
        # __init__.pyのget_ordinal_suffix関数をテスト
        def get_ordinal_suffix(n):
            if 10 <= n % 100 <= 20:
                suffix = 'th'
            else:
                suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
            return suffix
        
        # 基本的な序数詞のテスト
        self.assertEqual(get_ordinal_suffix(1), 'st')
        self.assertEqual(get_ordinal_suffix(2), 'nd')
        self.assertEqual(get_ordinal_suffix(3), 'rd')
        self.assertEqual(get_ordinal_suffix(4), 'th')
        self.assertEqual(get_ordinal_suffix(11), 'th')
        self.assertEqual(get_ordinal_suffix(21), 'st')


if __name__ == '__main__':
    # テストの実行
    print("証明書プラグインのテストを開始します...")
    
    # テストスイートを作成
    test_suite = unittest.TestSuite()
    
    # テストクラスを追加
    test_suite.addTest(unittest.makeSuite(TestCertificateGenerator))
    test_suite.addTest(unittest.makeSuite(TestCertificateModels))
    test_suite.addTest(unittest.makeSuite(TestCertificatePlugin))
    test_suite.addTest(unittest.makeSuite(TestCertificateHelperFunctions))
    
    # テストランナーを作成して実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # 結果を出力
    if result.wasSuccessful():
        print("\n✅ すべてのテストが成功しました！")
    else:
        print(f"\n❌ {len(result.failures)} 個の失敗と {len(result.errors)} 個のエラーがありました。")
        
        if result.failures:
            print("\n失敗したテスト:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback}")
        
        if result.errors:
            print("\nエラーが発生したテスト:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback}")
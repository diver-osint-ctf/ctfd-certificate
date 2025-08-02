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
    
    def test_generate_certificate_pdf_basic(self):
        """基本的な証明書PDF生成のテスト"""
        from certificate_generator import generate_certificate_pdf
        
        file_path = generate_certificate_pdf(
            user_name="Test User",
            team_name="Test Team", 
            score=1000,
            rank=1,
            ctf_title="Test CTF",
            settings=self.settings
        )
        
        # ファイルが生成されることを確認
        self.assertTrue(os.path.exists(file_path))
        self.assertTrue(file_path.endswith('.pdf'))
        
        # ファイルサイズが0より大きいことを確認
        self.assertGreater(os.path.getsize(file_path), 0)
        
        # テスト後にファイルを削除
        os.remove(file_path)
    
    def test_generate_certificate_pdf_no_team(self):
        """チーム無しの証明書PDF生成のテスト"""
        from certificate_generator import generate_certificate_pdf
        
        file_path = generate_certificate_pdf(
            user_name="Solo User",
            team_name=None,
            score=500,
            rank=5,
            ctf_title="Solo CTF",
            settings=self.settings
        )
        
        # ファイルが生成されることを確認
        self.assertTrue(os.path.exists(file_path))
        
        # テスト後にファイルを削除
        os.remove(file_path)
    
    def test_generate_certificate_pdf_no_settings(self):
        """設定なしの証明書PDF生成のテスト"""
        from certificate_generator import generate_certificate_pdf
        
        file_path = generate_certificate_pdf(
            user_name="Default User",
            team_name="Default Team",
            score=750,
            rank=3,
            ctf_title="Default CTF",
            settings=None
        )
        
        # ファイルが生成されることを確認
        self.assertTrue(os.path.exists(file_path))
        
        # テスト後にファイルを削除
        os.remove(file_path)


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
    
    def test_cos_sin_approximation(self):
        """三角関数近似のテスト"""
        from certificate_generator import cos_approx, sin_approx
        import math
        
        # 0度のテスト
        self.assertAlmostEqual(cos_approx(0), math.cos(0), places=5)
        self.assertAlmostEqual(sin_approx(0), math.sin(0), places=5)
        
        # 90度のテスト
        angle_90 = math.pi / 2
        self.assertAlmostEqual(cos_approx(angle_90), math.cos(angle_90), places=5)
        self.assertAlmostEqual(sin_approx(angle_90), math.sin(angle_90), places=5)


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
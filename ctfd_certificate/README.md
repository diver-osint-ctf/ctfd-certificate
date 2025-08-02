# CTFd Certificate Generator Plugin

CTFdの参加者に証明書を発行するプラグインです。

## 機能

- ユーザーの成績（スコア、順位）に基づいた証明書の生成
- PDF形式での証明書ダウンロード
- 管理者による証明書デザインの設定
- 証明書生成履歴の管理

## インストール

1. このプラグインディレクトリを CTFd の `plugins` フォルダにコピーします：
   ```bash
   cp -r ctfd-certificate /path/to/CTFd/CTFd/plugins/
   ```

2. 必要な依存関係をインストールします：
   ```bash
   pip install reportlab
   ```

3. CTFdを再起動します。

## 使用方法

### 管理者

1. CTFd管理画面にログインします
2. プラグインページで証明書プラグインを有効化します
3. `/certificates/admin/settings` にアクセスして証明書の設定を行います：
   - CTFタイトル
   - 証明書のデザイン（色、フォント等）
   - フッターテキスト

### ユーザー

1. CTFに参加してスコアを獲得します
2. プロフィールページにアクセスします
3. 「証明書を生成」ボタンをクリックします
4. 生成された証明書をダウンロードします

## ファイル構成

```
ctfd-certificate/
├── __init__.py              # メインプラグインファイル
├── config.json              # プラグイン設定
├── requirements.txt         # 依存関係
├── models.py               # データベースモデル
├── certificate_generator.py # PDF生成機能
├── test_certificate.py     # テストファイル
├── templates/              # HTMLテンプレート
│   ├── certificate_admin.html
│   ├── certificate_button.html
│   └── certificate_history.html
└── assets/                 # CSS/JSファイル
    └── certificate.css
```

## API エンドポイント

- `POST /certificates/generate` - 証明書生成
- `GET /certificates/download/<id>` - 証明書ダウンロード
- `GET /certificates/history` - 証明書履歴
- `GET /certificates/admin/settings` - 管理設定画面

## データベーステーブル

### certificate_settings
証明書のデザイン設定を保存

| カラム名 | 型 | 説明 |
|---------|----|----|
| id | Integer | 主キー |
| ctf_title | String | CTFタイトル |
| template_type | String | テンプレートタイプ |
| background_color | String | 背景色 |
| text_color | String | 文字色 |
| footer_text | Text | フッターテキスト |

### certificate_history
証明書の生成履歴を保存

| カラム名 | 型 | 説明 |
|---------|----|----|
| id | Integer | 主キー |
| user_id | Integer | ユーザーID |
| team_id | Integer | チームID |
| user_name | String | ユーザー名 |
| team_name | String | チーム名 |
| score | Integer | スコア |
| rank | Integer | 順位 |
| ctf_title | String | CTFタイトル |
| file_path | String | PDFファイルパス |
| generated_at | DateTime | 生成日時 |

## テスト

テストを実行するには：

```bash
cd ctfd-certificate
python test_certificate.py
```

## 設定例

### 証明書設定の例

```json
{
  "ctf_title": "Security Competition 2024",
  "template_type": "modern",
  "background_color": "#f8f9fa",
  "text_color": "#2c3e50",
  "footer_text": "Certified by Security Academy"
}
```

## トラブルシューティング

### 証明書が生成されない場合

1. ユーザーにスコアがあることを確認
2. reportlabライブラリがインストールされていることを確認
3. 一時ディレクトリの書き込み権限を確認

### PDFダウンロードができない場合

1. 証明書ファイルが存在することを確認
2. ファイルパスが正しいことを確認
3. ウェブサーバーのファイル配信設定を確認

## 開発者向け情報

### カスタムテンプレートの追加

新しい証明書テンプレートを追加するには：

1. `certificate_generator.py` の `generate_certificate_pdf` 関数を修正
2. 新しいテンプレートタイプを `certificate_admin.html` に追加
3. 対応するCSS/JSを `assets/` に追加

### プラグインの拡張

- 証明書のロゴ画像対応
- 複数言語サポート
- メール自動送信機能
- QRコード付き証明書

## ライセンス

このプラグインはMITライセンスの下で公開されています。

## サポート

問題や質問がある場合は、GitHubのIssueまたはCTFdコミュニティフォーラムにお問い合わせください。
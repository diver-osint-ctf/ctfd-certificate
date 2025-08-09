# CTFd Certificate Generator Plugin

CTFdの参加者にHTML証明書を発行するプラグインです。

## 機能

- ユーザーの成績（スコア、順位）に基づいたHTML証明書の生成
- 美しいHTML証明書の表示（印刷/PDF保存対応）
- 管理者による証明書デザインの設定
- 証明書生成履歴の管理
- セキュアなチームトークンによる証明書アクセス管理
- Twitter共有機能付き

## インストール

1. このプラグインディレクトリを CTFd の `plugins` フォルダにコピーします：
   ```bash
   cp -r ctfd_certificate /path/to/CTFd/CTFd/plugins/
   ```

2. CTFdを再起動します。

## 使用方法

### 管理者

1. CTFd管理画面にログインします
2. `/admin/certificates` にアクセスして証明書の設定を行います：
   - CTFタイトル
   - 証明書のデザイン（背景色、文字色等）
   - フッターテキスト

### ユーザー

1. CTFに参加してスコアを獲得します
2. チームページ（`/team`）にアクセスします
3. 「証明書を生成」ボタンをクリックします
4. 生成されたHTML証明書が新しいタブで開きます
5. ブラウザの印刷機能でPDF保存や印刷が可能です
6. Twitter共有ボタンで成果をシェアできます

## ファイル構成

```
ctfd_certificate/
├── __init__.py              # メインプラグインファイル
├── config.json              # プラグイン設定
├── requirements.txt         # 依存関係（現在は不要）
├── models.py               # データベースモデル
├── test_certificate.py     # テストファイル
├── templates/              # HTMLテンプレート
│   ├── certificate_admin.html
│   ├── certificate_display.html
│   └── teams/
│       └── private.html
└── assets/                 # CSS/JSファイル
    └── certificate.css
```

## API エンドポイント

- `POST /certificates/generate` - 証明書生成
- `GET /certificates/<token>` - 証明書表示（チームトークン認証）
- `GET /certificates/history` - 証明書履歴
- `GET /admin/certificates` - 管理設定画面

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
| file_path | String | ファイルパス（HTML用は空文字列） |
| generated_at | DateTime | 生成日時 |

### team_certificate_tokens
チーム証明書アクセストークンを管理

| カラム名 | 型 | 説明 |
|---------|----|----|
| id | Integer | 主キー |
| team_id | Integer | チームID |
| token | String | アクセストークン（32文字） |
| created_at | DateTime | 作成日時 |
| updated_at | DateTime | 更新日時 |

## テスト

テストを実行するには：

```bash
cd ctfd_certificate
python test_certificate.py
```

## 設定例

### 証明書設定の例

```json
{
  "ctf_title": "Security Competition 2024",
  "template_type": "default",
  "background_color": "#ffffff",
  "text_color": "#1a365d",
  "footer_text": "Certified by Security Academy"
}
```

## 証明書の特徴

### デザイン
- プロフェッショナルなHTML証明書
- モダンなCSS3デザイン
- レスポンシブ対応（モバイルでも表示可能）
- 印刷最適化済み

### セキュリティ
- チーム固有のアクセストークンによる認証
- 証明書ごとの固有URL
- 不正アクセス防止

### 機能
- ブラウザ内印刷/PDF保存
- Twitter共有機能
- CTFロゴ表示対応
- 多言語対応の基盤

## トラブルシューティング

### 証明書が生成されない場合

1. ユーザーがチームに所属していることを確認
2. ユーザーにスコアがあることを確認
3. データベース接続を確認

### 証明書が表示されない場合

1. 証明書トークンが正しいことを確認
2. チームトークンが有効であることを確認
3. テンプレートファイルが存在することを確認

## 開発者向け情報

### カスタマイズ

証明書デザインをカスタマイズするには：

1. `templates/certificate_display.html` を編集
2. CSS スタイルを調整
3. 管理画面から設定可能な項目を追加する場合は `certificate_admin.html` も編集

### プラグインの拡張

今後の拡張候補：
- 複数の証明書テンプレート
- 多言語サポート
- メール自動送信機能
- QRコード付き証明書
- PDF直接生成機能の復活

## 技術仕様

- **フロントエンド**: HTML5, CSS3, JavaScript
- **バックエンド**: Python Flask (CTFd フレームワーク)
- **データベース**: SQLAlchemy ORM
- **認証**: チームトークンベース
- **デプロイ**: Docker対応

## ライセンス

このプラグインはMITライセンスの下で公開されています。

## サポート

問題や質問がある場合は、GitHubのIssueまたはCTFdコミュニティフォーラムにお問い合わせください。
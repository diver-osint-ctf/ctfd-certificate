from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
    make_response,
)
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.models import db, Users, Teams, Solves
from CTFd.utils import get_config
from CTFd.utils.user import get_current_user
from CTFd.plugins import register_plugin_assets_directory, register_plugin_script, register_plugin_stylesheet
from .models import CertificateSettings, TeamCertificateToken, generate_certificate_token
import os
import re
import base64
from datetime import datetime
from urllib.parse import quote


def get_certificate_logo_base64(settings=None):
    """
    証明書のロゴをbase64エンコードして取得

    将来的な拡張:
    - settingsオブジェクトに logo_data フィールドがあればそれを使用
    - なければデフォルトのロゴファイルを使用

    Args:
        settings: CertificateSettings オブジェクト (オプション)

    Returns:
        str: base64エンコードされたロゴ文字列、またはNone
    """
    try:
        # 将来的な拡張: データベースからロゴを取得
        # if settings and hasattr(settings, 'logo_data') and settings.logo_data:
        #     return base64.b64encode(settings.logo_data).decode('utf-8')

        # 現在: デフォルトのロゴファイルを使用
        logo_path = os.path.join(os.path.dirname(__file__), "assets", "default-logo.png")

        if os.path.exists(logo_path):
            with open(logo_path, "rb") as logo_file:
                logo_data = logo_file.read()
                encoded = base64.b64encode(logo_data).decode('utf-8')
                return encoded
        else:
            return None
    except Exception as e:
        return None


def load(app):
    # データベーステーブルを作成・マイグレーション
    try:
        # 手動でテーブル作成とカラム追加を実行
        from sqlalchemy import text

        with app.db.engine.connect() as conn:
            # 既存のテーブル構造を確認
            pass

        # 全テーブル作成
        app.db.create_all()

        # 色カラムのマイグレーション
        try:
            with app.db.engine.begin() as conn:
                # certificate_settingsテーブルの構造を確認
                result = conn.execute(text("DESCRIBE certificate_settings"))
                columns = [row[0] for row in result]

                # 新しい色カラムを追加
                color_columns = {
                    "border_color": "#FFD700",
                    "title_color": "#1a365d",
                    "ctf_title_color": "#B8860B",
                    "accent_color": "#B8860B",
                }

                for column_name, default_value in color_columns.items():
                    if column_name not in columns:
                        conn.execute(
                            text(
                                f"""
                            ALTER TABLE certificate_settings
                            ADD COLUMN {column_name} VARCHAR(7) DEFAULT '{default_value}'
                        """
                            )
                        )

                # 古いカラムを削除
                old_columns = [
                    "template_type",
                    "background_color",
                    "logo_path",
                ]
                for column_name in old_columns:
                    if column_name in columns:
                        conn.execute(
                            text(
                                f"ALTER TABLE certificate_settings DROP COLUMN {column_name}"
                            )
                        )

                # Refresh columns list after any drops
                result = conn.execute(text("DESCRIBE certificate_settings"))
                columns = [row[0] for row in result]

                new_columns = {
                    "text_color": "#2A2A2A",
                    "title_text": "CERTIFICATE OF PARTICIPATION",
                    "footer_text": "Congratulations on your outstanding performance.",
                    "competition_phrase": "international cybersecurity competition",
                }
                for column_name, default_value in new_columns.items():
                    if column_name not in columns:
                        col_type = (
                            "VARCHAR(255)"
                            if column_name != "text_color"
                            else "VARCHAR(7)"
                        )
                        conn.execute(
                            text(
                                f"ALTER TABLE certificate_settings ADD COLUMN {column_name} {col_type} DEFAULT '{default_value}'"
                            )
                        )
                        conn.execute(
                            text(
                                f"ALTER TABLE certificate_settings ADD COLUMN {column_name} {col_type} DEFAULT '{default_value}'"
                            )
                        )

                # specific migration for event_id
                if "event_id" not in columns:
                    conn.execute(
                        text("ALTER TABLE certificate_settings ADD COLUMN event_id VARCHAR(255) DEFAULT ''")
                    )

        except Exception as e:
            pass

    except Exception as e:
        pass

    # アセットディレクトリを登録
    try:
        register_plugin_assets_directory(
            app, base_path="/plugins/ctfd-certificate/assets/"
        )
    except Exception as e:
        pass

    # スクリプトを登録
    try:
        register_plugin_script("/plugins/ctfd-certificate/assets/certificate.js")
    except Exception as e:
        pass

    # スタイルシートを登録
    try:
        register_plugin_stylesheet("/plugins/ctfd-certificate/assets/certificate-tooltip.css")
    except Exception as e:
        pass

    # Blueprintを作成

    # Blueprintを作成
    certificate_blueprint = Blueprint(
        "certificate", __name__, template_folder="templates", static_folder="assets"
    )

    # 管理者用ルートをBlueprintに登録
    @certificate_blueprint.route("/admin/certificates", methods=["GET", "POST"])
    @admins_only
    def admin_certificates():
        """管理者用証明書設定画面"""
        if request.method == "POST":

            # CSRF nonce検証
            submitted_nonce = request.form.get("nonce")
            session_nonce = session.get("nonce")

            if not submitted_nonce or submitted_nonce != session_nonce:
                flash("CSRF token validation failed. Please try again.", "error")
                return redirect(url_for("certificate.admin_certificates"))

            # 設定を保存（エラーハンドリング付き）
            try:
                settings = CertificateSettings.query.first()
                if not settings:
                    settings = CertificateSettings()
                    db.session.add(settings)

                settings.ctf_title = request.form.get("ctf_title", "CTF Certificate")
                # New customizable fields
                settings.title_text = request.form.get(
                    "title_text", settings.title_text or "CERTIFICATE OF PARTICIPATION"
                )
                settings.footer_text = request.form.get(
                    "footer_text",
                    settings.footer_text
                    or "Congratulations on your outstanding performance.",
                )
                settings.competition_phrase = request.form.get(
                    "competition_phrase",
                    settings.competition_phrase
                    or "international cybersecurity competition",
                )
                settings.event_id = request.form.get("event_id", "")

                # ロゴサイズ・位置の設定
                logo_scale = request.form.get("logo_scale", "100")
                logo_offset_x = request.form.get("logo_offset_x", "0")
                logo_offset_y = request.form.get("logo_offset_y", "0")

                # 数値に変換（空文字列の場合はデフォルト値）
                try:
                    settings.logo_scale = int(logo_scale) if logo_scale else 100
                except ValueError:
                    settings.logo_scale = 100

                try:
                    settings.logo_offset_x = int(logo_offset_x) if logo_offset_x else 0
                except ValueError:
                    settings.logo_offset_x = 0

                try:
                    settings.logo_offset_y = int(logo_offset_y) if logo_offset_y else 0
                except ValueError:
                    settings.logo_offset_y = 0

                # ロゴファイルの処理
                reset_logo = request.form.get("reset_logo")
                if reset_logo == "1":
                    # デフォルトロゴにリセット
                    settings.logo_data = None
                    flash("Logo reset to default successfully", "success")
                elif "logo_file" in request.files:
                    logo_file = request.files["logo_file"]
                    if logo_file and logo_file.filename:
                        # ファイル形式チェック
                        allowed_extensions = {"png", "jpg", "jpeg"}
                        file_ext = logo_file.filename.rsplit(".", 1)[-1].lower()
                        if file_ext not in allowed_extensions:
                            flash("Invalid file format. Please upload PNG or JPG", "error")
                        else:
                            # ファイルサイズチェック（5MB）
                            logo_file.seek(0, 2)  # ファイルの最後に移動
                            file_size = logo_file.tell()
                            logo_file.seek(0)  # ファイルの先頭に戻る

                            if file_size > 5 * 1024 * 1024:
                                flash("File size must be less than 5MB", "error")
                            else:
                                # ファイルを読み込んでBLOBとして保存
                                logo_data = logo_file.read()
                                settings.logo_data = logo_data
                                flash(f"Logo uploaded successfully ({file_ext.upper()}, {file_size // 1024}KB)", "success")

                settings.updated_at = datetime.utcnow()

                db.session.commit()
                if not reset_logo and "logo_file" not in request.files:
                    flash("Certificate settings saved successfully", "success")
            except Exception as e:
                flash(
                    "Failed to save settings. Database migration may be required.",
                    "error",
                )

            return redirect(url_for("certificate.admin_certificates"))

        # 設定を取得（エラーハンドリング付き）
        try:
            settings = CertificateSettings.query.first()
            if not settings:
                settings = CertificateSettings()
                # CTFdの設定からタイトルを取得してデフォルト値に設定
                settings.ctf_title = get_config("ctf_name", "CTF Certificate")
        except Exception as e:
            # デフォルト設定でフォールバック
            ctf_name = get_config("ctf_name", "CTF Certificate")
            settings = type(
                "Settings",
                (),
                {
                    "ctf_title": ctf_name,
                    "border_color": "#FFD700",
                    "title_color": "#2D2D2D",
                    "ctf_title_color": "#C53030",
                    "accent_color": "#FFD700",
                },
            )()

        # CTFdの設定からタイトルを取得
        ctf_name_from_config = get_config("ctf_name", "CTF Certificate")

        # ロゴデータをbase64エンコード（テンプレートで使用）
        logo_data_base64 = None
        if settings and hasattr(settings, 'logo_data') and settings.logo_data:
            import base64
            logo_data_base64 = base64.b64encode(settings.logo_data).decode('utf-8')

        context = {
            "settings": settings,
            "nonce": session["nonce"],
            "ctf_name_from_config": ctf_name_from_config,
            "logo_data_base64": logo_data_base64,
        }
        return render_template("certificate_admin.html", **context)

    def get_ordinal_suffix(n):
        """数字に序数詞接尾辞を追加する（例: 1st, 2nd, 3rd, 4th）"""
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return suffix

    def _generate_certificate_pdf(certificate_data, logo_data_from_db, filename):
        """共通のPDF生成関数

        Args:
            certificate_data: テンプレートに渡すデータの辞書
            logo_data_from_db: データベースからのロゴデータ（バイナリ）、なければNone
            filename: 生成するPDFのファイル名

        Returns:
            PDFのFlask Response
        """
        # HTMLをレンダリング
        rendered_html = render_template("certificate_display.html", **certificate_data)

        # PDFを生成
        from weasyprint import HTML, CSS
        import urllib.parse

        # カスタムurl_fetcherを定義（ローカルファイルを読み込むため）
        plugin_dir = os.path.dirname(__file__)

        def custom_url_fetcher(url):
            """カスタムURL取得関数：ローカルファイルまたはデータベースから読み込む"""
            # データベースロゴの特別な処理
            if url.endswith('db-logo.png') or 'db-logo.png' in url:
                if logo_data_from_db:
                    return {
                        'string': logo_data_from_db,
                        'mime_type': 'image/png',
                        'redirected_url': url,
                        'filename': 'db-logo.png'
                    }
                else:
                    return None

            # 相対パスの場合、プラグインディレクトリからの相対パスとして解釈
            if not url.startswith(('http://', 'https://', 'file://', 'data:')):
                file_path = os.path.join(plugin_dir, url)
            elif url.startswith('file://'):
                # file:// URLの場合、パスを抽出
                file_path = urllib.parse.urlparse(url).path
            else:
                # HTTPやHTTPSの場合、デフォルトの挙動に委譲
                return weasyprint.default_url_fetcher(url)

            # ファイルを読み込む
            if os.path.exists(file_path):
                import mimetypes
                with open(file_path, 'rb') as f:
                    content = f.read()
                    # MIMEタイプを推測
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if not mime_type:
                        mime_type = 'application/octet-stream'
                    return {
                        'string': content,
                        'mime_type': mime_type,
                        'redirected_url': url,
                        'filename': os.path.basename(file_path)
                    }
            else:
                return None

        import weasyprint
        base_url = f"file://{plugin_dir}/"
        pdf = HTML(string=rendered_html, base_url=base_url, url_fetcher=custom_url_fetcher).write_pdf()

        # レスポンスを作成
        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response

    @certificate_blueprint.route("/certificates/<token>")
    def view_certificate(token):
        """トークンを用いて証明書を表示（ログイン不要、トークン必須）"""
        token_row = TeamCertificateToken.query.filter_by(token=token).first()
        if not token_row:
            from flask import abort
            abort(404)

        team = Teams.query.filter_by(id=token_row.team_id).first()
        team_name = team.name if team else None

        # チームのスコアと順位
        try:
            team_score = team.get_score(admin=False) if team else 0
        except Exception:
            team_score = 0

        try:
            from CTFd.utils.scores import get_team_standings
            standings = get_team_standings(admin=False)
            team_rank = next((i + 1 for i, s in enumerate(standings) if s.team_id == (team.id if team else -1)), 0)
        except Exception:
            # フォールバック: 全チームをスコア順に並べる
            all_teams = Teams.query.all()
            teams_with_scores = [(t, t.get_score(admin=False)) for t in all_teams]
            teams_with_scores = [(t, s) for t, s in teams_with_scores if s and s > 0]
            teams_with_scores.sort(key=lambda x: x[1], reverse=True)
            team_rank = next((i + 1 for i, (t, _) in enumerate(teams_with_scores) if t.id == (team.id if team else -1)), 0)

        # ロゴ
        logo_url = None
        try:
            logo_path = get_config("ctf_logo")
            if logo_path:
                logo_url = url_for("views.files", path=logo_path)
        except Exception as e:
            pass

        # 参加チーム総数
        try:
            total_teams = (
                db.session.query(Solves.team_id)
                .filter(Solves.team_id.isnot(None))
                .distinct()
                .count()
            )
            if not total_teams:
                total_teams = (
                    db.session.query(Solves.user_id)
                    .filter(Solves.user_id.isnot(None))
                    .distinct()
                    .count()
                )
            if not total_teams:
                total_teams = Teams.query.count() or Users.query.count()
        except Exception as e:
            total_teams = None

        # 設定
        try:
            settings = CertificateSettings.query.first()
        except Exception as e:
            settings = None

        # 証明書ロゴを取得（データベース優先、なければデフォルトファイル）
        logo_data_from_db = None
        if settings and hasattr(settings, 'logo_data') and settings.logo_data:
            logo_data_from_db = settings.logo_data

        # ロゴのパスまたはデータURIを設定
        if logo_data_from_db:
            # データベースにロゴがある場合、base64エンコードしてdata URIとして埋め込む
            import base64
            logo_base64 = base64.b64encode(logo_data_from_db).decode('utf-8')
            certificate_logo_path = f"data:image/png;base64,{logo_base64}"
        else:
            # デフォルトのロゴファイルを使用
            certificate_logo_path = "assets/default-logo.png"

        # 証明書データを準備
        certificate_data = {
            "user_name": None,
            "team_name": team_name,
            "score": team_score,
            "rank": team_rank,
            "ctf_title": (settings.ctf_title if settings else get_config("ctf_name", "CTF")),
            "logo_url": logo_url,
            "certificate_logo_path": certificate_logo_path,
            "text_color": "#111111",
            "title_text": (getattr(settings, "title_text", "CERTIFICATE OF PARTICIPATION") if settings else "CERTIFICATE OF PARTICIPATION"),
            "footer_text": (getattr(settings, "footer_text", "Congratulations on your outstanding performance.") if settings else "Congratulations on your outstanding performance."),
            "competition_phrase": (getattr(settings, "competition_phrase", "international cybersecurity competition") if settings else "international cybersecurity competition"),
            "event_id": (getattr(settings, "event_id", "") if settings else ""),
            "competition_date": datetime.now().strftime("%B %Y"),
            "issue_date": datetime.now().strftime("%B %d, %Y"),
            "get_ordinal_suffix": get_ordinal_suffix,
            "is_preview": False,
            "total_teams": total_teams,
            "border_color": (getattr(settings, "border_color", "#d4af37") if settings else "#d4af37"),
            "title_color": (getattr(settings, "title_color", "#d4af37") if settings else "#d4af37"),
            "ctf_title_color": (getattr(settings, "ctf_title_color", "#c8a64b") if settings else "#c8a64b"),
            "accent_color": (getattr(settings, "accent_color", "#c8a64b") if settings else "#c8a64b"),
            "logo_width": (200 * (getattr(settings, "logo_scale", 130) if settings else 130) // 100),
            "logo_offset_x": (getattr(settings, "logo_offset_x", 30) if settings else 30),
            "logo_offset_y": (getattr(settings, "logo_offset_y", -70) if settings else -70),
        }

        # ファイル名を生成
        ctf_title_val = settings.ctf_title if settings else get_config("ctf_name", "CTF")
        safe_ctf_title = re.sub(r'[^\w\-_]', '_', ctf_title_val)
        safe_team_name = re.sub(r'[^\w\-_]', '_', team_name or "unknown_team")
        filename = f"{safe_ctf_title}_{safe_team_name}_certificate.pdf"

        # 共通のPDF生成関数を使用
        return _generate_certificate_pdf(certificate_data, logo_data_from_db, filename)

    # Token generator: returns URL with token
    @certificate_blueprint.route("/certificates/generate", methods=["POST"])
    @authed_only
    def generate_certificate_compat():
        user = get_current_user()
        if not user:
            return jsonify({"error": "User not found"}), 400
        team = user.team if hasattr(user, "team") else None
        if not team:
            return jsonify({"error": "Users not in a team cannot generate certificates"}), 400

        # 既存のトークンを取得/作成
        token_row = TeamCertificateToken.query.filter_by(team_id=team.id).first()
        if not token_row:
            token_row = TeamCertificateToken(team_id=team.id)
            db.session.add(token_row)
            db.session.commit()

        return jsonify({
            "success": True,
            "view_url": url_for("certificate.view_certificate", token=token_row.token),
        })

    @certificate_blueprint.route("/admin/certificates/logo")
    @admins_only
    def get_certificate_logo():
        """管理者用：証明書ロゴを取得"""
        try:
            settings = CertificateSettings.query.first()
            if settings and hasattr(settings, 'logo_data') and settings.logo_data:
                # データベースからロゴを返す
                from flask import Response
                return Response(settings.logo_data, mimetype='image/png')
            else:
                # デフォルトロゴを返す
                default_logo_path = os.path.join(os.path.dirname(__file__), "assets", "default-logo.png")
                if os.path.exists(default_logo_path):
                    with open(default_logo_path, 'rb') as f:
                        from flask import Response
                        return Response(f.read(), mimetype='image/png')
                else:
                    from flask import abort
                    abort(404)
        except Exception as e:
            from flask import abort
            abort(500)

    @certificate_blueprint.route("/admin/certificates/sample-pdf")
    @admins_only
    def sample_certificate():
        """管理者用サンプル証明書PDF生成"""
        # 設定を取得
        try:
            settings = CertificateSettings.query.first()
        except Exception as e:
            settings = None

        # 証明書ロゴを取得（データベース優先、なければデフォルトファイル）
        logo_data_from_db = None
        if settings and hasattr(settings, 'logo_data') and settings.logo_data:
            logo_data_from_db = settings.logo_data

        # ロゴのパスを設定
        if logo_data_from_db:
            # データベースにロゴがある場合、base64エンコードしてdata URIとして埋め込む
            import base64
            logo_base64 = base64.b64encode(logo_data_from_db).decode('utf-8')
            certificate_logo_path = f"data:image/png;base64,{logo_base64}"
        else:
            certificate_logo_path = "assets/default-logo.png"

        # 参加チーム総数を取得
        try:
            total_teams = (
                db.session.query(Solves.team_id)
                .filter(Solves.team_id.isnot(None))
                .distinct()
                .count()
            )
            if not total_teams:
                total_teams = (
                    db.session.query(Solves.user_id)
                    .filter(Solves.user_id.isnot(None))
                    .distinct()
                    .count()
                )
            if not total_teams:
                total_teams = Teams.query.count() or Users.query.count()
        except Exception as e:
            total_teams = None

        # サンプルデータを準備
        certificate_data = {
            "user_name": None,
            "team_name": "Sample Team",
            "score": 1337,
            "rank": 1,
            "ctf_title": (settings.ctf_title if settings else get_config("ctf_name", "Sample CTF 2024")),
            "logo_url": None,
            "certificate_logo_path": certificate_logo_path,
            "text_color": "#111111",
            "title_text": (getattr(settings, "title_text", "CERTIFICATE OF PARTICIPATION") if settings else "CERTIFICATE OF PARTICIPATION"),
            "footer_text": (getattr(settings, "footer_text", "Congratulations on your outstanding performance.") if settings else "Congratulations on your outstanding performance."),
            "competition_phrase": (getattr(settings, "competition_phrase", "international cybersecurity competition") if settings else "international cybersecurity competition"),
            "event_id": (getattr(settings, "event_id", "") if settings else ""),
            "competition_date": datetime.now().strftime("%B %Y"),
            "issue_date": datetime.now().strftime("%B %d, %Y"),
            "get_ordinal_suffix": get_ordinal_suffix,
            "is_preview": False,
            "total_teams": total_teams,
            "border_color": (getattr(settings, "border_color", "#d4af37") if settings else "#d4af37"),
            "title_color": (getattr(settings, "title_color", "#d4af37") if settings else "#d4af37"),
            "ctf_title_color": (getattr(settings, "ctf_title_color", "#c8a64b") if settings else "#c8a64b"),
            "accent_color": (getattr(settings, "accent_color", "#c8a64b") if settings else "#c8a64b"),
            "logo_width": (200 * (getattr(settings, "logo_scale", 130) if settings else 130) // 100),
            "logo_offset_x": (getattr(settings, "logo_offset_x", 30) if settings else 30),
            "logo_offset_y": (getattr(settings, "logo_offset_y", -70) if settings else -70),
        }

        # ファイル名を生成
        ctf_title_val = settings.ctf_title if settings else get_config("ctf_name", "CTF")
        safe_ctf_title = re.sub(r'[^\w\-_]', '_', ctf_title_val)
        filename = f"sample_{safe_ctf_title}_admin_team_certificate.pdf"

        # 共通のPDF生成関数を使用
        return _generate_certificate_pdf(certificate_data, logo_data_from_db, filename)

    # Blueprintを登録
    app.register_blueprint(certificate_blueprint)

    # テンプレートディレクトリを追加で登録
    try:
        # CTFdアプリのテンプレートローダーを確認・拡張
        template_folder = os.path.join(os.path.dirname(__file__), "templates")
        if os.path.exists(template_folder):
            # テンプレートフォルダーを環境に追加
            if hasattr(app, "jinja_loader"):
                from jinja2 import ChoiceLoader, FileSystemLoader

                if isinstance(app.jinja_loader, ChoiceLoader):
                    app.jinja_loader.loaders.insert(
                        0, FileSystemLoader(template_folder)
                    )
                else:
                    # 単一のローダーの場合、ChoiceLoaderでラップして追加
                    app.jinja_loader = ChoiceLoader(
                        [FileSystemLoader(template_folder), app.jinja_loader]
                    )
    except Exception as e:
        pass

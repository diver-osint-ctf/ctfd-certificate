print("=== CTFd Certificate Plugin: Module is being imported! ===")

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
)
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.models import db, Users, Teams, Solves
from CTFd.utils import get_config
from CTFd.utils.user import get_current_user
from CTFd.plugins import register_plugin_assets_directory
from .models import CertificateSettings, TeamCertificateToken, generate_certificate_token
import os
from datetime import datetime


print("=== CTFd Certificate Plugin: All imports completed! ===")


def load(app):
    print("=== CTFd Certificate Plugin: Load function called! ===")

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
                print(f"Current certificate_settings columns: {columns}")

                # 新しい色カラムを追加
                color_columns = {
                    "border_color": "#FFD700",
                    "title_color": "#1a365d",
                    "ctf_title_color": "#B8860B",
                    "accent_color": "#B8860B",
                }

                for column_name, default_value in color_columns.items():
                    if column_name not in columns:
                        print(
                            f"Adding {column_name} column to certificate_settings table"
                        )
                        conn.execute(
                            text(
                                f"""
                            ALTER TABLE certificate_settings 
                            ADD COLUMN {column_name} VARCHAR(7) DEFAULT '{default_value}'
                        """
                            )
                        )
                        print(f"{column_name} column added successfully")

                # 古いカラムを削除
                old_columns = [
                    "template_type",
                    "background_color",
                    "logo_path",
                ]
                for column_name in old_columns:
                    if column_name in columns:
                        print(f"Removing deprecated {column_name} column")
                        conn.execute(
                            text(
                                f"ALTER TABLE certificate_settings DROP COLUMN {column_name}"
                            )
                        )
                        print(f"{column_name} column removed successfully")

                # Refresh columns list after any drops
                result = conn.execute(text("DESCRIBE certificate_settings"))
                columns = [row[0] for row in result]
                print(f"certificate_settings columns after cleanup: {columns}")

                new_columns = {
                    "text_color": "#2A2A2A",
                    "title_text": "CERTIFICATE OF EXCELLENCE",
                    "footer_text": "Congratulations on your outstanding performance.",
                    "competition_phrase": "international cybersecurity competition",
                }
                for column_name, default_value in new_columns.items():
                    if column_name not in columns:
                        print(
                            f"Adding new column {column_name} to certificate_settings"
                        )
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
                        print(f"{column_name} added")

        except Exception as e:
            print(f"Certificate settings migration error: {e}")


        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")

    # アセットディレクトリを登録
    try:
        register_plugin_assets_directory(
            app, base_path="/plugins/ctfd_certificate/assets/"
        )
        print("Asset directory registered successfully")
    except Exception as e:
        print(f"Error registering asset directory: {e}")

    # Blueprintを作成
    certificate_blueprint = Blueprint(
        "certificate", __name__, template_folder="templates", static_folder="assets"
    )

    # 管理者用ルートをBlueprintに登録
    @certificate_blueprint.route("/admin/certificates", methods=["GET", "POST"])
    @admins_only
    def admin_certificates():
        """管理者用証明書設定画面"""
        print(f"=== Admin certificates accessed: method={request.method} ===")
        print(f"Request form data: {dict(request.form)}")
        print(f"Request headers: {dict(request.headers)}")

        if request.method == "POST":
            print("=== POST request processing ===")

            # CSRF nonce検証
            submitted_nonce = request.form.get("nonce")
            session_nonce = session.get("nonce")

            if not submitted_nonce or submitted_nonce != session_nonce:
                flash("CSRF token validation failed. Please try again.", "error")
                print(
                    f"CSRF validation failed: submitted={submitted_nonce}, session={session_nonce}"
                )
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
                    "title_text", settings.title_text or "CERTIFICATE OF EXCELLENCE"
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
                settings.updated_at = datetime.utcnow()

                db.session.commit()
                flash("Certificate settings saved successfully", "success")
            except Exception as e:
                print(f"Settings save error: {e}")
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
            print(f"Settings query error: {e}")
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

        context = {
            "settings": settings,
            "nonce": session["nonce"],
            "ctf_name_from_config": ctf_name_from_config,
        }
        return render_template("certificate_admin.html", **context)

    def get_ordinal_suffix(n):
        """数字に序数詞接尾辞を追加する（例: 1st, 2nd, 3rd, 4th）"""
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return suffix

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
            print(f"Failed to get logo URL: {e}")

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
            print(f"Failed to compute total_teams: {e}")
            total_teams = None

        # 設定
        try:
            settings = CertificateSettings.query.first()
        except Exception as e:
            print(f"Settings query error in view_certificate: {e}")
            settings = None

        return render_template(
            "certificate_display.html",
            user_name=None,
            team_name=team_name,
            score=team_score,
            rank=team_rank,
            ctf_title=(settings.ctf_title if settings else get_config("ctf_name", "CTF")),
            logo_url=logo_url,
            text_color="#111111",
            title_text=(getattr(settings, "title_text", "CERTIFICATE OF EXCELLENCE") if settings else "CERTIFICATE OF EXCELLENCE"),
            footer_text=(getattr(settings, "footer_text", "Congratulations on your outstanding performance.") if settings else "Congratulations on your outstanding performance."),
            competition_phrase=(getattr(settings, "competition_phrase", "international cybersecurity competition") if settings else "international cybersecurity competition"),
            competition_date=datetime.now().strftime("%B %Y"),
            issue_date=datetime.now().strftime("%B %d, %Y"),
            get_ordinal_suffix=get_ordinal_suffix,
            is_preview=False,
            total_teams=total_teams,
        )

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

    @certificate_blueprint.route("/admin/certificates/preview")
    @admins_only
    def preview_certificate():
        """管理者用証明書プレビュー"""
        # プレビュー用のサンプルデータ
        sample_data = {
            "user_name": "Sample User",
            "team_name": "Sample Team",
            "score": 1337,
            "rank": 1,
            "ctf_title": "Sample CTF 2024",
            "logo_url": None,
            "footer_text": "Congratulations on your outstanding performance.",
            "competition_date": datetime.now().strftime("%B %Y"),
            "issue_date": datetime.now().strftime("%B %d, %Y"),
            "get_ordinal_suffix": get_ordinal_suffix,
            "title_text": "CERTIFICATE OF EXCELLENCE",
            "text_color": "#111111",
            "competition_phrase": "international cybersecurity competition",
            "is_preview": True,
            "total_teams": None,
        }

        # 現在の設定を適用（エラーハンドリング付き）
        try:
            # 同様に参加チーム総数を試算
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
                print(f"Failed to compute total_teams (preview): {e}")
                total_teams = None

            settings = CertificateSettings.query.first()
            if settings:
                sample_data["ctf_title"] = settings.ctf_title or "Sample CTF 2024"
                sample_data["text_color"] = "#111111"
                sample_data["title_text"] = (
                    getattr(settings, "title_text", "CERTIFICATE OF EXCELLENCE")
                    or "CERTIFICATE OF EXCELLENCE"
                )
                sample_data["footer_text"] = (
                    getattr(
                        settings,
                        "footer_text",
                        "Congratulations on your outstanding performance.",
                    )
                    or "Congratulations on your outstanding performance."
                )
                sample_data["competition_phrase"] = (
                    getattr(
                        settings,
                        "competition_phrase",
                        "international cybersecurity competition",
                    )
                    or "international cybersecurity competition"
                )
                sample_data["total_teams"] = total_teams
            else:
                sample_data["text_color"] = "#111111"
                sample_data["title_text"] = "CERTIFICATE OF EXCELLENCE"
                sample_data["footer_text"] = (
                    "Congratulations on your outstanding performance."
                )
                sample_data["competition_phrase"] = (
                    "international cybersecurity competition"
                )
                sample_data["total_teams"] = total_teams
        except Exception as e:
            print(f"Settings query error in preview: {e}")
            sample_data["text_color"] = "#111111"
            sample_data["title_text"] = "CERTIFICATE OF EXCELLENCE"
            sample_data["footer_text"] = (
                "Congratulations on your outstanding performance."
            )
            sample_data["competition_phrase"] = (
                "international cybersecurity competition"
            )
            # even on error, try a safe fallback (None -> 'many')
            sample_data["total_teams"] = None

        return render_template("certificate_display.html", **sample_data)

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
                    print(f"Template folder added: {template_folder}")
                else:
                    # 単一のローダーの場合、ChoiceLoaderでラップして追加
                    app.jinja_loader = ChoiceLoader(
                        [FileSystemLoader(template_folder), app.jinja_loader]
                    )
                    print(
                        f"Template loader wrapped and folder added: {template_folder}"
                    )

            print(f"Certificate plugin templates registered: {template_folder}")
    except Exception as e:
        print(f"Template registration error: {e}")

    # デバッグ: ルート登録後を確認
    print("CTFd Certificate Plugin: Routes registered")
    certificate_routes = [
        rule.rule for rule in app.url_map.iter_rules() if "certificate" in rule.rule
    ]
    print(f"App routes after: {certificate_routes}")
    print(f"Total certificate routes: {len(certificate_routes)}")
    print("Plugin loaded successfully!")

print("=== CTFd Certificate Plugin: Module is being imported! ===")

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.models import db, Users, Teams, Solves
from CTFd.utils import get_config
from CTFd.utils.user import get_current_user
from CTFd.plugins import register_plugin_assets_directory
from .models import CertificateSettings, CertificateHistory
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
            try:
                result = conn.execute(text("DESCRIBE certificate_history"))
                columns = [row[0] for row in result]
                print(f"Current certificate_history columns: {columns}")
                
                # certificate_tokenカラムが存在しない場合は追加
                if 'certificate_token' not in columns:
                    print("Adding certificate_token column to certificate_history table")
                    # まずはUNIQUE制約なしでカラムを追加
                    conn.execute(text("""
                        ALTER TABLE certificate_history 
                        ADD COLUMN certificate_token VARCHAR(32) DEFAULT NULL
                    """))
                    conn.commit()
                    print("certificate_token column added successfully")
                
            except Exception as e:
                print(f"Table might not exist yet: {e}")
        
        # 全テーブル作成
        app.db.create_all()
        
        # 既存のデータをマイグレーション
        from .models import CertificateHistory, TeamCertificateToken, generate_certificate_token
        
        try:
            # 新しいテーブル構造のための移行処理
            existing_teams_with_certs = app.db.session.query(CertificateHistory.team_id).filter(
                CertificateHistory.team_id.isnot(None)
            ).distinct().all()
            
            if existing_teams_with_certs:
                print(f"Creating team tokens for {len(existing_teams_with_certs)} teams...")
                for team_id_tuple in existing_teams_with_certs:
                    team_id = team_id_tuple[0]
                    
                    # チームトークンが既に存在するかチェック
                    existing_token = TeamCertificateToken.query.filter_by(team_id=team_id).first()
                    if not existing_token:
                        # 新しいチームトークンを作成
                        team_token = TeamCertificateToken(team_id=team_id)
                        app.db.session.add(team_token)
                
                app.db.session.commit()
                print("Team token migration completed")
                
        except Exception as e:
            print(f"Team token migration skipped due to error: {e}")
            
        # 古いcertificate_tokenカラムの削除は手動で行う
        try:
            with app.db.engine.connect() as conn:
                result = conn.execute(text("DESCRIBE certificate_history"))
                columns = [row[0] for row in result]
                
                if 'certificate_token' in columns:
                    print("Removing deprecated certificate_token column from certificate_history")
                    conn.execute(text("ALTER TABLE certificate_history DROP COLUMN certificate_token"))
                    conn.commit()
                    print("Deprecated column removed successfully")
        except Exception as e:
            print(f"Column removal skipped: {e}")
        
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
        "certificate",
        __name__,
        template_folder="templates",
        static_folder="assets"
    )
    
    # 管理者用ルートをBlueprintに登録
    @certificate_blueprint.route('/admin/certificates', methods=['GET', 'POST'])
    @admins_only
    def admin_certificates():
        """管理者用証明書設定画面"""
        print(f"=== Admin certificates accessed: method={request.method} ===")
        print(f"Request form data: {dict(request.form)}")
        print(f"Request headers: {dict(request.headers)}")
        
        if request.method == 'POST':
            print("=== POST request processing ===")
            # 設定を保存
            settings = CertificateSettings.query.first()
            if not settings:
                settings = CertificateSettings()
                db.session.add(settings)
            
            settings.ctf_title = request.form.get('ctf_title', 'CTF Certificate')
            settings.template_type = request.form.get('template_type', 'default')
            settings.background_color = request.form.get('background_color', '#ffffff')
            settings.text_color = request.form.get('text_color', '#000000')
            settings.footer_text = request.form.get('footer_text', '')
            settings.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('証明書設定が保存されました', 'success')
            return redirect(url_for('certificate.admin_certificates'))
        
        # 設定を取得
        settings = CertificateSettings.query.first()
        if not settings:
            settings = CertificateSettings()
        
        return render_template('certificate_admin.html', settings=settings)
    
    def get_ordinal_suffix(n):
        """数字に序数詞接尾辞を追加する（例: 1st, 2nd, 3rd, 4th）"""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return suffix
    
    @certificate_blueprint.route('/certificates/generate', methods=['POST'])
    @authed_only
    def generate_certificate():
        """証明書を生成（HTML表示に変更）"""
        user = get_current_user()
        if not user:
            return jsonify({'error': 'ユーザーが見つかりません'}), 400
        
        # ユーザーのスコアと順位を計算
        user_score = user.score
        team = user.team if hasattr(user, 'team') else None
        team_name = team.name if team else None
        
        # 順位を計算 - CTFdのget_user_standingsを使用
        try:
            from CTFd.utils.scores import get_user_standings
            standings = get_user_standings(admin=False)
            user_rank = next((i + 1 for i, standing in enumerate(standings) if standing.user_id == user.id), 0)
        except Exception as e:
            print(f"Failed to get user standings: {e}")
            # フォールバック: すべてのユーザーを取得してスコアで並び替え
            all_users = Users.query.all()
            users_with_scores = [(u, u.get_score(admin=False)) for u in all_users]
            users_with_scores = [(u, score) for u, score in users_with_scores if score and score > 0]
            users_with_scores.sort(key=lambda x: x[1], reverse=True)
            user_rank = next((i + 1 for i, (u, _) in enumerate(users_with_scores) if u.id == user.id), 0)
        
        # CTFタイトルを取得
        settings = CertificateSettings.query.first()
        ctf_title = settings.ctf_title if settings else get_config('ctf_name', 'CTF')
        
        try:
            if not team:
                return jsonify({'error': 'チームに所属していないユーザーは証明書を生成できません'}), 400
            
            # チームの既存証明書を削除（チームごとに1つのみ保持）
            existing_certificates = CertificateHistory.query.filter_by(team_id=team.id).all()
            for cert in existing_certificates:
                db.session.delete(cert)
            
            # チームトークンを取得または作成
            from .models import TeamCertificateToken
            team_token = TeamCertificateToken.query.filter_by(team_id=team.id).first()
            if not team_token:
                team_token = TeamCertificateToken(team_id=team.id)
                db.session.add(team_token)
            else:
                # 新しいトークンを生成（古いトークンを無効化）
                team_token.token = generate_certificate_token()
                team_token.updated_at = datetime.utcnow()
            
            # 新しい証明書を保存
            history = CertificateHistory(
                user_id=user.id,
                team_id=team.id,
                user_name=user.name,
                team_name=team_name,
                score=user_score,
                rank=user_rank,
                ctf_title=ctf_title,
                file_path=''  # HTMLの場合は空文字列
            )
            db.session.add(history)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'view_url': url_for('certificate.view_certificate', token=team_token.token)
            })
        
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Certificate generation failed: {error_details}")
            return jsonify({'error': f'証明書の生成に失敗しました: {str(e)}'}), 500
    
    @certificate_blueprint.route('/certificates/<token>')
    def view_certificate(token):
        """HTML証明書を表示（チームトークンベース認証）"""
        from .models import TeamCertificateToken
        
        # チームトークンから証明書を検索
        team_token = TeamCertificateToken.query.filter_by(token=token).first()
        if not team_token:
            from flask import abort
            abort(404)
        
        # そのチームの最新の証明書を取得
        certificate = CertificateHistory.query.filter_by(
            team_id=team_token.team_id
        ).order_by(CertificateHistory.generated_at.desc()).first()
        
        if not certificate:
            from flask import abort
            abort(404)
        
        # CTFロゴのURLを取得
        logo_url = None
        try:
            logo_path = get_config("ctf_logo")
            if logo_path:
                logo_url = url_for('views.files', path=logo_path)
        except Exception as e:
            print(f"Failed to get logo URL: {e}")
        
        # 設定を取得
        settings = CertificateSettings.query.first()
        
        return render_template('certificate_display.html',
            user_name=certificate.user_name,
            team_name=certificate.team_name,
            score=certificate.score,
            rank=certificate.rank,
            ctf_title=certificate.ctf_title,
            logo_url=logo_url,
            footer_text=settings.footer_text if settings else '',
            competition_date=datetime.now().strftime('%B %Y'),
            issue_date=certificate.generated_at.strftime('%B %d, %Y'),
            get_ordinal_suffix=get_ordinal_suffix
        )
    
    
    
    # Blueprintを登録
    app.register_blueprint(certificate_blueprint)
    
    # テンプレートディレクトリを追加で登録
    try:
        # CTFdアプリのテンプレートローダーを確認・拡張
        template_folder = os.path.join(os.path.dirname(__file__), 'templates')
        if os.path.exists(template_folder):
            # テンプレートフォルダーを環境に追加
            if hasattr(app, 'jinja_loader'):
                from jinja2 import ChoiceLoader, FileSystemLoader
                if isinstance(app.jinja_loader, ChoiceLoader):
                    app.jinja_loader.loaders.insert(0, FileSystemLoader(template_folder))
                    print(f"Template folder added: {template_folder}")
                else:
                    # 単一のローダーの場合、ChoiceLoaderでラップして追加
                    app.jinja_loader = ChoiceLoader([
                        FileSystemLoader(template_folder),
                        app.jinja_loader
                    ])
                    print(f"Template loader wrapped and folder added: {template_folder}")
            
            print(f"Certificate plugin templates registered: {template_folder}")
    except Exception as e:
        print(f"Template registration error: {e}")
    
    # デバッグ: ルート登録後を確認
    print("CTFd Certificate Plugin: Routes registered")
    certificate_routes = [rule.rule for rule in app.url_map.iter_rules() if 'certificate' in rule.rule]
    print(f"App routes after: {certificate_routes}")
    print(f"Total certificate routes: {len(certificate_routes)}")
    print("Plugin loaded successfully!")
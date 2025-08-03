print("=== CTFd Certificate Plugin: Module is being imported! ===")

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.models import db, Users, Teams, Solves
from CTFd.utils import get_config
from CTFd.utils.user import get_current_user
from CTFd.plugins import register_plugin_assets_directory
from .models import CertificateSettings, CertificateHistory
# PDF生成機能は動的インポートで遅延読み込み
# from .certificate_generator import generate_certificate_pdf
import os
from datetime import datetime

print("=== CTFd Certificate Plugin: All imports completed! ===")


def load(app):
    print("=== CTFd Certificate Plugin: Load function called! ===")
    
    # データベーステーブルを作成
    try:
        app.db.create_all()
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
    
    @certificate_blueprint.route('/certificates/generate', methods=['POST'])
    @authed_only
    def generate_certificate():
        """証明書を生成"""
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
        
        # 証明書を生成
        try:
            # reportlabの動的インポート
            from .certificate_generator import generate_certificate_pdf
            
            file_path = generate_certificate_pdf(
                user_name=user.name,
                team_name=team_name,
                score=user_score,
                rank=user_rank,
                ctf_title=ctf_title,
                settings=settings
            )
            
            # 履歴に保存
            history = CertificateHistory(
                user_id=user.id,
                team_id=team.id if team else None,
                user_name=user.name,
                team_name=team_name,
                score=user_score,
                rank=user_rank,
                ctf_title=ctf_title,
                file_path=file_path
            )
            db.session.add(history)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'download_url': url_for('certificate.download_certificate', cert_id=history.id)
            })
        
        except Exception as e:
            return jsonify({'error': f'証明書の生成に失敗しました: {str(e)}'}), 500
    
    @certificate_blueprint.route('/certificates/download/<int:cert_id>')
    @authed_only
    def download_certificate(cert_id):
        """証明書をダウンロード"""
        user = get_current_user()
        certificate = CertificateHistory.query.filter_by(
            id=cert_id,
            user_id=user.id
        ).first()
        
        if not certificate:
            flash('証明書が見つかりません', 'error')
            return redirect(url_for('users.private'))
        
        if not os.path.exists(certificate.file_path):
            flash('証明書ファイルが見つかりません', 'error')
            return redirect(url_for('users.private'))
        
        return send_file(
            certificate.file_path,
            as_attachment=True,
            download_name=f'certificate_{certificate.user_name}_{certificate.generated_at.strftime("%Y%m%d")}.pdf'
        )
    
    @certificate_blueprint.route('/certificates/history')
    @authed_only
    def certificate_history():
        """ユーザーの証明書履歴"""
        user = get_current_user()
        certificates = CertificateHistory.query.filter_by(user_id=user.id).order_by(
            CertificateHistory.generated_at.desc()
        ).all()
        
        return render_template('certificate_history.html', certificates=certificates)
    
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
    print(f"App routes after: {[rule.rule for rule in app.url_map.iter_rules() if 'certificate' in rule.rule]}")
    print("Plugin loaded successfully!")
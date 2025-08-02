from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
from CTFd.utils.decorators import admins_only, authed_only
from CTFd.models import db, Users, Teams, Solves
from CTFd.utils import get_config
from CTFd.utils.user import get_current_user
from CTFd.plugins import register_plugin_assets_directory
from .models import CertificateSettings, CertificateHistory
from .certificate_generator import generate_certificate_pdf
import os
from datetime import datetime


def load(app):
    # データベーステーブルを作成
    app.db.create_all()
    
    # アセットディレクトリを登録
    register_plugin_assets_directory(
        app, base_path="/plugins/ctfd-certificate/assets/"
    )
    
    # Blueprintを作成
    certificate_blueprint = Blueprint(
        "certificate",
        __name__,
        template_folder="templates",
        static_folder="assets",
        url_prefix="/certificates"
    )
    
    @certificate_blueprint.route('/admin/settings', methods=['GET', 'POST'])
    @admins_only
    def admin_settings():
        """管理者用証明書設定画面"""
        if request.method == 'POST':
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
            return redirect(url_for('certificate.admin_settings'))
        
        # 設定を取得
        settings = CertificateSettings.query.first()
        if not settings:
            settings = CertificateSettings()
        
        return render_template('certificate_admin.html', settings=settings)
    
    @certificate_blueprint.route('/generate', methods=['POST'])
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
        
        # 順位を計算（簡易版）
        users_by_score = Users.query.filter(Users.score > 0).order_by(Users.score.desc()).all()
        user_rank = next((i + 1 for i, u in enumerate(users_by_score) if u.id == user.id), 0)
        
        # CTFタイトルを取得
        settings = CertificateSettings.query.first()
        ctf_title = settings.ctf_title if settings else get_config('ctf_name', 'CTF')
        
        # 証明書を生成
        try:
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
    
    @certificate_blueprint.route('/download/<int:cert_id>')
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
    
    @certificate_blueprint.route('/history')
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
    
    # ユーザープロフィールページにボタンを追加するためのテンプレート拡張
    @app.context_processor
    def inject_certificate_button():
        def can_generate_certificate():
            user = get_current_user()
            if not user:
                return False
            # ユーザーがスコアを持っているかチェック
            return user.score > 0
        
        return dict(can_generate_certificate=can_generate_certificate)
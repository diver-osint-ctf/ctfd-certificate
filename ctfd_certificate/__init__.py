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


def load(app):
    # データベーステーブルを作成
    app.db.create_all()
    
    # アセットディレクトリを登録
    register_plugin_assets_directory(
        app, base_path="/plugins/ctfd_certificate/assets/"
    )
    
    # 管理者用ルートを直接アプリに登録
    @app.route('/admin/certificates', methods=['GET', 'POST'])
    @admins_only
    def admin_certificates():
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
            return redirect('/admin/certificates')
        
        # 設定を取得
        settings = CertificateSettings.query.first()
        if not settings:
            settings = CertificateSettings()
        
        return render_template('certificate_admin.html', settings=settings)
    
    # Blueprintを作成
    certificate_blueprint = Blueprint(
        "certificate",
        __name__,
        template_folder="templates",
        static_folder="assets",
        url_prefix="/certificates"
    )
    
    # 重複した管理者ルートを削除（上記で直接appに登録済み）
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
    
    # /teamページを直接オーバーライドして証明書機能を追加
    @app.route('/team')
    @authed_only
    def team_with_certificate():
        """チームページに証明書機能を含めたバージョン"""
        from CTFd.views.teams import private as original_team_view
        from flask import Response
        import re
        
        # 元のチームページのレスポンスを取得
        try:
            # 元のチームビューの処理を実行
            response = original_team_view()
            
            # レスポンスがstringの場合（テンプレートの場合）
            if isinstance(response, str):
                html_content = response
            elif hasattr(response, 'data'):
                html_content = response.data.decode('utf-8')
            else:
                html_content = str(response)
            
            # 証明書セクションのHTMLを追加
            certificate_section = '''
<!-- 証明書生成セクション -->
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<div class="row mt-4">
    <div class="col-md-12">
        <div class="card" style="border: 2px solid #007bff; border-radius: 10px;">
            <div class="card-header" style="background: linear-gradient(135deg, #007bff 0%, #0056b3 100%); color: white;">
                <h5 class="card-title mb-0">
                    <i class="fas fa-certificate"></i>
                    証明書
                </h5>
            </div>
            <div class="card-body">
                <p class="card-text">CTFの完了証明書を生成してダウンロードできます。</p>
                <button id="generate-certificate-btn" class="btn btn-primary">
                    <i class="fas fa-download"></i>
                    証明書を生成
                </button>
                <a href="/certificates/history" class="btn btn-outline-secondary ml-2">
                    <i class="fas fa-history"></i>
                    生成履歴
                </a>
            </div>
        </div>
    </div>
</div>

<!-- 証明書生成モーダル -->
<div class="modal fade" id="certificateModal" tabindex="-1" role="dialog" aria-labelledby="certificateModalLabel" aria-hidden="true">
    <div class="modal-dialog" role="document">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="certificateModalLabel">証明書生成</h5>
                <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
            <div class="modal-body">
                <div id="certificate-loading" style="display: none;">
                    <div class="text-center">
                        <div class="spinner-border text-primary" role="status">
                            <span class="sr-only">Loading...</span>
                        </div>
                        <p class="mt-2">証明書を生成中...</p>
                    </div>
                </div>
                <div id="certificate-success" style="display: none;">
                    <div class="alert alert-success">
                        <i class="fas fa-check-circle"></i>
                        証明書が正常に生成されました！
                    </div>
                    <p>証明書をダウンロードできます。</p>
                </div>
                <div id="certificate-error" style="display: none;">
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle"></i>
                        証明書の生成に失敗しました。
                    </div>
                    <p id="error-message"></p>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-dismiss="modal">閉じる</button>
                <a id="download-certificate-btn" href="#" class="btn btn-primary" style="display: none;">
                    <i class="fas fa-download"></i>
                    ダウンロード
                </a>
            </div>
        </div>
    </div>
</div>

<script>
$(document).ready(function() {
    $('#generate-certificate-btn').click(function() {
        $('#certificateModal').modal('show');
        $('#certificate-loading').show();
        $('#certificate-success, #certificate-error, #download-certificate-btn').hide();
        
        $.ajax({
            url: '/certificates/generate',
            method: 'POST',
            headers: {
                'X-CSRFToken': $('meta[name=csrf-token]').attr('content')
            },
            success: function(response) {
                $('#certificate-loading').hide();
                if (response.success) {
                    $('#certificate-success').show();
                    $('#download-certificate-btn').attr('href', response.download_url).show();
                } else {
                    $('#certificate-error').show();
                    $('#error-message').text(response.error || '不明なエラーが発生しました');
                }
            },
            error: function(xhr, status, error) {
                $('#certificate-loading').hide();
                $('#certificate-error').show();
                var errorMsg = 'サーバーエラーが発生しました';
                if (xhr.responseJSON && xhr.responseJSON.error) {
                    errorMsg = xhr.responseJSON.error;
                }
                $('#error-message').text(errorMsg);
            }
        });
    });
});
</script>
'''
            
            # HTMLコンテンツの最後（</body>タグ前）に証明書セクションを挿入
            if '</body>' in html_content:
                html_content = html_content.replace('</body>', certificate_section + '</body>')
            else:
                # </body>タグがない場合は末尾に追加
                html_content += certificate_section
            
            return Response(html_content, mimetype='text/html')
            
        except Exception as e:
            # エラーが発生した場合は元のビューを実行
            print(f"Certificate plugin error: {e}")
            return original_team_view()
    
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
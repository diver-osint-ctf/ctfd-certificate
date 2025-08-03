"""
CTFd Certificate Generator
PDF certificate generation functionality using ReportLab
"""

import os
import tempfile
from datetime import datetime
from io import BytesIO

# ReportLabの動的インポート
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import inch, cm
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_certificate_pdf(user_name, team_name, score, rank, ctf_title, settings=None):
    """
    PDF証明書を生成する（プロフェッショナルデザイン）
    
    Args:
        user_name (str): ユーザー名
        team_name (str): チーム名（Noneの場合は個人参加）
        score (int): スコア
        rank (int): 順位
        ctf_title (str): CTFのタイトル
        settings (CertificateSettings): 証明書設定オブジェクト
    
    Returns:
        str: 生成されたPDFファイルのパス
    
    Raises:
        ImportError: ReportLabが利用できない場合
        Exception: PDF生成に失敗した場合
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab library is not available. Please install reportlab>=3.6.0")
    
    # 設定の取得（デフォルト値を設定）
    template_type = settings.template_type if settings else 'default'
    background_color = HexColor(settings.background_color) if settings and settings.background_color else white
    text_color = HexColor(settings.text_color) if settings and settings.text_color else HexColor('#1a365d')  # Deep blue
    footer_text = settings.footer_text if settings and settings.footer_text else ''
    
    # 一時ファイルを作成
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"certificate_{user_name}_{timestamp}.pdf"
    file_path = os.path.join(temp_dir, filename)
    
    # PDF生成
    try:
        # A4横向きでマージンを調整
        doc = SimpleDocTemplate(
            file_path,
            pagesize=landscape(A4),
            rightMargin=1.5*cm,
            leftMargin=1.5*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )
        
        # ストーリー（PDFコンテンツ）を構築
        story = []
        styles = getSampleStyleSheet()
        
        # 証明書ボーダーを描画するためのカスタムDrawingクラス
        from reportlab.graphics.shapes import Drawing, Rect
        from reportlab.graphics import renderPDF
        
        # エレガントなボーダーの作成
        border_drawing = Drawing(25*cm, 18*cm)  # A4横向きサイズ
        
        # 外側のボーダー（太い線）
        border_drawing.add(Rect(0.3*cm, 0.3*cm, 24.4*cm, 17.4*cm, 
                               strokeColor=HexColor('#2c5282'), strokeWidth=3, fillColor=None))
        
        # 内側のボーダー（細い線）
        border_drawing.add(Rect(0.6*cm, 0.6*cm, 23.8*cm, 16.8*cm, 
                               strokeColor=HexColor('#4299e1'), strokeWidth=1, fillColor=None))
        
        # 装飾的なコーナー
        corner_size = 0.4*cm
        for x, y in [(0.6*cm, 16.8*cm), (23.8*cm, 16.8*cm), (0.6*cm, 0.6*cm), (23.8*cm, 0.6*cm)]:
            border_drawing.add(Rect(x-corner_size/2, y-corner_size/2, corner_size, corner_size,
                                   strokeColor=HexColor('#2c5282'), strokeWidth=2, fillColor=HexColor('#e6f3ff')))
        
        story.append(border_drawing)
        story.append(Spacer(1, -16*cm))  # ボーダーの上にコンテンツを配置
        
        # プロフェッショナルなスタイル定義
        cert_title_style = ParagraphStyle(
            'CertificateTitle',
            parent=styles['Title'],
            fontSize=36,
            spaceAfter=8,
            textColor=HexColor('#1a365d'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=20,
            textColor=HexColor('#4a5568'),
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        )
        
        ctf_title_style = ParagraphStyle(
            'CTFTitle',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=25,
            textColor=HexColor('#2c5282'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        presenter_style = ParagraphStyle(
            'Presenter',
            parent=styles['Normal'],
            fontSize=16,
            spaceAfter=10,
            textColor=HexColor('#4a5568'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        recipient_style = ParagraphStyle(
            'Recipient',
            parent=styles['Title'],
            fontSize=32,
            spaceAfter=15,
            textColor=HexColor('#1a365d'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        team_style = ParagraphStyle(
            'Team',
            parent=styles['Normal'],
            fontSize=18,
            spaceAfter=20,
            textColor=HexColor('#2c5282'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        achievement_style = ParagraphStyle(
            'Achievement',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=15,
            textColor=HexColor('#4a5568'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # 上部の余白
        story.append(Spacer(1, 1.5*cm))
        
        # 証明書タイトル
        story.append(Paragraph("CERTIFICATE", cert_title_style))
        story.append(Paragraph("OF EXCELLENCE", subtitle_style))
        
        # CTFタイトル
        story.append(Paragraph(ctf_title, ctf_title_style))
        
        # 授与文
        story.append(Paragraph("This certificate is proudly presented to", presenter_style))
        
        # 受賞者名（下線付き）
        story.append(Paragraph(f'<font color="#1a365d"><u>{user_name}</u></font>', recipient_style))
        
        # チーム名（該当する場合）
        if team_name:
            story.append(Paragraph(f"Member of Team: {team_name}", team_style))
        
        # 成果の説明
        story.append(Paragraph("for outstanding performance and dedication in cybersecurity challenges", achievement_style))
        
        # エレガントなアチーブメントボックス
        achievement_data = [
            ['Achievement Summary', ''],
            ['Final Score', f'{score} points'],
            ['Final Ranking', f'{rank}{_get_ordinal_suffix(rank)} place'],
            ['Competition Date', datetime.now().strftime('%B %Y')]
        ]
        
        achievement_table = Table(achievement_data, colWidths=[6*cm, 6*cm])
        achievement_table.setStyle(TableStyle([
            # ヘッダー行
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 16),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#1a365d')),
            ('SPAN', (0, 0), (1, 0)),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 15),
            
            # データ行
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 14),
            ('TEXTCOLOR', (0, 1), (0, -1), HexColor('#2c5282')),
            ('TEXTCOLOR', (1, 1), (1, -1), HexColor('#4a5568')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#f7fafc'), None]),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            
            # ボーダー
            ('BOX', (0, 0), (-1, -1), 2, HexColor('#2c5282')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, HexColor('#2c5282')),
            ('LINEBEFORE', (1, 1), (1, -1), 1, HexColor('#e2e8f0')),
        ]))
        
        story.append(Spacer(1, 10))
        story.append(achievement_table)
        story.append(Spacer(1, 20))
        
        # 署名欄とフッター
        signature_style = ParagraphStyle(
            'Signature',
            parent=styles['Normal'],
            fontSize=12,
            textColor=HexColor('#4a5568'),
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # 認証文
        story.append(Paragraph("This certificate validates the recipient's cybersecurity expertise", signature_style))
        story.append(Spacer(1, 15))
        
        # 署名欄のテーブル
        signature_data = [
            ['_' * 25, '_' * 25],
            ['Certificate Authority', 'Date of Issue'],
            ['', f"{datetime.now().strftime('%B %d, %Y')}"]
        ]
        
        signature_table = Table(signature_data, colWidths=[6*cm, 6*cm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), HexColor('#4a5568')),
            ('BOTTOMPADDING', (0, 0), (0, 0), 5),
            ('TOPPADDING', (0, 1), (-1, 1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 2),
        ]))
        
        story.append(signature_table)
        
        # フッターテキスト（管理者設定）
        if footer_text:
            footer_final_style = ParagraphStyle(
                'FooterFinal',
                parent=styles['Normal'],
                fontSize=10,
                textColor=HexColor('#4a5568'),
                alignment=TA_CENTER,
                fontName='Helvetica-Oblique'
            )
            story.append(Spacer(1, 10))
            story.append(Paragraph(footer_text, footer_final_style))
        
        # PDFをビルド
        doc.build(story)
        
        print(f"Certificate generated successfully: {file_path}")
        return file_path
        
    except Exception as e:
        # エラーが発生した場合、作成されたファイルを削除
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        raise Exception(f"Failed to generate PDF certificate: {str(e)}")


def _get_ordinal_suffix(n):
    """
    数字に序数詞接尾辞を追加する（例: 1st, 2nd, 3rd, 4th）
    
    Args:
        n (int): 数字
    
    Returns:
        str: 序数詞接尾辞
    """
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return suffix


def cleanup_old_certificates(max_age_days=30):
    """
    古い証明書ファイルをクリーンアップする
    
    Args:
        max_age_days (int): 保持期間（日数）
    """
    try:
        temp_dir = tempfile.gettempdir()
        current_time = datetime.now()
        
        for filename in os.listdir(temp_dir):
            if filename.startswith('certificate_') and filename.endswith('.pdf'):
                file_path = os.path.join(temp_dir, filename)
                try:
                    file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                    age_days = (current_time - file_time).days
                    
                    if age_days > max_age_days:
                        os.remove(file_path)
                        print(f"Cleaned up old certificate: {filename}")
                        
                except Exception as e:
                    print(f"Error cleaning up certificate {filename}: {e}")
                    
    except Exception as e:
        print(f"Error during certificate cleanup: {e}")


# テスト用関数
def test_certificate_generation():
    """証明書生成のテスト関数"""
    try:
        file_path = generate_certificate_pdf(
            user_name="Test User",
            team_name="Test Team",
            score=1500,
            rank=1,
            ctf_title="Test CTF 2024",
            settings=None
        )
        print(f"Test certificate generated: {file_path}")
        return file_path
    except Exception as e:
        print(f"Test failed: {e}")
        return None


if __name__ == "__main__":
    # テスト実行
    test_certificate_generation()
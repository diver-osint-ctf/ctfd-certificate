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
    PDF証明書を生成する
    
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
    text_color = HexColor(settings.text_color) if settings and settings.text_color else black
    footer_text = settings.footer_text if settings and settings.footer_text else ''
    
    # 一時ファイルを作成
    temp_dir = tempfile.gettempdir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"certificate_{user_name}_{timestamp}.pdf"
    file_path = os.path.join(temp_dir, filename)
    
    # PDF生成
    try:
        # A4横向き
        doc = SimpleDocTemplate(
            file_path,
            pagesize=landscape(A4),
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # ストーリー（PDFコンテンツ）を構築
        story = []
        styles = getSampleStyleSheet()
        
        # カスタムスタイルを作成（コンパクト版）
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=30,
            spaceAfter=15,
            textColor=text_color,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=12,
            textColor=text_color,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=8,
            textColor=text_color,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        
        # 証明書のタイトル
        story.append(Paragraph("Certificate of Achievement", title_style))
        story.append(Spacer(1, 12))
        
        # CTFタイトル
        story.append(Paragraph(f"<b>{ctf_title}</b>", heading_style))
        story.append(Spacer(1, 15))
        
        # 受賞者情報
        story.append(Paragraph("This is to certify that", normal_style))
        story.append(Spacer(1, 8))
        
        # ユーザー名（大きく表示）
        user_style = ParagraphStyle(
            'UserName',
            parent=styles['Title'],
            fontSize=26,
            spaceAfter=12,
            textColor=text_color,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph(f"<u>{user_name}</u>", user_style))
        
        # チーム名（該当する場合）
        if team_name:
            story.append(Paragraph(f"representing team <b>{team_name}</b>", normal_style))
            story.append(Spacer(1, 8))
        
        # 成績情報
        story.append(Paragraph("has successfully participated in this Capture The Flag competition", normal_style))
        story.append(Spacer(1, 12))
        
        # スコアと順位のテーブル
        if template_type == 'modern':
            # モダンスタイル: シンプルなレイアウト
            data = [
                ['Final Score:', f'{score} points'],
                ['Final Rank:', f'{rank}{_get_ordinal_suffix(rank)} place']
            ]
        else:
            # デフォルトスタイル: コンパクトなレイアウト（発行日は最下部に統一）
            data = [
                ['Achievement Details', ''],
                ['Final Score:', f'{score} points'],
                ['Final Rank:', f'{rank}{_get_ordinal_suffix(rank)} place']
            ]
        
        table = Table(data, colWidths=[7*cm, 7*cm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (-1, -1), text_color),
            ('GRID', (0, 1), (-1, -1), 1, text_color),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 15))
        
        # フッターテキストと発行日を統合してスペースを節約
        if footer_text:
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=10,
                textColor=text_color,
                alignment=TA_CENTER,
                fontName='Helvetica-Oblique',
                spaceAfter=8
            )
            story.append(Paragraph(footer_text, footer_style))
            story.append(Spacer(1, 8))
        
        # 発行日
        issue_date_style = ParagraphStyle(
            'IssueDate',
            parent=styles['Normal'],
            fontSize=9,
            textColor=text_color,
            alignment=TA_CENTER,
            fontName='Helvetica'
        )
        story.append(Paragraph(f"Issued on {datetime.now().strftime('%B %d, %Y')}", issue_date_style))
        
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
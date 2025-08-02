from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
import os
import tempfile
from datetime import datetime


def generate_certificate_pdf(user_name, team_name, score, rank, ctf_title, settings=None):
    """
    証明書PDFを生成する
    
    Args:
        user_name (str): ユーザー名
        team_name (str): チーム名
        score (int): スコア
        rank (int): 順位
        ctf_title (str): CTFのタイトル
        settings (CertificateSettings): 証明書設定
    
    Returns:
        str: 生成されたPDFファイルのパス
    """
    # 一時ファイルを作成
    temp_dir = tempfile.mkdtemp()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"certificate_{user_name}_{timestamp}.pdf"
    file_path = os.path.join(temp_dir, filename)
    
    # デフォルト設定
    bg_color = HexColor(settings.background_color if settings else '#ffffff')
    text_color = HexColor(settings.text_color if settings else '#000000')
    
    # PDFを作成（横向きA4）
    c = canvas.Canvas(file_path, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # 背景色を設定
    c.setFillColor(bg_color)
    c.rect(0, 0, width, height, fill=1)
    
    # 枠線を描画
    c.setStrokeColor(text_color)
    c.setLineWidth(3)
    margin = 30
    c.rect(margin, margin, width - 2*margin, height - 2*margin)
    
    # 装飾的な内側の枠線
    c.setLineWidth(1)
    inner_margin = margin + 15
    c.rect(inner_margin, inner_margin, width - 2*inner_margin, height - 2*inner_margin)
    
    # テキストの描画
    c.setFillColor(text_color)
    
    # タイトル
    c.setFont("Helvetica-Bold", 36)
    title_text = "Certificate of Achievement"
    title_width = c.stringWidth(title_text, "Helvetica-Bold", 36)
    c.drawString((width - title_width) / 2, height - 120, title_text)
    
    # CTFタイトル
    c.setFont("Helvetica-Bold", 24)
    ctf_width = c.stringWidth(ctf_title, "Helvetica-Bold", 24)
    c.drawString((width - ctf_width) / 2, height - 170, ctf_title)
    
    # "This certifies that" テキスト
    c.setFont("Helvetica", 16)
    certifies_text = "This certifies that"
    certifies_width = c.stringWidth(certifies_text, "Helvetica", 16)
    c.drawString((width - certifies_width) / 2, height - 220, certifies_text)
    
    # ユーザー名（大きく、太字）
    c.setFont("Helvetica-Bold", 28)
    user_width = c.stringWidth(user_name, "Helvetica-Bold", 28)
    c.drawString((width - user_width) / 2, height - 270, user_name)
    
    # チーム名（ある場合）
    if team_name:
        c.setFont("Helvetica", 18)
        team_text = f"Team: {team_name}"
        team_width = c.stringWidth(team_text, "Helvetica", 18)
        c.drawString((width - team_width) / 2, height - 310, team_text)
        y_offset = 350
    else:
        y_offset = 320
    
    # 成績情報
    c.setFont("Helvetica", 16)
    achievement_text = f"has successfully completed the challenges with a score of {score} points"
    achievement_width = c.stringWidth(achievement_text, "Helvetica", 16)
    c.drawString((width - achievement_width) / 2, height - y_offset, achievement_text)
    
    # 順位情報
    rank_text = f"achieving rank #{rank}"
    rank_width = c.stringWidth(rank_text, "Helvetica", 16)
    c.drawString((width - rank_width) / 2, height - y_offset - 30, rank_text)
    
    # 日付
    c.setFont("Helvetica", 14)
    date_text = f"Date: {datetime.now().strftime('%B %d, %Y')}"
    date_width = c.stringWidth(date_text, "Helvetica", 14)
    c.drawString((width - date_width) / 2, height - y_offset - 80, date_text)
    
    # フッターテキスト（設定がある場合）
    if settings and settings.footer_text:
        c.setFont("Helvetica", 10)
        footer_width = c.stringWidth(settings.footer_text, "Helvetica", 10)
        c.drawString((width - footer_width) / 2, 60, settings.footer_text)
    
    # 装飾的な要素を追加
    # 左上の星
    draw_star(c, 100, height - 100, 20, text_color)
    # 右上の星
    draw_star(c, width - 100, height - 100, 20, text_color)
    # 左下の星
    draw_star(c, 100, 100, 20, text_color)
    # 右下の星
    draw_star(c, width - 100, 100, 20, text_color)
    
    # PDFを保存
    c.save()
    
    return file_path


def draw_star(canvas, x, y, size, color):
    """星形を描画する補助関数"""
    canvas.setFillColor(color)
    canvas.setStrokeColor(color)
    
    # 簡単な星形を描画
    points = []
    for i in range(10):
        angle = i * 36 * 3.14159 / 180  # 36度ずつ回転
        if i % 2 == 0:
            # 外側の点
            px = x + size * 0.8 * cos_approx(angle)
            py = y + size * 0.8 * sin_approx(angle)
        else:
            # 内側の点
            px = x + size * 0.3 * cos_approx(angle)
            py = y + size * 0.3 * sin_approx(angle)
        points.extend([px, py])
    
    # パスを作成して描画
    path = canvas.beginPath()
    path.moveTo(points[0], points[1])
    for i in range(2, len(points), 2):
        path.lineTo(points[i], points[i+1])
    path.closePath()
    canvas.drawPath(path, fill=1, stroke=1)


def cos_approx(angle):
    """コサインの近似値"""
    import math
    return math.cos(angle)


def sin_approx(angle):
    """サインの近似値"""
    import math
    return math.sin(angle)
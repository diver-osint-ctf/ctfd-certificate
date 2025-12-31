from CTFd.models import db
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import secrets
import string


class CertificateSettings(db.Model):
    __tablename__ = "certificate_settings"

    id = Column(Integer, primary_key=True)
    ctf_title = Column(String(255), default="CTF Certificate", nullable=False)
    title_text = Column(String(255), default="CERTIFICATE OF PARTICIPATION", nullable=False)
    footer_text = Column(
        String(255), default="Congratulations on your outstanding performance.", nullable=False
    )
    competition_phrase = Column(
        String(255), default="international cybersecurity competition", nullable=False
    )
    event_id = Column(String(255), default="", nullable=True)
    logo_data = Column(db.LargeBinary, nullable=True)  # ロゴ画像データ（BLOB）
    logo_scale = Column(Integer, default=100, nullable=True)  # ロゴ拡大率（%、基準200px）
    logo_offset_x = Column(Integer, default=0, nullable=True)  # X軸オフセット（px）
    logo_offset_y = Column(Integer, default=0, nullable=True)  # Y軸オフセット（px）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def generate_certificate_token():
    """32文字のセキュアなランダムトークンを生成"""
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(32)
    )


class TeamCertificateToken(db.Model):
    """チームごとの証明書アクセストークン管理"""

    __tablename__ = "team_certificate_tokens"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), unique=True, nullable=False)
    token = Column(
        String(32), default=generate_certificate_token, unique=True, nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    team = relationship("Teams", backref="certificate_token")

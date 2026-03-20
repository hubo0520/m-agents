"""
认证 API 测试：登录、错误密码、Token 刷新、Token 过期、系统初始化
"""
import time
from datetime import timedelta

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token


class TestSetup:
    """系统初始化测试"""

    def test_setup_first_admin(self, client):
        """首次初始化应成功创建超级管理员"""
        resp = client.post("/api/auth/setup", json={
            "username": "first_admin",
            "display_name": "首位管理员",
            "password": "admin123456",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "first_admin"
        assert data["user"]["role"] == "admin"
        assert data["user"]["is_superadmin"] is True

    def test_setup_already_initialized(self, client, admin_user):
        """系统已初始化时再次调用 setup 应返回 403"""
        resp = client.post("/api/auth/setup", json={
            "username": "another_admin",
            "display_name": "另一个管理员",
            "password": "admin123456",
        })
        assert resp.status_code == 403

    def test_check_init_no_users(self, client):
        """无用户时 check-init 返回 initialized=False"""
        resp = client.get("/api/auth/check-init")
        assert resp.status_code == 200
        assert resp.json()["initialized"] is False

    def test_check_init_with_users(self, client, admin_user):
        """有用户时 check-init 返回 initialized=True"""
        resp = client.get("/api/auth/check-init")
        assert resp.status_code == 200
        assert resp.json()["initialized"] is True


class TestLogin:
    """登录测试"""

    def test_login_success(self, client, admin_user):
        """正确的用户名和密码应登录成功"""
        resp = client.post("/api/auth/login", json={
            "username": "test_admin",
            "password": "admin123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "test_admin"

    def test_login_wrong_password(self, client, admin_user):
        """错误密码应返回 401"""
        resp = client.post("/api/auth/login", json={
            "username": "test_admin",
            "password": "wrong_password",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """不存在的用户应返回 401"""
        resp = client.post("/api/auth/login", json={
            "username": "ghost_user",
            "password": "whatever",
        })
        assert resp.status_code == 401

    def test_login_disabled_user(self, client, db_session, admin_user):
        """被禁用的用户应返回 403"""
        admin_user.is_active = False
        db_session.flush()

        resp = client.post("/api/auth/login", json={
            "username": "test_admin",
            "password": "admin123",
        })
        assert resp.status_code == 403


class TestTokenRefresh:
    """Token 刷新测试"""

    def test_refresh_valid_token(self, client, admin_user):
        """使用有效的 Refresh Token 应成功获取新 Access Token"""
        # 先登录获取 refresh_token
        login_resp = client.post("/api/auth/login", json={
            "username": "test_admin",
            "password": "admin123",
        })
        refresh_token = login_resp.json()["refresh_token"]

        resp = client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_refresh_invalid_token(self, client):
        """无效的 Refresh Token 应返回 401"""
        resp = client.post("/api/auth/refresh", json={
            "refresh_token": "invalid.token.here",
        })
        assert resp.status_code == 401

    def test_refresh_with_access_token(self, client, admin_token):
        """使用 Access Token（而非 Refresh Token）应返回 401"""
        resp = client.post("/api/auth/refresh", json={
            "refresh_token": admin_token,
        })
        assert resp.status_code == 401

    def test_refresh_expired_token(self, client, admin_user):
        """过期的 Refresh Token 应返回 401"""
        payload = {
            "sub": str(admin_user.id),
            "username": admin_user.username,
            "role": admin_user.role,
        }
        expired_token = create_refresh_token(payload, expires_delta=timedelta(seconds=-1))

        resp = client.post("/api/auth/refresh", json={
            "refresh_token": expired_token,
        })
        assert resp.status_code == 401


class TestTokenExpiration:
    """Token 过期测试"""

    def test_expired_access_token_rejected(self, client, admin_user):
        """过期的 Access Token 应被拒绝"""
        payload = {
            "sub": str(admin_user.id),
            "username": admin_user.username,
            "role": admin_user.role,
        }
        expired_token = create_access_token(payload, expires_delta=timedelta(seconds=-1))

        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_valid_access_token_accepted(self, auth_client):
        """有效的 Access Token 可正常访问受保护的端点"""
        resp = auth_client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "test_admin"

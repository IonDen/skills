"""Tests for Account lifecycle service."""

from unittest.mock import Mock, call
import pytest
from fixture_d_account import Account, AccountRepo, Mailer, AccountService


@pytest.fixture
def mock_repo():
    return Mock(spec=AccountRepo)


@pytest.fixture
def mock_mailer():
    return Mock(spec=Mailer)


@pytest.fixture
def account_service(mock_repo, mock_mailer):
    return AccountService(mock_repo, mock_mailer)


class TestAccountService:
    def test_deactivate_active_account(self, account_service, mock_repo, mock_mailer):
        user_id = "user123"
        email = "user@example.com"
        account = Account(user_id=user_id, email=email, status="active")
        mock_repo.get.return_value = account

        account_service.deactivate(user_id)

        mock_repo.get.assert_called_once_with(user_id)
        mock_repo.set_status.assert_called_once_with(user_id, "inactive")
        mock_mailer.send_goodbye.assert_called_once_with(email)

    def test_deactivate_inactive_account(self, account_service, mock_repo, mock_mailer):
        user_id = "user123"
        email = "user@example.com"
        account = Account(user_id=user_id, email=email, status="inactive")
        mock_repo.get.return_value = account

        account_service.deactivate(user_id)

        mock_repo.get.assert_called_once_with(user_id)
        mock_repo.set_status.assert_not_called()
        mock_mailer.send_goodbye.assert_not_called()

    def test_deactivate_returns_none(self, account_service, mock_repo):
        account = Account(user_id="user123", email="user@example.com", status="active")
        mock_repo.get.return_value = account

        result = account_service.deactivate("user123")

        assert result is None

    def test_deactivate_calls_repo_get_first(self, account_service, mock_repo, mock_mailer):
        account = Account(user_id="user123", email="user@example.com", status="active")
        mock_repo.get.return_value = account

        account_service.deactivate("user123")

        call_order = []
        mock_repo.get.side_effect = lambda uid: (call_order.append("get"), account)[1]
        mock_repo.set_status.side_effect = lambda uid, status: call_order.append("set_status")

        account_service.deactivate("user123")

        assert call_order[0] == "get"

    def test_deactivate_with_different_user_ids(self, account_service, mock_repo, mock_mailer):
        account = Account(user_id="user456", email="another@example.com", status="active")
        mock_repo.get.return_value = account

        account_service.deactivate("user456")

        mock_repo.get.assert_called_with("user456")
        mock_repo.set_status.assert_called_with("user456", "inactive")
        mock_mailer.send_goodbye.assert_called_with("another@example.com")

    def test_deactivate_with_empty_user_id(self, account_service, mock_repo, mock_mailer):
        account = Account(user_id="", email="user@example.com", status="active")
        mock_repo.get.return_value = account

        account_service.deactivate("")

        mock_repo.get.assert_called_once_with("")
        mock_repo.set_status.assert_called_once_with("", "inactive")
        mock_mailer.send_goodbye.assert_called_once_with("user@example.com")


class TestAccount:
    def test_account_creation(self):
        account = Account(user_id="user123", email="user@example.com", status="active")

        assert account.user_id == "user123"
        assert account.email == "user@example.com"
        assert account.status == "active"

    def test_account_with_inactive_status(self):
        account = Account(user_id="user123", email="user@example.com", status="inactive")

        assert account.status == "inactive"

    def test_account_equality(self):
        account1 = Account(user_id="user123", email="user@example.com", status="active")
        account2 = Account(user_id="user123", email="user@example.com", status="active")

        assert account1 == account2

    def test_account_inequality(self):
        account1 = Account(user_id="user123", email="user@example.com", status="active")
        account2 = Account(user_id="user456", email="user@example.com", status="active")

        assert account1 != account2


class TestAccountRepo:
    def test_get_not_implemented(self):
        repo = AccountRepo()

        with pytest.raises(NotImplementedError, match="real DB access"):
            repo.get("user123")

    def test_set_status_not_implemented(self):
        repo = AccountRepo()

        with pytest.raises(NotImplementedError, match="real DB access"):
            repo.set_status("user123", "inactive")


class TestMailer:
    def test_send_goodbye_not_implemented(self):
        mailer = Mailer()

        with pytest.raises(NotImplementedError, match="real email send"):
            mailer.send_goodbye("user@example.com")

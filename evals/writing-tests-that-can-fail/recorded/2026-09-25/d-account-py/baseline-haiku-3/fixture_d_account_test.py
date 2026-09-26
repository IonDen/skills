"""Tests for account lifecycle service."""

import pytest
from unittest.mock import Mock, call

from fixture_d_account import Account, AccountRepo, Mailer, AccountService


class TestAccount:
    def test_account_creation(self):
        account = Account(user_id="u123", email="user@example.com", status="active")
        assert account.user_id == "u123"
        assert account.email == "user@example.com"
        assert account.status == "active"

    def test_account_with_inactive_status(self):
        account = Account(user_id="u456", email="inactive@example.com", status="inactive")
        assert account.status == "inactive"


class TestAccountRepo:
    def test_get_not_implemented(self):
        repo = AccountRepo()
        with pytest.raises(NotImplementedError):
            repo.get("u123")

    def test_set_status_not_implemented(self):
        repo = AccountRepo()
        with pytest.raises(NotImplementedError):
            repo.set_status("u123", "inactive")


class TestMailer:
    def test_send_goodbye_not_implemented(self):
        mailer = Mailer()
        with pytest.raises(NotImplementedError):
            mailer.send_goodbye("user@example.com")


class TestAccountService:
    @pytest.fixture
    def mock_repo(self):
        return Mock(spec=AccountRepo)

    @pytest.fixture
    def mock_mailer(self):
        return Mock(spec=Mailer)

    @pytest.fixture
    def service(self, mock_repo, mock_mailer):
        return AccountService(mock_repo, mock_mailer)

    def test_deactivate_active_account(self, service, mock_repo, mock_mailer):
        account = Account(user_id="u123", email="user@example.com", status="active")
        mock_repo.get.return_value = account

        service.deactivate("u123")

        mock_repo.get.assert_called_once_with("u123")
        mock_repo.set_status.assert_called_once_with("u123", "inactive")
        mock_mailer.send_goodbye.assert_called_once_with("user@example.com")

    def test_deactivate_already_inactive_account(self, service, mock_repo, mock_mailer):
        account = Account(user_id="u456", email="inactive@example.com", status="inactive")
        mock_repo.get.return_value = account

        service.deactivate("u456")

        mock_repo.get.assert_called_once_with("u456")
        mock_repo.set_status.assert_not_called()
        mock_mailer.send_goodbye.assert_not_called()

    def test_deactivate_calls_get_before_set_status(self, service, mock_repo, mock_mailer):
        account = Account(user_id="u789", email="test@example.com", status="active")
        mock_repo.get.return_value = account

        service.deactivate("u789")

        expected_calls = [call.get("u789"), call.set_status("u789", "inactive")]
        assert mock_repo.method_calls[:2] == expected_calls

    def test_deactivate_sends_email_to_correct_address(self, service, mock_repo, mock_mailer):
        account = Account(user_id="u999", email="specific@domain.com", status="active")
        mock_repo.get.return_value = account

        service.deactivate("u999")

        mock_mailer.send_goodbye.assert_called_once_with("specific@domain.com")

    def test_deactivate_multiple_accounts_sequentially(self, service, mock_repo, mock_mailer):
        account1 = Account(user_id="u1", email="user1@example.com", status="active")
        account2 = Account(user_id="u2", email="user2@example.com", status="active")
        mock_repo.get.side_effect = [account1, account2]

        service.deactivate("u1")
        service.deactivate("u2")

        assert mock_repo.get.call_count == 2
        assert mock_repo.set_status.call_count == 2
        assert mock_mailer.send_goodbye.call_count == 2

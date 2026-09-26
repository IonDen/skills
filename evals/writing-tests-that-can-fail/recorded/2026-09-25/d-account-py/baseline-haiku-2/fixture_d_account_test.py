"""Tests for account lifecycle service."""

import pytest
from unittest.mock import Mock, MagicMock

from fixture_d_account import Account, AccountRepo, Mailer, AccountService


class TestAccount:
    """Tests for Account dataclass."""

    def test_account_creation(self):
        account = Account(user_id="user123", email="user@example.com", status="active")
        assert account.user_id == "user123"
        assert account.email == "user@example.com"
        assert account.status == "active"

    def test_account_with_inactive_status(self):
        account = Account(user_id="user456", email="inactive@example.com", status="inactive")
        assert account.status == "inactive"

    def test_account_is_dataclass(self):
        account = Account(user_id="user1", email="test@example.com", status="active")
        assert hasattr(account, "__dataclass_fields__")


class TestAccountRepo:
    """Tests for AccountRepo base class."""

    def test_get_not_implemented(self):
        repo = AccountRepo()
        with pytest.raises(NotImplementedError, match="real DB access"):
            repo.get("user123")

    def test_set_status_not_implemented(self):
        repo = AccountRepo()
        with pytest.raises(NotImplementedError, match="real DB access"):
            repo.set_status("user123", "inactive")


class TestMailer:
    """Tests for Mailer base class."""

    def test_send_goodbye_not_implemented(self):
        mailer = Mailer()
        with pytest.raises(NotImplementedError, match="real email send"):
            mailer.send_goodbye("user@example.com")


class TestAccountService:
    """Tests for AccountService."""

    def test_initialization(self):
        repo = Mock(spec=AccountRepo)
        mailer = Mock(spec=Mailer)
        service = AccountService(repo, mailer)
        assert service._repo is repo
        assert service._mailer is mailer

    def test_deactivate_active_account(self):
        repo = Mock(spec=AccountRepo)
        mailer = Mock(spec=Mailer)
        account = Account(user_id="user123", email="user@example.com", status="active")
        repo.get.return_value = account

        service = AccountService(repo, mailer)
        service.deactivate("user123")

        repo.get.assert_called_once_with("user123")
        repo.set_status.assert_called_once_with("user123", "inactive")
        mailer.send_goodbye.assert_called_once_with("user@example.com")

    def test_deactivate_inactive_account_skips_status_and_email(self):
        repo = Mock(spec=AccountRepo)
        mailer = Mock(spec=Mailer)
        account = Account(user_id="user456", email="inactive@example.com", status="inactive")
        repo.get.return_value = account

        service = AccountService(repo, mailer)
        service.deactivate("user456")

        repo.get.assert_called_once_with("user456")
        repo.set_status.assert_not_called()
        mailer.send_goodbye.assert_not_called()

    def test_deactivate_calls_get_with_correct_user_id(self):
        repo = Mock(spec=AccountRepo)
        mailer = Mock(spec=Mailer)
        account = Account(user_id="user789", email="user789@example.com", status="active")
        repo.get.return_value = account

        service = AccountService(repo, mailer)
        service.deactivate("user789")

        repo.get.assert_called_once_with("user789")

    def test_deactivate_order_of_operations(self):
        """Ensure get is called before set_status and send_goodbye."""
        repo = Mock(spec=AccountRepo)
        mailer = Mock(spec=Mailer)
        account = Account(user_id="user100", email="user100@example.com", status="active")
        repo.get.return_value = account

        call_order = []
        repo.get.side_effect = lambda user_id: (call_order.append("get"), account)[1]
        repo.set_status.side_effect = lambda uid, status: call_order.append("set_status")
        mailer.send_goodbye.side_effect = lambda email: call_order.append("send_goodbye")

        service = AccountService(repo, mailer)
        service.deactivate("user100")

        assert call_order == ["get", "set_status", "send_goodbye"]

    def test_deactivate_preserves_email_for_inactive_check(self):
        """Verify the email is available when checking inactive status."""
        repo = Mock(spec=AccountRepo)
        mailer = Mock(spec=Mailer)
        email = "test@example.com"
        account = Account(user_id="user200", email=email, status="active")
        repo.get.return_value = account

        service = AccountService(repo, mailer)
        service.deactivate("user200")

        mailer.send_goodbye.assert_called_once_with(email)

    def test_deactivate_multiple_calls_on_same_user(self):
        """Test deactivating the same user multiple times."""
        repo = Mock(spec=AccountRepo)
        mailer = Mock(spec=Mailer)

        active_account = Account(user_id="user300", email="user300@example.com", status="active")
        inactive_account = Account(user_id="user300", email="user300@example.com", status="inactive")
        repo.get.side_effect = [active_account, inactive_account]

        service = AccountService(repo, mailer)

        service.deactivate("user300")
        assert repo.set_status.call_count == 1
        assert mailer.send_goodbye.call_count == 1

        service.deactivate("user300")
        assert repo.set_status.call_count == 1
        assert mailer.send_goodbye.call_count == 1

    def test_deactivate_with_different_users(self):
        """Test deactivating different users."""
        repo = Mock(spec=AccountRepo)
        mailer = Mock(spec=Mailer)

        user1_account = Account(user_id="user1", email="user1@example.com", status="active")
        user2_account = Account(user_id="user2", email="user2@example.com", status="active")
        repo.get.side_effect = [user1_account, user2_account]

        service = AccountService(repo, mailer)

        service.deactivate("user1")
        service.deactivate("user2")

        assert repo.get.call_count == 2
        assert repo.set_status.call_count == 2
        assert mailer.send_goodbye.call_count == 2
        mailer.send_goodbye.assert_any_call("user1@example.com")
        mailer.send_goodbye.assert_any_call("user2@example.com")

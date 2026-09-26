"""Test suite for Account lifecycle service."""

from unittest.mock import MagicMock, call

import pytest

from fixture_d_account import Account, AccountService, AccountRepo, Mailer


@pytest.fixture
def mock_repo():
    """Mock AccountRepo dependency."""
    return MagicMock(spec=AccountRepo)


@pytest.fixture
def mock_mailer():
    """Mock Mailer dependency."""
    return MagicMock(spec=Mailer)


@pytest.fixture
def service(mock_repo, mock_mailer):
    """AccountService with mocked dependencies."""
    return AccountService(repo=mock_repo, mailer=mock_mailer)


class TestAccountServiceDeactivate:
    """Test suite for AccountService.deactivate method."""

    def test_deactivate_active_account_changes_status(self, service, mock_repo, mock_mailer):
        """Deactivating an active account sets status to inactive."""
        user_id = "user123"
        account = Account(user_id=user_id, email="user@example.com", status="active")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        mock_repo.set_status.assert_called_once_with(user_id, "inactive")

    def test_deactivate_active_account_sends_goodbye_email(self, service, mock_repo, mock_mailer):
        """Deactivating an active account sends goodbye email."""
        user_id = "user123"
        email = "user@example.com"
        account = Account(user_id=user_id, email=email, status="active")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        mock_mailer.send_goodbye.assert_called_once_with(email)

    def test_deactivate_active_account_repo_before_mailer(self, service, mock_repo, mock_mailer):
        """Repo is updated before mailer is called."""
        user_id = "user123"
        account = Account(user_id=user_id, email="user@example.com", status="active")
        mock_repo.get.return_value = account
        call_order = []

        def track_repo_call(*args, **kwargs):
            call_order.append("repo")

        def track_mailer_call(*args, **kwargs):
            call_order.append("mailer")

        mock_repo.set_status.side_effect = track_repo_call
        mock_mailer.send_goodbye.side_effect = track_mailer_call

        service.deactivate(user_id)

        assert call_order == ["repo", "mailer"]

    def test_deactivate_inactive_account_returns_early(self, service, mock_repo, mock_mailer):
        """Deactivating an already inactive account does nothing."""
        user_id = "user123"
        account = Account(user_id=user_id, email="user@example.com", status="inactive")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        mock_repo.set_status.assert_not_called()
        mock_mailer.send_goodbye.assert_not_called()

    def test_deactivate_retrieves_account_by_user_id(self, service, mock_repo, mock_mailer):
        """Deactivate retrieves the account using the provided user_id."""
        user_id = "user456"
        account = Account(user_id=user_id, email="user@example.com", status="active")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        mock_repo.get.assert_called_once_with(user_id)

    def test_deactivate_uses_correct_email_from_account(self, service, mock_repo, mock_mailer):
        """Goodbye email is sent to the account's email address."""
        user_id = "user123"
        correct_email = "correct@example.com"
        account = Account(user_id=user_id, email=correct_email, status="active")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        mock_mailer.send_goodbye.assert_called_once_with(correct_email)

    def test_deactivate_different_user_ids(self, service, mock_repo, mock_mailer):
        """Multiple calls with different user_ids are handled correctly."""
        account1 = Account(user_id="user1", email="user1@example.com", status="active")
        account2 = Account(user_id="user2", email="user2@example.com", status="active")
        mock_repo.get.side_effect = [account1, account2]

        service.deactivate("user1")
        service.deactivate("user2")

        assert mock_repo.get.call_count == 2
        assert mock_repo.set_status.call_count == 2
        assert mock_mailer.send_goodbye.call_count == 2
        mock_mailer.send_goodbye.assert_any_call("user1@example.com")
        mock_mailer.send_goodbye.assert_any_call("user2@example.com")

    def test_deactivate_with_empty_string_user_id(self, service, mock_repo, mock_mailer):
        """Deactivate handles empty string user_id by delegating to repo."""
        account = Account(user_id="", email="user@example.com", status="active")
        mock_repo.get.return_value = account

        service.deactivate("")

        mock_repo.get.assert_called_once_with("")
        mock_repo.set_status.assert_called_once_with("", "inactive")

    def test_deactivate_preserves_user_id_through_lifecycle(self, service, mock_repo, mock_mailer):
        """User ID remains consistent from get to set_status."""
        user_id = "user123"
        account = Account(user_id=user_id, email="user@example.com", status="active")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        get_call = mock_repo.get.call_args
        set_call = mock_repo.set_status.call_args
        assert get_call[0][0] == user_id
        assert set_call[0][0] == user_id

    def test_deactivate_inactive_status_case_sensitive(self, service, mock_repo, mock_mailer):
        """Status check is case-sensitive; 'Inactive' is not 'inactive'."""
        user_id = "user123"
        account = Account(user_id=user_id, email="user@example.com", status="Inactive")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        # Status is "Inactive" not "inactive", so it should deactivate
        mock_repo.set_status.assert_called_once_with(user_id, "inactive")
        mock_mailer.send_goodbye.assert_called_once()

    def test_deactivate_with_special_characters_in_email(self, service, mock_repo, mock_mailer):
        """Email with special characters is passed correctly to mailer."""
        user_id = "user123"
        special_email = "user+tag@sub.example.co.uk"
        account = Account(user_id=user_id, email=special_email, status="active")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        mock_mailer.send_goodbye.assert_called_once_with(special_email)

    def test_deactivate_idempotent_on_multiple_calls(self, service, mock_repo, mock_mailer):
        """Calling deactivate twice on same user is idempotent after first call."""
        user_id = "user123"
        account_active = Account(user_id=user_id, email="user@example.com", status="active")
        account_inactive = Account(user_id=user_id, email="user@example.com", status="inactive")
        mock_repo.get.side_effect = [account_active, account_inactive]

        service.deactivate(user_id)
        service.deactivate(user_id)

        assert mock_repo.set_status.call_count == 1
        assert mock_mailer.send_goodbye.call_count == 1

    def test_deactivate_with_numeric_user_id(self, service, mock_repo, mock_mailer):
        """Deactivate works with numeric-like user_id strings."""
        user_id = "12345"
        account = Account(user_id=user_id, email="user@example.com", status="active")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        mock_repo.get.assert_called_once_with("12345")
        mock_repo.set_status.assert_called_once_with("12345", "inactive")

    def test_deactivate_account_service_initialization(self, mock_repo, mock_mailer):
        """AccountService initializes with repo and mailer."""
        service = AccountService(repo=mock_repo, mailer=mock_mailer)

        assert service._repo is mock_repo
        assert service._mailer is mock_mailer

    def test_deactivate_always_passes_inactive_string_to_repo(self, service, mock_repo, mock_mailer):
        """Deactivate always sets status to the string 'inactive'."""
        user_id = "user123"
        account = Account(user_id=user_id, email="user@example.com", status="active")
        mock_repo.get.return_value = account

        service.deactivate(user_id)

        # Verify the exact string passed
        call_args = mock_repo.set_status.call_args
        assert call_args[0][1] == "inactive"

import test from "node:test";
import assert from "node:assert";
import { AccountService } from "./fixture_d_account.mjs";

// Fake repo: in-memory implementation of AccountRepo
class FakeAccountRepo {
  constructor() {
    this.accounts = new Map();
    this.statusUpdates = [];
  }

  get(userId) {
    if (!this.accounts.has(userId)) {
      throw new Error(`Account not found for user ${userId}`);
    }
    return this.accounts.get(userId);
  }

  setStatus(userId, status) {
    this.statusUpdates.push({ userId, status });
    const account = this.accounts.get(userId);
    if (account) {
      account.status = status;
    }
  }

  addAccount(userId, email, status = "active") {
    this.accounts.set(userId, { email, status });
  }
}

// Fake mailer: in-memory implementation of Mailer
class FakeMailer {
  constructor() {
    this.sentEmails = [];
  }

  sendGoodbye(email) {
    this.sentEmails.push(email);
  }
}

test("AccountService.deactivate: active account transitions to inactive", () => {
  const repo = new FakeAccountRepo();
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  repo.addAccount("user123", "alice@example.com", "active");
  service.deactivate("user123");

  const account = repo.get("user123");
  assert.strictEqual(account.status, "inactive", "Account status should be set to inactive");
});

test("AccountService.deactivate: sends goodbye email to account email address", () => {
  const repo = new FakeAccountRepo();
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  repo.addAccount("user456", "bob@example.com", "active");
  service.deactivate("user456");

  assert.deepStrictEqual(
    mailer.sentEmails,
    ["bob@example.com"],
    "Goodbye email should be sent to the account's email address"
  );
});

test("AccountService.deactivate: already inactive account sends no email", () => {
  const repo = new FakeAccountRepo();
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  repo.addAccount("user789", "charlie@example.com", "inactive");
  service.deactivate("user789");

  assert.deepStrictEqual(
    mailer.sentEmails,
    [],
    "No email should be sent when account is already inactive"
  );
});

test("AccountService.deactivate: already inactive account does not call setStatus", () => {
  const repo = new FakeAccountRepo();
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  repo.addAccount("user999", "dave@example.com", "inactive");
  service.deactivate("user999");

  assert.deepStrictEqual(
    repo.statusUpdates,
    [],
    "setStatus should not be called for already inactive accounts"
  );
});

test("AccountService.deactivate: active account calls setStatus with inactive", () => {
  const repo = new FakeAccountRepo();
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  repo.addAccount("user111", "eve@example.com", "active");
  service.deactivate("user111");

  assert.deepStrictEqual(
    repo.statusUpdates,
    [{ userId: "user111", status: "inactive" }],
    "setStatus should be called with correct userId and 'inactive' status"
  );
});

test("AccountService.deactivate: verifies early return prevents double deactivation side effects", () => {
  const repo = new FakeAccountRepo();
  const mailer = new FakeMailer();
  const service = new AccountService(repo, mailer);

  repo.addAccount("user222", "frank@example.com", "inactive");

  // Deactivate an already-inactive account
  service.deactivate("user222");

  // Status should remain unchanged
  const account = repo.get("user222");
  assert.strictEqual(account.status, "inactive", "Status should remain inactive");

  // Email list should be empty (no goodbye sent to already-inactive account)
  assert.strictEqual(mailer.sentEmails.length, 0, "No email should be sent for already-inactive account");
});

import { test } from "node:test";
import assert from "node:assert/strict";
import { AccountService } from "./fixture_d_account.mjs";

class FakeRepo {
  constructor(...accounts) {
    this.accounts = new Map(accounts.map((a) => [a.userId, a]));
  }
  get(userId) {
    return this.accounts.get(userId);
  }
  setStatus(userId, status) {
    this.accounts.set(userId, { ...this.accounts.get(userId), status });
  }
}

class FakeMailer {
  constructor() {
    this.goodbyes = [];
  }
  sendGoodbye(email) {
    this.goodbyes.push(email);
  }
}

function make(status) {
  const repo = new FakeRepo({ userId: "u1", email: "u1@example.com", status });
  const mailer = new FakeMailer();
  return { svc: new AccountService(repo, mailer), repo, mailer };
}

test("deactivating an active account marks it inactive", () => {
  const { svc, repo } = make("active");
  svc.deactivate("u1");
  assert.equal(repo.accounts.get("u1").status, "inactive");
});

test("deactivating an active account sends one goodbye", () => {
  const { svc, mailer } = make("active");
  svc.deactivate("u1");
  assert.deepEqual(mailer.goodbyes, ["u1@example.com"]);
});

test("deactivating an inactive account changes nothing", () => {
  const { svc, repo, mailer } = make("inactive");
  svc.deactivate("u1");
  assert.deepEqual(mailer.goodbyes, []);
  assert.equal(repo.accounts.get("u1").status, "inactive");
});

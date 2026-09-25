import test from "node:test";
import assert from "node:assert";
import { AccountService, AccountRepo, Mailer } from "./fixture_d_account.mjs";

test("AccountService.deactivate", async (t) => {
  await t.test("should deactivate an active account and send goodbye email", () => {
    const userId = "user123";
    const email = "user@example.com";

    const mockRepo = {
      get: (id) => {
        assert.strictEqual(id, userId);
        return { status: "active", email };
      },
      setStatus: (id, status) => {
        assert.strictEqual(id, userId);
        assert.strictEqual(status, "inactive");
      },
    };

    const mockMailer = {
      sendGoodbye: (emailAddr) => {
        assert.strictEqual(emailAddr, email);
      },
    };

    const service = new AccountService(mockRepo, mockMailer);
    service.deactivate(userId);
  });

  await t.test("should not send email if account is already inactive", () => {
    const userId = "user456";
    const email = "user2@example.com";

    let setStatusCalled = false;
    let sendGoodbyeCalled = false;

    const mockRepo = {
      get: (id) => {
        assert.strictEqual(id, userId);
        return { status: "inactive", email };
      },
      setStatus: (id, status) => {
        setStatusCalled = true;
      },
    };

    const mockMailer = {
      sendGoodbye: (emailAddr) => {
        sendGoodbyeCalled = true;
      },
    };

    const service = new AccountService(mockRepo, mockMailer);
    service.deactivate(userId);

    assert.strictEqual(setStatusCalled, false, "setStatus should not be called");
    assert.strictEqual(sendGoodbyeCalled, false, "sendGoodbye should not be called");
  });

  await t.test("should retrieve account before deactivating", () => {
    const userId = "user789";
    const email = "user3@example.com";
    let getWasCalledFirst = false;

    const mockRepo = {
      get: (id) => {
        getWasCalledFirst = true;
        assert.strictEqual(id, userId);
        return { status: "active", email };
      },
      setStatus: (id, status) => {
        assert.strictEqual(getWasCalledFirst, true);
        assert.strictEqual(id, userId);
        assert.strictEqual(status, "inactive");
      },
    };

    const mockMailer = {
      sendGoodbye: (emailAddr) => {
        assert.strictEqual(emailAddr, email);
      },
    };

    const service = new AccountService(mockRepo, mockMailer);
    service.deactivate(userId);
  });

  await t.test("should handle different email addresses correctly", () => {
    const userId = "user999";
    const email = "different.email+test@domain.co.uk";

    const mockRepo = {
      get: () => {
        return { status: "active", email };
      },
      setStatus: () => {},
    };

    let receivedEmail = null;
    const mockMailer = {
      sendGoodbye: (emailAddr) => {
        receivedEmail = emailAddr;
      },
    };

    const service = new AccountService(mockRepo, mockMailer);
    service.deactivate(userId);

    assert.strictEqual(receivedEmail, email);
  });

  await t.test("should return undefined when deactivating active account", () => {
    const mockRepo = {
      get: () => ({ status: "active", email: "user@example.com" }),
      setStatus: () => {},
    };

    const mockMailer = {
      sendGoodbye: () => {},
    };

    const service = new AccountService(mockRepo, mockMailer);
    const result = service.deactivate("user123");

    assert.strictEqual(result, undefined);
  });

  await t.test("should return undefined when deactivating inactive account", () => {
    const mockRepo = {
      get: () => ({ status: "inactive", email: "user@example.com" }),
      setStatus: () => {},
    };

    const mockMailer = {
      sendGoodbye: () => {},
    };

    const service = new AccountService(mockRepo, mockMailer);
    const result = service.deactivate("user123");

    assert.strictEqual(result, undefined);
  });
});

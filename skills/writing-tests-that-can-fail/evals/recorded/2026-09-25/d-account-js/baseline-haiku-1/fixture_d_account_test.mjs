import { test } from 'node:test';
import assert from 'node:assert';
import { AccountRepo, Mailer, AccountService } from './fixture_d_account.mjs';

test('AccountService.deactivate', async (t) => {
  await t.test('deactivates an active account and sends goodbye email', () => {
    const mockRepo = {
      get: (userId) => ({ email: 'user@example.com', status: 'active' }),
      setStatus: () => {},
    };
    const mockMailer = {
      sendGoodbye: () => {},
    };

    let setStatusCalled = false;
    let setStatusUserId = null;
    let setStatusValue = null;
    mockRepo.setStatus = (userId, status) => {
      setStatusCalled = true;
      setStatusUserId = userId;
      setStatusValue = status;
    };

    let sendGoodbyeCalled = false;
    let sendGoodbyeEmail = null;
    mockMailer.sendGoodbye = (email) => {
      sendGoodbyeCalled = true;
      sendGoodbyeEmail = email;
    };

    const service = new AccountService(mockRepo, mockMailer);
    service.deactivate('user123');

    assert.strictEqual(setStatusCalled, true);
    assert.strictEqual(setStatusUserId, 'user123');
    assert.strictEqual(setStatusValue, 'inactive');
    assert.strictEqual(sendGoodbyeCalled, true);
    assert.strictEqual(sendGoodbyeEmail, 'user@example.com');
  });

  await t.test('skips deactivation if account is already inactive', () => {
    const mockRepo = {
      get: (userId) => ({ email: 'user@example.com', status: 'inactive' }),
      setStatus: () => {},
    };
    const mockMailer = {
      sendGoodbye: () => {},
    };

    let setStatusCalled = false;
    mockRepo.setStatus = () => {
      setStatusCalled = true;
    };

    let sendGoodbyeCalled = false;
    mockMailer.sendGoodbye = () => {
      sendGoodbyeCalled = true;
    };

    const service = new AccountService(mockRepo, mockMailer);
    service.deactivate('user123');

    assert.strictEqual(setStatusCalled, false);
    assert.strictEqual(sendGoodbyeCalled, false);
  });

  await t.test('passes correct userId to repo.get', () => {
    const mockRepo = {
      get: (userId) => ({ email: 'user@example.com', status: 'active' }),
      setStatus: () => {},
    };
    const mockMailer = {
      sendGoodbye: () => {},
    };

    let getCalledWith = null;
    mockRepo.get = (userId) => {
      getCalledWith = userId;
      return { email: 'user@example.com', status: 'active' };
    };

    const service = new AccountService(mockRepo, mockMailer);
    service.deactivate('user456');

    assert.strictEqual(getCalledWith, 'user456');
  });

  await t.test('uses account email from repo for goodbye message', () => {
    const mockRepo = {
      get: (userId) => ({ email: 'custom@example.com', status: 'active' }),
      setStatus: () => {},
    };
    const mockMailer = {
      sendGoodbye: () => {},
    };

    let sendGoodbyeEmail = null;
    mockMailer.sendGoodbye = (email) => {
      sendGoodbyeEmail = email;
    };

    const service = new AccountService(mockRepo, mockMailer);
    service.deactivate('user123');

    assert.strictEqual(sendGoodbyeEmail, 'custom@example.com');
  });

  await t.test('calls repo and mailer in correct order', () => {
    const callOrder = [];

    const mockRepo = {
      get: (userId) => {
        callOrder.push('get');
        return { email: 'user@example.com', status: 'active' };
      },
      setStatus: () => {
        callOrder.push('setStatus');
      },
    };
    const mockMailer = {
      sendGoodbye: () => {
        callOrder.push('sendGoodbye');
      },
    };

    const service = new AccountService(mockRepo, mockMailer);
    service.deactivate('user123');

    assert.deepStrictEqual(callOrder, ['get', 'setStatus', 'sendGoodbye']);
  });
});

test('AccountRepo', async (t) => {
  await t.test('get throws error', () => {
    const repo = new AccountRepo();
    assert.throws(() => repo.get('user123'), /real DB access/);
  });

  await t.test('setStatus throws error', () => {
    const repo = new AccountRepo();
    assert.throws(() => repo.setStatus('user123', 'inactive'), /real DB access/);
  });
});

test('Mailer', async (t) => {
  await t.test('sendGoodbye throws error', () => {
    const mailer = new Mailer();
    assert.throws(() => mailer.sendGoodbye('user@example.com'), /real email send/);
  });
});

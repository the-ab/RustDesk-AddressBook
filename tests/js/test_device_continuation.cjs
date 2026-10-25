const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../app/static/js/app.js'), 'utf8');
const element = (values = {}) => ({
  dataset: {}, value: '', disabled: false,
  addEventListener() {}, ...values
});

function runPage({connectUrl, blocked = false, passwordResponse, resume = false} = {}) {
  const launches = [], requests = [], modals = [], alerts = [];
  const elements = {};
  if (connectUrl) elements.rustdeskConnectLink = element({href: connectUrl});
  if (resume) {
    elements.resumeDevicePassword = element({
      dataset: {passwordUrl: '/devices/12/password', deviceName: 'Selected client'}
    });
    elements.devicePasswordModal = element();
    elements.devicePasswordValue = element();
    elements.devicePasswordTitle = element();
  }
  const context = {
    document: {
      querySelector: (selector) => selector === 'meta[name="csrf-token"]' ? {getAttribute: () => 'csrf-test'} : null,
      querySelectorAll: (selector) => selector === '.device-password-action' && resume ? [elements.resumeDevicePassword] : [],
      getElementById: (id) => elements[id] || null
    },
    window: {
      location: {hash: '', assign: (url) => {
        if (blocked) throw new Error('external handler unavailable');
        launches.push(url);
      }},
      addEventListener() {},
      alert: (message) => alerts.push(message)
    },
    bootstrap: {Modal: {getOrCreateInstance: () => ({show: () => modals.push(true)})}},
    fetch: async (url, options) => {
      requests.push({url, options});
      return passwordResponse || {ok: true, status: 200, json: async () => ({password: 'synthetic-secret'})};
    },
    setTimeout() {}, setInterval() {}
  };
  vm.runInNewContext(source, context);
  return {launches, requests, modals, alerts, elements};
}

test('the completed connection page launches exactly the selected client', () => {
  const url = process.env.RAB_TEST_CONNECT_URL || 'rustdesk://987654321?password=synthetic-secret';
  const page = runPage({connectUrl: url});
  assert.deepEqual(page.launches, [url]);
  assert.equal(page.elements.rustdeskConnectLink.href, url);
  assert.deepEqual(page.requests, []);
});

test('a blocked automatic protocol launch keeps the normal retry link', () => {
  const url = 'rustdesk://987654321';
  const page = runPage({connectUrl: url, blocked: true});
  assert.equal(page.elements.rustdeskConnectLink.href, url);
  assert.equal(page.elements.rustdeskConnectLink.disabled, false);
  assert.deepEqual(page.alerts, []);
});

test('unrelated pages do not launch a client', () => {
  assert.deepEqual(runPage().launches, []);
});

test('the resumed password action uses a CSRF protected POST and opens its modal', async () => {
  const page = runPage({resume: true});
  await new Promise(setImmediate);
  assert.equal(page.requests.length, 1);
  assert.equal(page.requests[0].url, '/devices/12/password');
  assert.equal(page.requests[0].options.method, 'POST');
  assert.equal(page.requests[0].options.headers['X-CSRF-Token'], 'csrf-test');
  assert.equal(page.elements.devicePasswordValue.value, 'synthetic-secret');
  assert.equal(page.elements.devicePasswordTitle.textContent, 'Selected client');
  assert.deepEqual(page.modals, [true]);
  assert.equal(page.elements.resumeDevicePassword.disabled, false);
});

test('an expired continuation returns to reauth without displaying a password', async () => {
  const page = runPage({resume: true, passwordResponse: {
    ok: false, status: 401,
    json: async () => ({reauth_url: '/reauth?next=/devices/12/password/view'})
  }});
  await new Promise(setImmediate);
  assert.deepEqual(page.launches, ['/reauth?next=/devices/12/password/view']);
  assert.equal(page.elements.devicePasswordValue.value, '');
  assert.deepEqual(page.modals, []);
});

test('a denied password request does not open a modal or retain a secret', async () => {
  const page = runPage({resume: true, passwordResponse: {ok: false, status: 404, json: async () => ({})}});
  await new Promise(setImmediate);
  assert.equal(page.elements.devicePasswordValue.value, '');
  assert.deepEqual(page.modals, []);
  assert.equal(page.alerts.length, 1);
});

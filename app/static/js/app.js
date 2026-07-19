(function () {
  const alerts = document.querySelectorAll('.toast-stack .alert');
  alerts.forEach((alert) => {
    setTimeout(() => {
      const instance = bootstrap.Alert.getOrCreateInstance(alert);
      instance.close();
    }, 6000);
  });

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

  document.querySelectorAll('[data-confirm]').forEach((element) => {
    const eventName = element.tagName === 'FORM' ? 'submit' : 'click';
    element.addEventListener(eventName, (event) => {
      if (!window.confirm(element.dataset.confirm || 'Fortfahren?')) event.preventDefault();
    });
  });

  document.querySelectorAll('[data-user-provider]').forEach((provider) => {
    const form = provider.closest('form') || document;
    const updateProviderFields = () => {
      const isLocal = provider.value === 'local';
      form.querySelectorAll('.local-password-field').forEach((el) => el.classList.toggle('d-none', !isLocal));
      form.querySelectorAll('.oidc-identity-field').forEach((el) => el.classList.toggle('d-none', isLocal));
    };
    provider.addEventListener('change', updateProviderFields);
    updateProviderFields();
  });
  const i18n = window.RAB_I18N || {};

  function activateSettingsTabFromHash() {
    const hash = window.location.hash;
    if (!hash) return;
    let targetPane = document.querySelector(hash);
    if (hash === '#update-check-card') {
      targetPane = document.querySelector('#updates');
    } else if (targetPane && !targetPane.classList.contains('tab-pane')) {
      targetPane = targetPane.closest('.tab-pane');
    }
    if (!targetPane || !targetPane.id) return;
    const trigger = document.querySelector(`[data-bs-target="#${targetPane.id}"]`);
    if (trigger) {
      bootstrap.Tab.getOrCreateInstance(trigger).show();
      if (hash !== `#${targetPane.id}`) {
        setTimeout(() => document.querySelector(hash)?.scrollIntoView({block: 'start'}), 100);
      }
    }
  }

  activateSettingsTabFromHash();
  window.addEventListener('hashchange', activateSettingsTabFromHash);

  document.querySelectorAll('.password-toggle').forEach((button) => {
    button.addEventListener('click', async () => {
      const group = button.closest('.input-group');
      const input = group ? group.querySelector('.password-field') : null;
      const icon = button.querySelector('i');
      if (!input) return;

      if (input.dataset.passwordUrl && input.type === 'password' && !input.dataset.loaded && !input.value) {
        button.disabled = true;
        try {
          const response = await fetch(input.dataset.passwordUrl, {
            method: 'POST',
            headers: {'X-CSRF-Token': csrfToken}
          });
          const data = await response.json().catch(() => ({}));
          if (response.status === 401 && data.reauth_url) { window.location.assign(data.reauth_url); return; }
          if (response.ok) {
            input.value = data.password || '';
            input.dataset.loaded = '1';
          }
        } finally {
          button.disabled = false;
        }
      }

      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      if (icon) {
        icon.classList.toggle('bi-eye', !show);
        icon.classList.toggle('bi-eye-slash', show);
      }
    });
  });

  function updateGroupIconPreview(select) {
    const targetSelector = select.dataset.previewTarget;
    const target = targetSelector ? document.querySelector(targetSelector) : null;
    if (!target) return;
    const allowed = new Set(['collection','hdd-network','server','pc-display','pc-display-horizontal','laptop','windows','ubuntu','apple','android2','phone','router','ethernet','globe2','house','building','person-workspace','people','shield-lock','cloud','database','device-hdd','tools','wrench-adjustable','tag','star','folder']);
    const value = allowed.has(select.value) ? select.value : 'collection';
    const icon = document.createElement('i');
    icon.className = `bi bi-${value}`;
    target.replaceChildren(icon);
  }

  const passwordModalElement = document.getElementById('devicePasswordModal');
  const passwordValue = document.getElementById('devicePasswordValue');
  const passwordTitle = document.getElementById('devicePasswordTitle');
  document.querySelectorAll('.device-password-action').forEach((button) => {
    button.addEventListener('click', async () => {
      const url = button.dataset.passwordUrl;
      if (!url || !passwordModalElement || !passwordValue) return;
      button.disabled = true;
      passwordValue.value = '';
      try {
        const response = await fetch(url, {method: 'POST', headers: {'X-CSRF-Token': csrfToken, 'Accept': 'application/json'}});
        const data = await response.json().catch(() => ({}));
        if (response.status === 401 && data.reauth_url) { window.location.assign(data.reauth_url); return; }
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        passwordValue.value = data.password || '';
        if (passwordTitle) passwordTitle.textContent = button.dataset.deviceName || 'RustDesk';
        bootstrap.Modal.getOrCreateInstance(passwordModalElement).show();
      } catch (error) {
        window.alert(i18n.passwordLoadFailed || 'Passwort konnte nicht geladen werden.');
      } finally {
        button.disabled = false;
      }
    });
  });

  document.getElementById('devicePasswordCopy')?.addEventListener('click', async () => {
    if (!passwordValue) return;
    try {
      await navigator.clipboard.writeText(passwordValue.value || '');
    } catch (error) {
      passwordValue.select();
      document.execCommand('copy');
    }
  });

  document.querySelectorAll('[data-copy-value]').forEach((button) => {
    button.addEventListener('click', async () => {
      const value = button.dataset.copyValue || '';
      try { await navigator.clipboard.writeText(value); } catch (error) { /* browser may deny clipboard */ }
    });
  });

  document.querySelectorAll('.group-icon-select').forEach((select) => {
    updateGroupIconPreview(select);
    select.addEventListener('change', () => updateGroupIconPreview(select));
  });


  const escapeHtml = (value) => String(value || '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[ch] || ch));



  document.querySelectorAll('.rab-file-input').forEach((input) => {
    const label = document.querySelector(`[data-file-label-for="${input.id}"]`);
    const noFileText = input.dataset.noFileText || (i18n.noFileSelected || 'No file selected');
    const filesText = input.dataset.filesText || (i18n.filesSelected || 'files selected');
    const updateFileLabel = () => {
      if (!label) return;
      if (!input.files || input.files.length === 0) {
        label.textContent = noFileText;
      } else if (input.files.length === 1) {
        label.textContent = input.files[0].name;
      } else {
        label.textContent = `${input.files.length} ${filesText}`;
      }
    };
    updateFileLabel();
    input.addEventListener('change', updateFileLabel);
  });

  const updateButton = document.getElementById('updateCheckButton');
  const updateResult = document.getElementById('updateCheckResult');
  const updateBadge = document.getElementById('updateAvailableBadge');
  const renderUpdateCheck = (data) => {
    if (updateBadge) {
      updateBadge.classList.toggle('d-none', !data.update_available);
    }
    if (!updateResult) return;
    const badgeClass = data.update_available ? 'text-bg-warning' : (data.ok ? 'text-bg-success' : 'text-bg-danger');
    const badgeText = data.update_available ? (i18n.updateAvailable || 'Update verfügbar') : (data.ok ? (i18n.current || 'Aktuell') : (i18n.error || 'Fehler'));
    const details = [];
    details.push(`<div class="mb-1"><span class="badge ${badgeClass}">${badgeText}</span><span class="ms-2 text-secondary">${escapeHtml(data.checked_at || '')}</span></div>`);
    details.push(`<div>${escapeHtml(data.message || i18n.noMessage || 'Keine Meldung erhalten.')}</div>`);
    if (data.download_url) {
      details.push(`<div class="mt-1 text-secondary">${escapeHtml(i18n.download || 'Download')}: <code>${escapeHtml(data.download_url)}</code></div>`);
    }
    if (data.release_notes && data.release_notes.length) {
      details.push(`<div class="mt-3 fw-semibold">${escapeHtml(i18n.changes || 'Änderungen dieser Version')}</div><ul class="mb-0 mt-1">${data.release_notes.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`);
    }
    updateResult.innerHTML = details.join('');
  };

  const runUpdateCheck = async (showButtonState = false) => {
    const url = (updateButton && updateButton.dataset.updateCheckUrl) || (window.RAB_UPDATE_CHECK && window.RAB_UPDATE_CHECK.endpoint);
    if (!url) return null;
    let originalHtml = '';
    if (showButtonState && updateButton) {
      updateButton.disabled = true;
      originalHtml = updateButton.innerHTML;
      updateButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>' + escapeHtml(i18n.checking || 'Prüfe...');
    }
    try {
      const response = await fetch(url, {headers: {'Accept': 'application/json'}});
      const data = await response.json();
      renderUpdateCheck(data);
      return data;
    } catch (error) {
      if (updateResult) {
        updateResult.innerHTML = `<div><span class="badge text-bg-danger">${escapeHtml(i18n.error || 'Fehler')}</span></div><div class="mt-1">${escapeHtml(i18n.updateFailed || 'Update-Check fehlgeschlagen')}: ${escapeHtml(String(error))}</div>`;
      }
      return null;
    } finally {
      if (showButtonState && updateButton) {
        updateButton.disabled = false;
        updateButton.innerHTML = originalHtml;
      }
    }
  };

  if (updateButton) {
    updateButton.addEventListener('click', () => runUpdateCheck(true));
  }

  const updateAuto = window.RAB_UPDATE_CHECK;
  if (updateAuto && updateAuto.enabled && updateAuto.endpoint) {
    if (updateAuto.stale) {
      setTimeout(() => runUpdateCheck(false), 3000);
    }
    if (updateAuto.intervalSeconds >= 3600) {
      setInterval(() => runUpdateCheck(false), updateAuto.intervalSeconds * 1000);
    }
  }

  const autoStatus = window.RAB_AUTO_STATUS;
  if (autoStatus && autoStatus.enabled && autoStatus.endpoint && autoStatus.intervalSeconds >= 60) {
    let running = false;
    const runAutoStatusCheck = async () => {
      if (running) return;
      running = true;
      try {
        await fetch(autoStatus.endpoint, {
          method: 'POST',
          headers: {'X-CSRF-Token': csrfToken, 'Accept': 'application/json'}
        });
      } catch (error) {
        // Silent by design: the result is visible in Settings/Dashboard after the next page refresh.
      } finally {
        running = false;
      }
    };
    setTimeout(runAutoStatusCheck, 10000);
    setInterval(runAutoStatusCheck, autoStatus.intervalSeconds * 1000);
  }

})();

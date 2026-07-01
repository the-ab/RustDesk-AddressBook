(function () {
  const alerts = document.querySelectorAll('.toast-stack .alert');
  alerts.forEach((alert) => {
    setTimeout(() => {
      const instance = bootstrap.Alert.getOrCreateInstance(alert);
      instance.close();
    }, 6000);
  });

  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

  document.querySelectorAll('.password-toggle').forEach((button) => {
    button.addEventListener('click', async () => {
      const group = button.closest('.input-group');
      const input = group ? group.querySelector('.password-field') : null;
      const icon = button.querySelector('i');
      if (!input) return;

      if (input.dataset.passwordUrl && input.type === 'password' && !input.dataset.loaded) {
        button.disabled = true;
        try {
          const response = await fetch(input.dataset.passwordUrl, {
            method: 'POST',
            headers: {'X-CSRF-Token': csrfToken}
          });
          if (response.ok) {
            const data = await response.json();
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
    const value = select.value || 'collection';
    target.innerHTML = `<i class="bi bi-${value}"></i>`;
  }

  document.querySelectorAll('.group-icon-select').forEach((select) => {
    updateGroupIconPreview(select);
    select.addEventListener('change', () => updateGroupIconPreview(select));
  });


  const escapeHtml = (value) => String(value || '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[ch] || ch));

  const updateButton = document.getElementById('updateCheckButton');
  const updateResult = document.getElementById('updateCheckResult');
  const updateBadge = document.getElementById('updateAvailableBadge');

  const renderUpdateCheck = (data) => {
    if (updateBadge) {
      updateBadge.classList.toggle('d-none', !data.update_available);
    }
    if (!updateResult) return;
    const badgeClass = data.update_available ? 'text-bg-warning' : (data.ok ? 'text-bg-success' : 'text-bg-danger');
    const badgeText = data.update_available ? 'Update verfügbar' : (data.ok ? 'Aktuell' : 'Fehler');
    const details = [];
    details.push(`<div class="mb-1"><span class="badge ${badgeClass}">${badgeText}</span><span class="ms-2 text-secondary">${escapeHtml(data.checked_at || '')}</span></div>`);
    details.push(`<div>${escapeHtml(data.message || 'Keine Meldung erhalten.')}</div>`);
    if (data.download_url) {
      details.push(`<div class="mt-1 text-secondary">Download: <code>${escapeHtml(data.download_url)}</code></div>`);
    }
    if (data.release_notes && data.release_notes.length) {
      details.push(`<div class="mt-3 fw-semibold">Änderungen dieser Version</div><ul class="mb-0 mt-1">${data.release_notes.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`);
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
      updateButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>Prüfe...';
    }
    try {
      const response = await fetch(url, {headers: {'Accept': 'application/json'}});
      const data = await response.json();
      renderUpdateCheck(data);
      return data;
    } catch (error) {
      if (updateResult) {
        updateResult.innerHTML = `<div><span class="badge text-bg-danger">Fehler</span></div><div class="mt-1">Update-Check fehlgeschlagen: ${escapeHtml(String(error))}</div>`;
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

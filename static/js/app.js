// NHM Coach Backoffice — Global JS Utilities

function showToast(msg, type = 'success') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.className = `toast toast-${type}`;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 4000);
}

function showLoading(text = 'Wird geladen…') {
  const overlay = document.getElementById('loading-overlay');
  const textEl = document.getElementById('loading-text');
  if (!overlay) return;
  if (textEl) textEl.textContent = text;
  overlay.classList.remove('hidden');
}

function hideLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) overlay.classList.add('hidden');
}

// Close modal on backdrop click
document.addEventListener('click', (e) => {
  const modal = document.getElementById('meal-replace-modal');
  if (modal && e.target === modal) {
    modal.classList.add('hidden');
  }
});

// Auto-save indicator for editable content
let saveTimeout;
document.addEventListener('input', (e) => {
  if (e.target.hasAttribute('contenteditable')) {
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
      const saveBtn = document.getElementById('btn-save');
      if (saveBtn) saveBtn.textContent = '💾 Speichern *';
    }, 300);
  }
});

(function () {
    function rememberHome(el) {
        if (!el._portalHome) {
            el._portalHome = { parent: el.parentElement, next: el.nextSibling };
        }
    }

    function portalToBody(el) {
        rememberHome(el);
        if (el.parentElement !== document.body) {
            document.body.appendChild(el);
        }
        el.classList.add('wa-fmodal--portaled');
    }

    function restoreFromPortal(el) {
        const home = el._portalHome;
        if (home && home.parent && el.parentElement === document.body) {
            home.parent.insertBefore(el, home.next);
        }
        el.classList.remove('wa-fmodal--portaled');
    }

    function serializeForm(form) {
        const data = {};
        form.querySelectorAll('input, select, textarea').forEach((el) => {
            if (!el.name) return;
            if (el.type === 'radio') {
                if (el.checked) data[el.name] = el.value;
            } else if (el.type === 'checkbox') {
                const multi = el.closest('.wa-fmodal__options--multi');
                if (multi) {
                    if (!Array.isArray(data[el.name])) data[el.name] = [];
                    if (el.checked) data[el.name].push(el.value);
                } else if (el.checked) {
                    data[el.name] = el.value || 'on';
                }
            } else {
                data[el.name] = el.value;
            }
        });
        form.querySelectorAll('input[type="radio"]').forEach((el) => {
            if (el.name && !(el.name in data)) data[el.name] = '';
        });
        form.querySelectorAll('.wa-fmodal__options--multi input[type="checkbox"]').forEach((el) => {
            if (el.name && !Array.isArray(data[el.name])) data[el.name] = [];
        });
        return JSON.stringify(data);
    }

    function restoreForm(form, snapshotJson) {
        const data = JSON.parse(snapshotJson);
        form.querySelectorAll('input, select, textarea').forEach((el) => {
            if (!el.name) return;
            if (el.type === 'radio') {
                el.checked = el.value === (data[el.name] ?? '');
            } else if (el.type === 'checkbox') {
                const multi = el.closest('.wa-fmodal__options--multi');
                if (multi) {
                    const vals = data[el.name];
                    el.checked = Array.isArray(vals) ? vals.includes(el.value) : false;
                } else {
                    el.checked = Boolean(data[el.name]);
                }
            } else {
                el.value = data[el.name] ?? '';
            }
        });
    }

    function openModal(modal) {
        const form = modal.querySelector('.wa-fmodal__form');
        if (form) {
            modal.dataset.snapshot = serializeForm(form);
        }
        portalToBody(modal);
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('wa-fmodal-open');
        const first = modal.querySelector('input[type="radio"]:checked, input[type="checkbox"]:checked, input, select');
        if (first) first.focus();
    }

    function closeModal(modal, restore) {
        const form = modal.querySelector('.wa-fmodal__form');
        if (restore && form && modal.dataset.snapshot) {
            restoreForm(form, modal.dataset.snapshot);
        }
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        if (!document.querySelector('.wa-fmodal.is-open')) {
            document.body.classList.remove('wa-fmodal-open');
        }
        restoreFromPortal(modal);
    }

    document.querySelectorAll('[data-fmodal-open]').forEach((btn) => {
        btn.addEventListener('click', function () {
            const id = btn.getAttribute('data-fmodal-open');
            const modal = document.getElementById(id);
            if (modal) openModal(modal);
        });
    });

    document.querySelectorAll('.wa-fmodal').forEach((modal) => {
        const form = modal.querySelector('.wa-fmodal__form');

        modal.querySelectorAll('[data-fmodal-close]').forEach((el) => {
            el.addEventListener('click', function () {
                closeModal(modal, true);
            });
        });

        modal.querySelectorAll('[data-fmodal-cancel]').forEach((el) => {
            el.addEventListener('click', function () {
                closeModal(modal, true);
            });
        });

        if (form) {
            modal.querySelectorAll('[data-fmodal-clear]').forEach((el) => {
                el.addEventListener('click', function () {
                    form.querySelectorAll('input[type="radio"]').forEach((radio) => {
                        radio.checked = radio.value === '';
                    });
                    form.querySelectorAll('.wa-fmodal__options--multi input[type="checkbox"]').forEach((checkbox) => {
                        checkbox.checked = false;
                    });
                });
            });
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        document.querySelectorAll('.wa-fmodal.is-open').forEach((modal) => {
            closeModal(modal, true);
        });
    });

    document.querySelectorAll('.wa-fmodal[data-fmodal-auto-open]').forEach((modal) => {
        openModal(modal);
    });
})();

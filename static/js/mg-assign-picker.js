(function () {
    const RECOMMEND_URL = document.body.dataset.recommendAssigneesUrl || '/recommend-assignees/';

    function getSelectedTaskTypes() {
        const checked = document.querySelectorAll('input[name="types"]:checked');
        if (checked.length) {
            return Array.from(checked).map((el) => el.value);
        }
        const legacy = document.getElementById('id_type');
        if (legacy && legacy.value) {
            return [legacy.value];
        }
        return ['BD'];
    }

    function getTaskContext() {
        const rankEl = document.getElementById('id_rank');
        return {
            types: getSelectedTaskTypes(),
            rank: rankEl ? rankEl.value : '350',
        };
    }

    function fetchRecommendations(query) {
        const ctx = getTaskContext();
        const params = new URLSearchParams({
            rank: ctx.rank,
            q: query || '',
        });
        ctx.types.forEach((typeCode) => params.append('type', typeCode));
        return fetch(RECOMMEND_URL + '?' + params.toString()).then(r => r.json());
    }

    function renderItem(picker, item, kind) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'mg-assign-picker__item';
        btn.dataset.id = item.id;

        const scoreClass = item.score >= 70 ? ' mg-assign-picker__score--high' : '';
        let meta = '';
        if (kind === 'worker') {
            meta = `Рейтинг: ${item.rating}`;
            if (item.specialization) meta += ` · ${item.specialization}`;
            if (item.team_name) meta += ` · ${item.team_name}`;
            if (item.reasons && item.reasons.length) meta += ` — ${item.reasons.join(', ')}`;
        } else {
            meta = `${item.members_count} участн. · синергия ${item.synergy}`;
            if (item.dominant_type) meta += ` · ${item.dominant_type}`;
            if (item.reasons && item.reasons.length) meta += ` — ${item.reasons.join(', ')}`;
        }

        btn.innerHTML =
            '<span class="mg-assign-picker__item-main">' +
            '<span class="mg-assign-picker__item-name">' + escapeHtml(item.label) +
            (item.score >= 65 ? '<span class="mg-assign-picker__badge">совпадение</span>' : '') +
            '</span>' +
            '<span class="mg-assign-picker__item-meta">' + escapeHtml(meta) + '</span>' +
            '</span>' +
            '<span class="mg-assign-picker__score' + scoreClass + '">' + item.score + '</span>';

        return btn;
    }

    function escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function initPicker(picker) {
        const inputId = picker.dataset.input;
        const hidden = document.getElementById(inputId);
        const clearOtherId = picker.dataset.clearTeam || picker.dataset.clearWorker;
        const clearOther = clearOtherId ? document.getElementById(clearOtherId) : null;
        const listEl = picker.querySelector('.mg-assign-picker__list');
        const searchEl = picker.querySelector('.mg-assign-picker__search');
        const selectedEl = picker.querySelector('.mg-assign-picker__selected');
        const kind = picker.dataset.kind;
        let activeTab = 'recommended';
        let cache = { recommended: [], all: [] };

        function setSelected(id, label) {
            hidden.value = id || '';
            if (clearOther && id) clearOther.value = '';
            if (id) {
                selectedEl.hidden = false;
                selectedEl.innerHTML = 'Выбрано: <strong>' + escapeHtml(label) + '</strong>' +
                    ' <button type="button" class="mg-assign-picker__clear">Сбросить</button>';
                selectedEl.querySelector('.mg-assign-picker__clear').onclick = function () {
                    setSelected('', '');
                    renderList();
                };
            } else {
                selectedEl.hidden = true;
            }
            renderList();
        }

        function renderList() {
            const q = (searchEl.value || '').toLowerCase();
            let items = cache[activeTab] || [];
            if (q) {
                items = items.filter(i =>
                    (i.label || '').toLowerCase().includes(q) ||
                    (i.username || '').toLowerCase().includes(q)
                );
            }
            listEl.innerHTML = '';
            if (!items.length) {
                listEl.innerHTML = '<div class="mg-assign-picker__empty">Ничего не найдено</div>';
                return;
            }
            items.forEach(item => {
                const btn = renderItem(picker, item, kind);
                if (String(hidden.value) === String(item.id)) {
                    btn.classList.add('is-selected');
                }
                btn.addEventListener('click', function () {
                    setSelected(item.id, item.label);
                });
                listEl.appendChild(btn);
            });
        }

        function applyPrefill() {
            if (!hidden.value) return;
            const pool = [...(cache.recommended || []), ...(cache.all || [])];
            const item = pool.find(i => String(i.id) === String(hidden.value));
            const label = item
                ? (item.label || item.name)
                : (hidden.dataset.prefillLabel || ('#' + hidden.value));
            setSelected(hidden.value, label);
        }

        function load() {
            const q = searchEl.value.trim();
            fetchRecommendations(q).then(data => {
                cache.recommended = kind === 'worker' ? data.workers : data.teams;
                cache.all = cache.recommended;
                renderList();
                applyPrefill();
            }).catch(() => {
                listEl.innerHTML = '<div class="mg-assign-picker__empty">Не удалось загрузить</div>';
            });
        }

        picker.querySelectorAll('.mg-assign-picker__tab').forEach(tab => {
            tab.addEventListener('click', function () {
                picker.querySelectorAll('.mg-assign-picker__tab').forEach(t =>
                    t.classList.remove('mg-assign-picker__tab--active'));
                tab.classList.add('mg-assign-picker__tab--active');
                activeTab = tab.dataset.tab;
                renderList();
            });
        });

        searchEl.addEventListener('input', function () {
            window.clearTimeout(picker._searchTimer);
            picker._searchTimer = window.setTimeout(load, 280);
        });

        document.querySelectorAll('input[name="types"]').forEach((typeEl) => {
            typeEl.addEventListener('change', load);
        });
        const rankEl = document.getElementById('id_rank');
        if (rankEl) rankEl.addEventListener('change', load);

        if (hidden.value && hidden.dataset.prefillLabel) {
            setSelected(hidden.value, hidden.dataset.prefillLabel);
        }

        load();
    }

    function boot() {
        document.querySelectorAll('.mg-assign-picker').forEach(initPicker);
    }

    ['manager-create-task', 'manager-edit-task'].forEach(function (modalId) {
        document.querySelectorAll('[data-fmodal-open="' + modalId + '"]').forEach(btn => {
            btn.addEventListener('click', function () {
                window.setTimeout(boot, 120);
            });
        });

        const modal = document.getElementById(modalId);
        if (modal && modal.hasAttribute('data-fmodal-auto-open')) {
            boot();
        }
    });
})();

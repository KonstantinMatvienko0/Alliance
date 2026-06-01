(function () {
    const modal = document.getElementById('mg-team-detail-modal');
    const dataEl = document.getElementById('mg-teams-detail-data');
    if (!modal || !dataEl) return;

    let teamsMap = {};
    try {
        teamsMap = JSON.parse(dataEl.textContent);
    } catch (e) {
        return;
    }

    const els = {
        label: document.getElementById('mg-team-detail-label'),
        priority: document.getElementById('mg-team-detail-priority'),
        title: document.getElementById('mg-team-detail-title'),
        description: document.getElementById('mg-team-detail-description'),
        metrics: document.getElementById('mg-team-detail-metrics'),
        typesWrap: document.getElementById('mg-team-detail-types-wrap'),
        types: document.getElementById('mg-team-detail-types'),
        targetWrap: document.getElementById('mg-team-detail-target-wrap'),
        target: document.getElementById('mg-team-detail-target'),
        members: document.getElementById('mg-team-detail-members'),
        notes: document.getElementById('mg-team-detail-notes'),
        notesStatus: document.getElementById('mg-team-detail-notes-status'),
        foot: document.getElementById('mg-team-detail-foot'),
    };

    let currentTeam = null;
    let notesTimer = null;
    let notesSaving = false;

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

    function openModal() {
        portalToBody(modal);
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('wa-fmodal-open');
    }

    function closeModal() {
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        if (!document.querySelector('.wa-fmodal.is-open')) {
            document.body.classList.remove('wa-fmodal-open');
        }
        restoreFromPortal(modal);
        currentTeam = null;
    }

    function metricCard(label, value, extraClass, wide) {
        const card = document.createElement('div');
        card.className = 'tdm-metric' + (wide ? ' tdm-metric--wide' : '');
        card.innerHTML =
            '<span class="tdm-metric__label">' + label + '</span>' +
            '<span class="tdm-metric__value' + (extraClass ? ' ' + extraClass : '') + '">' + value + '</span>';
        return card;
    }

    function renderPills(container, items) {
        container.innerHTML = '';
        items.forEach(function (label) {
            const pill = document.createElement('span');
            pill.className = 'tdm-type-pill';
            pill.textContent = label;
            container.appendChild(pill);
        });
    }

    function renderMetrics(team) {
        els.metrics.innerHTML = '';
        els.metrics.appendChild(metricCard('Участники', team.members_count));
        els.metrics.appendChild(metricCard('Синергия', team.synergy_score, 'tdm-metric__value--accent'));
        els.metrics.appendChild(metricCard('Сплочённость', team.cohesion_score));
        els.metrics.appendChild(metricCard('Рейтинг', team.total_rating, 'tdm-metric__value--accent'));
        els.metrics.appendChild(metricCard('Открытые задачи', team.tasks_open));
        els.metrics.appendChild(metricCard('Все задачи', team.tasks_total));
        els.metrics.appendChild(metricCard('Завершено', team.tasks_done));
        els.metrics.appendChild(metricCard('Провалено', team.tasks_failed, 'tdm-metric__value--danger'));
        els.metrics.appendChild(metricCard('Ср. ранг задач', team.avg_rank, '', true));
    }

    function renderMembers(team) {
        els.members.innerHTML = '';
        if (!team.members.length) {
            const li = document.createElement('li');
            li.className = 'tdm-team-member tdm-team-member--empty';
            li.textContent = 'Участников пока нет';
            els.members.appendChild(li);
            return;
        }
        team.members.forEach(function (m) {
            const a = document.createElement('a');
            a.href = m.profile_url;
            a.className = 'tdm-team-member';
            a.addEventListener('click', function (e) {
                e.stopPropagation();
            });
            const meta = [];
            if (m.is_working) meta.push('Работает');
            meta.push('Сегодня ' + m.today_display);
            a.innerHTML =
                '<span class="tdm-team-member__avatar"><i class="fa-solid fa-user"></i></span>' +
                '<span class="tdm-team-member__main">' +
                '<span class="tdm-team-member__name">' + escapeHtml(m.name) + '</span>' +
                '<span class="tdm-team-member__meta">' + escapeHtml(meta.join(' · ')) + '</span>' +
                '</span>' +
                '<span class="tdm-team-member__rating">' + m.rating + '</span>';
            const li = document.createElement('li');
            li.appendChild(a);
            els.members.appendChild(li);
        });
    }

    function escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function renderFooter(team) {
        els.foot.innerHTML = '';
        if (team.create_task_url) {
            const create = document.createElement('a');
            create.href = team.create_task_url;
            create.className = 'tdm-foot__btn tdm-foot__btn--primary';
            create.innerHTML = '<i class="fa-solid fa-plus"></i> Задача';
            els.foot.appendChild(create);
        }
        if (team.edit_url) {
            const edit = document.createElement('a');
            edit.href = team.edit_url;
            edit.className = 'tdm-foot__btn tdm-foot__btn--ghost';
            edit.innerHTML = '<i class="fa-solid fa-pen"></i> Редактировать';
            els.foot.appendChild(edit);
        }
        if (team.detail_url) {
            const full = document.createElement('a');
            full.href = team.detail_url;
            full.className = 'tdm-foot__btn tdm-foot__btn--ghost';
            full.innerHTML = '<i class="fa-solid fa-arrow-up-right-from-square"></i> Полная страница';
            els.foot.appendChild(full);
        }
        els.foot.hidden = !els.foot.children.length;
    }

    function setNotesStatus(text, kind) {
        els.notesStatus.textContent = text || '';
        els.notesStatus.className = 'tdm-notes-hint' + (kind ? ' tdm-notes-hint--' + kind : '');
    }

    function saveNotes() {
        if (!currentTeam || !currentTeam.notes_url) return;
        const body = new URLSearchParams();
        body.set('manager_notes', els.notes.value);
        body.set('csrfmiddlewaretoken', currentTeam.csrf);
        notesSaving = true;
        setNotesStatus('Сохранение…', '');
        fetch(currentTeam.notes_url, {
            method: 'POST',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            body: body,
        })
            .then(function (r) {
                return r.json().then(function (data) {
                    return { ok: r.ok, data: data };
                });
            })
            .then(function (res) {
                notesSaving = false;
                if (res.ok && res.data.ok) {
                    currentTeam.manager_notes = els.notes.value;
                    teamsMap[String(currentTeam.id)] = currentTeam;
                    setNotesStatus('Сохранено', 'ok');
                    window.setTimeout(function () {
                        if (!notesSaving && els.notesStatus.textContent === 'Сохранено') {
                            setNotesStatus('', '');
                        }
                    }, 2000);
                } else {
                    setNotesStatus(res.data.error || 'Ошибка сохранения', 'err');
                }
            })
            .catch(function () {
                notesSaving = false;
                setNotesStatus('Ошибка сети', 'err');
            });
    }

    function scheduleNotesSave() {
        if (!currentTeam) return;
        window.clearTimeout(notesTimer);
        notesTimer = window.setTimeout(saveNotes, 700);
    }

    function fillModal(team) {
        currentTeam = team;
        els.label.textContent = 'Команда #' + team.id;
        els.title.textContent = team.name;
        els.description.textContent = team.description;

        els.priority.textContent = team.priority;
        els.priority.className = 'tdm-head__status mg-priority-pill mg-priority-pill--' + team.priority_class;

        renderMetrics(team);

        if (team.task_types && team.task_types.length) {
            els.typesWrap.hidden = false;
            renderPills(els.types, team.task_types);
        } else {
            els.typesWrap.hidden = true;
        }

        if (team.target_types && team.target_types.length) {
            els.targetWrap.hidden = false;
            renderPills(els.target, team.target_types);
        } else if (team.dominant_task_type) {
            els.targetWrap.hidden = false;
            renderPills(els.target, [team.dominant_task_type]);
        } else {
            els.targetWrap.hidden = true;
        }

        renderMembers(team);
        els.notes.value = team.manager_notes || '';
        setNotesStatus('', '');
        renderFooter(team);
    }

    function showTeam(teamId) {
        const team = teamsMap[String(teamId)];
        if (!team) return;
        fillModal(team);
        openModal();
    }

    document.querySelectorAll('.mg-team-card--openable').forEach(function (card) {
        card.setAttribute('tabindex', '0');
        card.addEventListener('click', function (e) {
            if (e.target.closest('a, button, input, label, select, textarea')) {
                return;
            }
            showTeam(card.dataset.teamId);
        });
        card.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                showTeam(card.dataset.teamId);
            }
        });
    });

    document.querySelectorAll('[data-team-open]').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            showTeam(btn.dataset.teamOpen);
        });
    });

    els.notes.addEventListener('input', scheduleNotesSave);

    modal.querySelectorAll('[data-team-detail-close]').forEach(function (el) {
        el.addEventListener('click', closeModal);
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && modal.classList.contains('is-open')) {
            closeModal();
        }
    });
})();

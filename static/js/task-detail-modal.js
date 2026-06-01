(function () {
    const modal = document.getElementById('wa-task-detail-modal');
    const dataEl = document.getElementById('wa-tasks-detail-data');
    if (!modal || !dataEl) return;

    let tasksMap = {};
    try {
        tasksMap = JSON.parse(dataEl.textContent);
    } catch (e) {
        return;
    }

    const els = {
        code: document.getElementById('wa-task-detail-code'),
        status: document.getElementById('wa-task-detail-status'),
        statusIcon: document.getElementById('wa-task-detail-status-icon'),
        statusLabel: document.getElementById('wa-task-detail-status-label'),
        title: document.getElementById('wa-task-detail-title'),
        metrics: document.getElementById('wa-task-detail-metrics'),
        typesWrap: document.getElementById('wa-task-detail-types-wrap'),
        types: document.getElementById('wa-task-detail-types'),
        description: document.getElementById('wa-task-detail-description'),
        meta: document.getElementById('wa-task-detail-meta'),
        linkWrap: document.getElementById('wa-task-detail-link-wrap'),
        link: document.getElementById('wa-task-detail-link'),
        linkText: document.getElementById('wa-task-detail-link-text'),
        foot: document.getElementById('wa-task-detail-foot'),
    };

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
    }

    function signedClass(n) {
        if (n > 0) return 'tdm-metric__value--accent';
        if (n < 0) return 'tdm-metric__value--danger';
        return '';
    }

    function formatSigned(n) {
        if (n > 0) return '+' + n;
        return String(n);
    }

    function metricCard(label, value, extraClass, wide) {
        const card = document.createElement('div');
        card.className = 'tdm-metric' + (wide ? ' tdm-metric--wide' : '');
        card.innerHTML =
            '<span class="tdm-metric__label">' + label + '</span>' +
            '<span class="tdm-metric__value' + (extraClass ? ' ' + extraClass : '') + '">' + value + '</span>';
        return card;
    }

    function kvRow(label, value) {
        if (!value) return null;
        const row = document.createElement('div');
        row.className = 'tdm-kv';
        row.innerHTML =
            '<span class="tdm-kv__label">' + label + '</span>' +
            '<span class="tdm-kv__value">' + value + '</span>';
        return row;
    }

    function escapeHtml(s) {
        const d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function renderTypes(types) {
        els.types.innerHTML = '';
        if (!types || !types.length) {
            els.typesWrap.hidden = true;
            return;
        }
        els.typesWrap.hidden = false;
        types.forEach(function (t) {
            const pill = document.createElement('span');
            pill.className = 'tdm-type-pill';
            pill.innerHTML =
                '<i class="fa-solid ' + escapeHtml(t.icon) + '" aria-hidden="true"></i> ' +
                escapeHtml(t.code);
            els.types.appendChild(pill);
        });
    }

    function renderMetrics(task) {
        els.metrics.innerHTML = '';
        els.metrics.appendChild(metricCard('Ранг задачи', String(task.rank), 'tdm-metric__value--accent'));

        if (task.task_rank_signed !== undefined && task.task_rank_signed !== null) {
            els.metrics.appendChild(
                metricCard(
                    'Итог по задаче',
                    formatSigned(task.task_rank_signed),
                    signedClass(task.task_rank_signed)
                )
            );
        }

        if (task.worker_rating_change !== undefined && task.worker_rating_change !== null) {
            els.metrics.appendChild(
                metricCard(
                    'Ваш рейтинг',
                    formatSigned(task.worker_rating_change),
                    signedClass(task.worker_rating_change)
                )
            );
        }

        els.metrics.appendChild(metricCard('Приоритет', task.priority, ''));

        if (task.is_overdue) {
            els.metrics.appendChild(metricCard('Срок', 'Просрочено', 'tdm-metric__value--danger', true));
        }
    }

    function renderMeta(task) {
        els.meta.innerHTML = '';
        const rows = [
            kvRow('Срок выполнения', task.due_date),
            kvRow('Завершено', task.completed_at),
            kvRow('Создано', task.created_at),
            kvRow('Команда', task.team),
            kvRow('Исполнитель', task.assigned_to),
            kvRow('Закрыл', task.completed_by),
        ];
        rows.forEach(function (row) {
            if (row) els.meta.appendChild(row);
        });
        if (!els.meta.children.length) {
            els.meta.hidden = true;
        } else {
            els.meta.hidden = false;
        }
    }

    function postForm(action, fields, btnClass, btnLabel) {
        const form = document.createElement('form');
        form.method = 'post';
        form.action = action;
        let html = '<input type="hidden" name="csrfmiddlewaretoken" value="' +
            escapeHtml(fields.csrf || '') + '">';
        Object.keys(fields).forEach(function (key) {
            if (key === 'csrf') return;
            html += '<input type="hidden" name="' + escapeHtml(key) + '" value="' +
                escapeHtml(fields[key]) + '">';
        });
        html += '<button type="submit" class="tdm-foot__btn ' + btnClass + '">' +
            escapeHtml(btnLabel) + '</button>';
        form.innerHTML = html;
        return form;
    }

    function renderManagerFooter(task) {
        els.foot.innerHTML = '';
        els.foot.hidden = true;
        let hasActions = false;

        if (task.edit_url && (task.status === 'open' || task.status === 'in_progress')) {
            const edit = document.createElement('a');
            edit.href = task.edit_url;
            edit.className = 'tdm-foot__btn tdm-foot__btn--ghost';
            edit.textContent = 'Редактировать';
            els.foot.appendChild(edit);
            hasActions = true;
        }

        if (task.manager_complete_url && task.status !== 'completed' && task.status !== 'failed') {
            els.foot.appendChild(postForm(
                task.manager_complete_url,
                { csrf: task.csrf, success: 'true' },
                'tdm-foot__btn--primary',
                'Завершить'
            ));
            els.foot.appendChild(postForm(
                task.manager_complete_url,
                { csrf: task.csrf, success: 'false' },
                'tdm-foot__btn--danger',
                'Провал'
            ));
            hasActions = true;
        }

        if (task.delete_url) {
            const delForm = postForm(
                task.delete_url,
                { csrf: task.csrf },
                'tdm-foot__btn--danger',
                'Удалить'
            );
            delForm.addEventListener('submit', function (e) {
                if (!window.confirm('Удалить эту задачу?')) {
                    e.preventDefault();
                }
            });
            els.foot.appendChild(delForm);
            hasActions = true;
        }

        if (hasActions) {
            els.foot.hidden = false;
        }
    }

    function renderWorkerFooter(task) {
        els.foot.innerHTML = '';
        els.foot.hidden = true;
        if (task.status !== 'open' && task.status !== 'in_progress') {
            return;
        }
        els.foot.hidden = false;
        if (task.status === 'open' && task.start_url) {
            els.foot.appendChild(postForm(
                task.start_url,
                { csrf: task.csrf },
                'tdm-foot__btn--primary',
                'Начать задачу'
            ));
        }
        if ((task.status === 'open' || task.status === 'in_progress') && task.complete_url) {
            els.foot.appendChild(postForm(
                task.complete_url,
                { csrf: task.csrf },
                'tdm-foot__btn--ghost',
                'Завершить'
            ));
        }
    }

    function renderFooter(task) {
        if (task.manager_complete_url || task.edit_url || task.delete_url) {
            renderManagerFooter(task);
        } else {
            renderWorkerFooter(task);
        }
    }

    function fillModal(task) {
        els.code.textContent = task.code;
        els.title.textContent = task.title;
        els.description.textContent = task.description || 'Описание не указано.';

        els.statusLabel.textContent = task.status_label;
        els.statusIcon.className = task.status_icon;
        els.status.className = 'tdm-head__status tdm-head__status--' + task.status;

        renderTypes(task.types);
        renderMetrics(task);
        renderMeta(task);

        if (task.link) {
            els.linkWrap.hidden = false;
            els.link.href = task.link;
            els.linkText.textContent = task.link;
        } else {
            els.linkWrap.hidden = true;
        }

        renderFooter(task);
    }

    function showTask(taskId) {
        const task = tasksMap[String(taskId)];
        if (!task) return;
        fillModal(task);
        openModal();
    }

    document.querySelectorAll('.wa-task-row--openable').forEach(function (row) {
        row.setAttribute('tabindex', '0');
        row.addEventListener('click', function (e) {
            if (e.target.closest('.wa-check, .wa-actions, button, a, input, label, select')) {
                return;
            }
            showTask(row.dataset.taskId);
        });
        row.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                showTask(row.dataset.taskId);
            }
        });
    });

    modal.querySelectorAll('[data-task-detail-close]').forEach(function (el) {
        el.addEventListener('click', closeModal);
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && modal.classList.contains('is-open')) {
            closeModal();
        }
    });
})();

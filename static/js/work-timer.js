(function () {
    const btn = document.getElementById('wa-work-timer-btn');
    if (!btn) return;

    const urls = {
        status: btn.dataset.statusUrl,
        toggle: btn.dataset.toggleUrl,
        stop: btn.dataset.stopUrl,
    };
    const csrfToken = btn.dataset.csrf;

    const labelEl = document.getElementById('wa-work-timer-label');
    const displayEl = document.getElementById('wa-work-timer-display');

    let active = false;
    let startedAtMs = null;
    let tickInterval = null;

    function getCookie(name) {
        const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? decodeURIComponent(match[2]) : '';
    }

    function csrfHeader() {
        return csrfToken || getCookie('csrftoken');
    }

    function formatElapsed(totalSeconds) {
        const s = Math.max(0, Math.floor(totalSeconds));
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = s % 60;
        return [h, m, sec].map((n) => String(n).padStart(2, '0')).join(':');
    }

    function updateDisplay() {
        if (!active || startedAtMs === null) {
            displayEl.textContent = '00:00:00';
            return;
        }
        const elapsed = (Date.now() - startedAtMs) / 1000;
        displayEl.textContent = formatElapsed(elapsed);
    }

    function setUiRunning(running) {
        active = running;
        btn.classList.toggle('is-running', running);
        btn.setAttribute('aria-pressed', running ? 'true' : 'false');
        labelEl.textContent = running ? 'работаю' : 'начать работу';
        if (running) {
            if (!tickInterval) tickInterval = setInterval(updateDisplay, 1000);
            updateDisplay();
        } else {
            clearInterval(tickInterval);
            tickInterval = null;
            displayEl.textContent = '00:00:00';
        }
    }

    async function fetchStatus() {
        const res = await fetch(urls.status, { credentials: 'same-origin' });
        if (!res.ok) return;
        const data = await res.json();
        if (data.active && data.started_at) {
            startedAtMs = new Date(data.started_at).getTime();
            setUiRunning(true);
        } else {
            startedAtMs = null;
            setUiRunning(false);
        }
    }

    async function postJson(url, payload) {
        const res = await fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-CSRFToken': csrfHeader(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload || {}),
            keepalive: true,
        });
        if (!res.ok) throw new Error('request failed');
        return res.json();
    }

    async function stopTimer(useKeepalive) {
        if (!active) return;
        try {
            await postJson(urls.stop, { action: 'stop' });
        } catch (e) {
            if (!useKeepalive) return;
        }
        setUiRunning(false);
        startedAtMs = null;
    }

    async function toggleTimer() {
        btn.disabled = true;
        try {
            const data = await postJson(urls.toggle, {});
            if (data.active && data.started_at) {
                startedAtMs = new Date(data.started_at).getTime();
                setUiRunning(true);
            } else {
                setUiRunning(false);
                startedAtMs = null;
            }
        } finally {
            btn.disabled = false;
        }
    }

    btn.addEventListener('click', toggleTimer);

    document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'hidden' && active) {
            stopTimer(true);
        }
    });

    window.addEventListener('pagehide', function () {
        if (active) stopTimer(true);
    });

    const logoutForm = document.querySelector('.wa-logout-form');
    if (logoutForm) {
        logoutForm.addEventListener('submit', function () {
            if (active) stopTimer(true);
        });
    }

    fetchStatus();
})();

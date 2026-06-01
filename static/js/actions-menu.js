(function () {
    function getMenu(actions) {
        return actions._menuEl || actions.querySelector('.wa-actions__menu');
    }

    function measureMenu(menu) {
        menu.style.position = 'fixed';
        menu.style.left = '-9999px';
        menu.style.top = '0';
        menu.style.visibility = 'hidden';
        menu.style.display = 'block';
        const w = menu.offsetWidth;
        const h = menu.offsetHeight;
        menu.style.visibility = '';
        return { w: w || 168, h: h || 80 };
    }

    function positionMenu(menu, btn) {
        const { w: menuW, h: menuH } = measureMenu(menu);
        const rect = btn.getBoundingClientRect();
        let top = rect.bottom + 4;
        let left = rect.right - menuW;

        if (left < 8) left = 8;
        if (left + menuW > window.innerWidth - 8) {
            left = window.innerWidth - menuW - 8;
        }
        if (top + menuH > window.innerHeight - 8) {
            top = Math.max(8, rect.top - menuH - 4);
        }

        menu.style.position = 'fixed';
        menu.style.zIndex = '1250';
        menu.style.top = top + 'px';
        menu.style.left = left + 'px';
        menu.style.right = 'auto';
        menu.style.bottom = 'auto';
        menu.style.transform = 'none';
    }

    function mountMenu(actions) {
        const menu = actions.querySelector('.wa-actions__menu');
        const btn = actions.querySelector('.wa-actions__toggle');
        if (!menu || !btn) return null;

        actions._menuEl = menu;
        if (!actions._menuHome) {
            actions._menuHome = { parent: menu.parentElement, next: menu.nextSibling };
        }

        document.body.appendChild(menu);
        menu.classList.add('wa-actions__menu--floating', 'wa-actions__menu--shown');
        positionMenu(menu, btn);
        return menu;
    }

    function unmountMenu(actions) {
        const menu = getMenu(actions);
        if (!menu) return;

        const home = actions._menuHome;
        if (home && home.parent) {
            home.parent.insertBefore(menu, home.next);
        }

        menu.classList.remove('wa-actions__menu--floating', 'wa-actions__menu--shown');
        menu.style.position = '';
        menu.style.top = '';
        menu.style.left = '';
        menu.style.right = '';
        menu.style.bottom = '';
        menu.style.zIndex = '';
        menu.style.transform = '';
        menu.style.display = '';
        menu.style.visibility = '';

        actions._menuEl = null;
    }

    function closeAll() {
        document.querySelectorAll('.wa-actions.is-open').forEach(function (el) {
            el.classList.remove('is-open');
            unmountMenu(el);
        });
        document.body.classList.remove('wa-actions-menu-open');
    }

    document.querySelectorAll('.wa-actions').forEach(function (actions) {
        const menu = actions.querySelector('.wa-actions__menu');
        if (menu) {
            menu.addEventListener('click', function (e) {
                e.stopPropagation();
            });
        }
    });

    document.querySelectorAll('.wa-actions__toggle').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            const parent = btn.closest('.wa-actions');
            const wasOpen = parent.classList.contains('is-open');

            closeAll();

            if (!wasOpen) {
                mountMenu(parent);
                parent.classList.add('is-open');
                document.body.classList.add('wa-actions-menu-open');
            }
        });
    });

    document.addEventListener('click', closeAll);

    window.addEventListener('resize', function () {
        document.querySelectorAll('.wa-actions.is-open').forEach(function (actions) {
            const menu = getMenu(actions);
            const btn = actions.querySelector('.wa-actions__toggle');
            if (menu && btn) positionMenu(menu, btn);
        });
    });

    window.addEventListener('scroll', function () {
        document.querySelectorAll('.wa-actions.is-open').forEach(function (actions) {
            const menu = getMenu(actions);
            const btn = actions.querySelector('.wa-actions__toggle');
            if (menu && btn) positionMenu(menu, btn);
        });
    }, true);
})();

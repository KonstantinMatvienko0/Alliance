(function () {
    const MODAL_IDS = ['manager-create-task', 'manager-edit-task'];
    const GAP = 10;

    function positionCalendarSmart(fp) {
        const cal = fp.calendarContainer;
        const input = fp._input;
        if (!cal || !input) return;

        const calH = cal.offsetHeight;
        const calW = cal.offsetWidth;
        const rect = input.getBoundingClientRect();
        const viewH = window.innerHeight;
        const viewW = window.innerWidth;

        const spaceBelow = viewH - rect.bottom - GAP;
        const spaceAbove = rect.top - GAP;
        const openAbove = spaceBelow < calH && spaceAbove >= spaceBelow;

        let top;
        if (openAbove) {
            top = Math.max(GAP, rect.top - calH - GAP);
            cal.classList.add('mg-flatpickr--above');
            cal.classList.remove('mg-flatpickr--below');
        } else {
            top = Math.min(viewH - calH - GAP, rect.bottom + GAP);
            if (top < GAP) top = GAP;
            cal.classList.add('mg-flatpickr--below');
            cal.classList.remove('mg-flatpickr--above');
        }

        let left = rect.left;
        if (left + calW > viewW - GAP) {
            left = viewW - calW - GAP;
        }
        if (left < GAP) {
            left = GAP;
        }

        cal.style.position = 'fixed';
        cal.style.top = top + 'px';
        cal.style.left = left + 'px';
        cal.style.right = 'auto';
        cal.style.bottom = 'auto';
        cal.style.zIndex = '1300';
    }

    function bindRepositionHandlers(fp) {
        if (fp._mgRepositionBound) return;
        fp._mgRepositionBound = true;

        const reposition = function () {
            if (fp.isOpen) {
                positionCalendarSmart(fp);
            }
        };

        window.addEventListener('resize', reposition);
        window.addEventListener('scroll', reposition, true);

        const modal = fp._input && fp._input.closest('.wa-fmodal');
        const scrollEl = modal && modal.querySelector('.wa-fmodal__body--form');
        if (scrollEl) {
            scrollEl.addEventListener('scroll', reposition);
        }
    }

    function initDeadlinePickers(root) {
        if (typeof flatpickr === 'undefined') return;
        const scope = root || document;
        scope.querySelectorAll('.mg-deadline-input').forEach((input) => {
            if (input._flatpickr) return;

            const fp = flatpickr(input, {
                enableTime: true,
                time_24hr: true,
                dateFormat: 'Y-m-d H:i',
                minuteIncrement: 5,
                defaultHour: 12,
                defaultMinute: 0,
                disableMobile: true,
                allowInput: false,
                clickOpens: true,
                appendTo: document.body,
                static: false,
                position: 'below',
                locale: {
                    firstDayOfWeek: 1,
                },
                onReady: function (_selectedDates, _dateStr, instance) {
                    instance.calendarContainer.classList.add('mg-flatpickr');
                },
                onOpen: function (_selectedDates, _dateStr, instance) {
                    requestAnimationFrame(function () {
                        positionCalendarSmart(instance);
                        bindRepositionHandlers(instance);
                    });
                },
                onMonthChange: function (_selectedDates, _dateStr, instance) {
                    requestAnimationFrame(function () {
                        positionCalendarSmart(instance);
                    });
                },
                onYearChange: function (_selectedDates, _dateStr, instance) {
                    requestAnimationFrame(function () {
                        positionCalendarSmart(instance);
                    });
                },
            });

            input._flatpickr = fp;
        });
    }

    MODAL_IDS.forEach(function (modalId) {
        document.querySelectorAll('[data-fmodal-open="' + modalId + '"]').forEach((btn) => {
            btn.addEventListener('click', function () {
                window.setTimeout(function () {
                    const modal = document.getElementById(modalId);
                    if (modal) initDeadlinePickers(modal);
                }, 60);
            });
        });

        const autoModal = document.getElementById(modalId);
        if (autoModal && autoModal.hasAttribute('data-fmodal-auto-open')) {
            initDeadlinePickers(autoModal);
        }
    });
})();

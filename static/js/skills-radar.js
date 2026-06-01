/**
 * Soft skills radar — Chart.js, mockup-style (labels on axis corners).
 * Data: #soft-skills-data JSON [{ name, value }, ...]
 */
(function (global) {
    'use strict';

    var CHART_PX = 300;
    var ACCENT = '#c1ff72';
    var ACCENT_FILL = 'rgba(193, 255, 114, 0.4)';

    function wrapLabel(name, maxChars) {
        var words = String(name).trim().split(/\s+/);
        if (!words.length) return '';
        var lines = [];
        var line = '';
        words.forEach(function (word) {
            var next = line ? line + ' ' + word : word;
            if (next.length > maxChars && line) {
                lines.push(line);
                line = word;
            } else {
                line = next;
            }
        });
        if (line) lines.push(line);
        if (lines.length === 1) return lines[0];
        if (lines.length === 2) return lines;
        return [lines[0], lines.slice(1).join(' ')];
    }

    function labelText(raw) {
        return Array.isArray(raw) ? raw.join(' ') : String(raw);
    }

    function initSkillsRadar() {
        if (typeof Chart === 'undefined') return;

        var dataEl = document.getElementById('soft-skills-data');
        var root = document.querySelector('[data-skills-radar]');
        var canvas = document.getElementById('skillsRadarChart');
        var emptyEl = document.getElementById('skillsRadarEmpty');
        var chartBox = document.querySelector('.ch-radar-card__chart');

        if (!dataEl || !root || !canvas) return;

        var skills = [];
        try {
            skills = JSON.parse(dataEl.textContent);
        } catch (e) {
            return;
        }

        if (!skills.length) {
            if (chartBox) chartBox.hidden = true;
            if (emptyEl) emptyEl.hidden = false;
            return;
        }

        if (emptyEl) emptyEl.hidden = true;
        if (chartBox) chartBox.hidden = false;

        var labels = skills.map(function (s) {
            return wrapLabel(s.name, 12);
        });

        var chart = new Chart(canvas.getContext('2d'), {
            type: 'radar',
            data: {
                labels: labels,
                datasets: [{
                    data: skills.map(function (s) { return s.value; }),
                    backgroundColor: ACCENT_FILL,
                    borderColor: ACCENT,
                    borderWidth: 2,
                    pointBackgroundColor: ACCENT,
                    pointBorderColor: '#141414',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    fill: true,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                layout: { padding: 0 },
                scales: {
                    r: {
                        beginAtZero: true,
                        min: 0,
                        max: 10,
                        ticks: {
                            display: false,
                            stepSize: 2,
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.14)',
                            lineWidth: 1,
                            circular: false,
                        },
                        angleLines: {
                            color: 'rgba(255, 255, 255, 0.12)',
                            lineWidth: 1,
                        },
                        pointLabels: {
                            display: true,
                            color: '#e4e4e7',
                            font: {
                                size: 11,
                                weight: '600',
                                family: 'system-ui, -apple-system, "Segoe UI", sans-serif',
                                lineHeight: 1.3,
                            },
                            padding: 22,
                            centerPointLabels: true,
                        },
                    },
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#27272a',
                        borderColor: '#3f3f46',
                        borderWidth: 1,
                        titleColor: '#fafafa',
                        bodyColor: ACCENT,
                        padding: 10,
                        callbacks: {
                            label: function (ctx) {
                                return labelText(ctx.chart.data.labels[ctx.dataIndex]) +
                                    ': ' + ctx.formattedValue + ' / 10';
                            },
                        },
                    },
                },
                elements: {
                    line: { tension: 0.08 },
                },
            },
        });

        if (chartBox) {
            chartBox.style.width = CHART_PX + 'px';
            chartBox.style.height = CHART_PX + 'px';
        }

        function onResize() {
            chart.resize();
        }

        window.addEventListener('resize', onResize);
        chart.resize();
    }

    global.initSkillsRadar = initSkillsRadar;
})(window);

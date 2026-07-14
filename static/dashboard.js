let portfolioChart = null;
let debtChart = null;
let flowChart = null;
let cashChart = null;

// Phones: skip chart animations — cheaper first paint and free 60s refreshes
if (typeof Chart !== 'undefined' && window.matchMedia
        && matchMedia('(max-width: 768px)').matches) {
    Chart.defaults.animation = false;
}

// Helper to show toast messages
function showToast(message, isError = false) {
    const toast = document.getElementById('notificationToast');
    const toastIcon = toast.querySelector('i');
    const toastMsg = toast.querySelector('.toast-message');

    toastMsg.textContent = message;
    if (isError) {
        toast.style.borderColor = 'rgba(248, 113, 113, 0.4)';
        toastIcon.className = 'fa-solid fa-circle-xmark';
        toastIcon.style.color = '#f87171';
    } else {
        toast.style.borderColor = 'rgba(34, 211, 238, 0.3)';
        toastIcon.className = 'fa-solid fa-circle-check';
        toastIcon.style.color = '#22d3ee';
    }

    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
}

// Write message to dashboard console box
function writeConsole(message, isPrompt = true) {
    const consoleBox = document.getElementById('consoleOutput');
    const msgSpan = consoleBox.querySelector('.message');
    msgSpan.textContent = message;
}

// Fetch bot status from API
async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error('API hatası');
        const data = await response.json();

        // Update mode badge
        const badge = document.getElementById('botStatusBadge');
        const modeText = document.getElementById('botModeText');
        modeText.textContent = data.mode;

        if (data.mode === 'High-Speed Mode') {
            badge.classList.add('critical-mode');
        } else {
            badge.classList.remove('critical-mode');
        }

        // Update last check subtext
        document.getElementById('lastCheckSubtext').textContent = 'Son sorgu: ' + (data.last_checked || 'Yapılmadı');

    } catch (error) {
        console.error('Status fetch error:', error);
    }
}

// Fetch historical filings & purchases from API
async function fetchHistory() {
    try {
        const response = await fetch('/api/history');
        if (!response.ok) throw new Error('API hatası');
        const data = await response.json();

        if (data.length === 0) return;

        // Update Stat Cards (with latest record)
        const latest = data[0];
        const rawHoldings = latest.total_holdings || '-';
        const cleanHoldings = rawHoldings.replace(/,/g, '');
        const holdingsNum = parseFloat(cleanHoldings);
        if (!isNaN(holdingsNum)) {
            document.getElementById('statTotalHoldings').textContent = holdingsNum.toLocaleString('tr-TR') + ' BTC';
        } else {
            document.getElementById('statTotalHoldings').textContent = rawHoldings + ' BTC';
        }
        
        document.getElementById('statTotalCost').textContent = latest.total_cost;
        document.getElementById('statAvgCost').textContent = latest.avg_cost;
        document.getElementById('statTotalDebt').textContent = latest.total_debt || '-';

        // Populate Table
        const tbody = document.getElementById('historyTableBody');
        tbody.innerHTML = '';

        data.forEach(item => {
            const tr = document.createElement('tr');
            
            // Format acquired badge safely
            let acquiredBadgeHtml = '';
            const rawAcq = item.btc_acquired || '-';
            if (rawAcq === '0' || rawAcq === '-') {
                acquiredBadgeHtml = `<span class="badge-no-acquired">0 BTC</span>`;
            } else {
                const cleanAcq = rawAcq.replace(/,/g, '');
                const acqNum = parseFloat(cleanAcq);
                if (!isNaN(acqNum)) {
                    if (acqNum < 0) {
                        acquiredBadgeHtml = `<span class="badge-sold">${acqNum.toLocaleString('tr-TR')} BTC</span>`;
                    } else {
                        acquiredBadgeHtml = `<span class="badge-acquired">+${acqNum.toLocaleString('tr-TR')} BTC</span>`;
                    }
                } else {
                    if (rawAcq.startsWith('-')) {
                        acquiredBadgeHtml = `<span class="badge-sold">${rawAcq} BTC</span>`;
                    } else {
                        acquiredBadgeHtml = `<span class="badge-acquired">+${rawAcq} BTC</span>`;
                    }
                }
            }

            // Format financing badge safely
            const fSource = item.financing_source || '-';
            let fBadgeClass = 'badge-source-none';
            if (fSource.includes('&') || (fSource.includes('ATM') && fSource.includes('Tahvil')) || fSource.includes('Nakit')) {
                fBadgeClass = 'badge-source-mixed';
            } else if (fSource.includes('ATM') || fSource.includes('Hisse')) {
                fBadgeClass = 'badge-source-atm';
            } else if (fSource.includes('Tahvil') || fSource.includes('Notes') || fSource.includes('Debt')) {
                fBadgeClass = 'badge-source-debt';
            } else {
                fBadgeClass = 'badge-source-none';
            }
            // Per-security ATM breakdown: visible lines under the badge, so
            // every report row shows WHICH security raised the cash
            const escAttr = (s) => String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
            let atmBreakdownHtml = '';
            if (item.atm_sales && Array.isArray(item.atm_sales.securities)) {
                const soldLines = item.atm_sales.securities
                    .filter(s => (s.shares_sold_num || 0) > 0)
                    .map(s => `<span class="atm-ticker">${escAttr(s.ticker)}</span>: ${escAttr(s.shares_sold)} adet → <strong>${escAttr(s.net_proceeds)}</strong> net`);
                if (soldLines.length) {
                    atmBreakdownHtml = `<div class="atm-breakdown">${soldLines.join('<br>')}</div>`;
                }
            }
            const financingBadgeHtml = `<span class="badge-source ${fBadgeClass}">${fSource}</span>${atmBreakdownHtml}`;

            // Format total holdings safely
            const rawTot = item.total_holdings || '-';
            const cleanTot = rawTot.replace(/,/g, '');
            const totNum = parseFloat(cleanTot);
            const totText = !isNaN(totNum) ? totNum.toLocaleString('tr-TR') + ' BTC' : rawTot + ' BTC';

            const shortLinkHtml = `<a href="${item.url}" target="_blank" class="table-link"><i class="fa-solid fa-arrow-up-right-from-square"></i> Form 8-K</a>`;

            tr.innerHTML = `
                <td><strong>${item.filing_date}</strong></td>
                <td>${acquiredBadgeHtml}</td>
                <td>${item.avg_price === '$0' ? '-' : item.avg_price}</td>
                <td>${totText}</td>
                <td>${financingBadgeHtml}</td>
                <td>${shortLinkHtml}</td>
            `;
            tbody.appendChild(tr);
        });

        // Initialize / Update Charts
        // Charts are rendered independently: a chart failure must never
        // wipe the already-populated table.
        const chartData = [...data].reverse(); // Chronological order
        try {
            renderPortfolioChart(chartData);
            renderFlowChart(chartData);
            renderDebtChart(chartData);
        } catch (chartError) {
            console.error('Chart render error:', chartError);
        }

    } catch (error) {
        console.error('History fetch error:', error);
        document.getElementById('historyTableBody').innerHTML = `<tr><td colspan="6" class="loading-cell" style="color: #f87171;">Veriler yüklenirken hata oluştu!</td></tr>`;
    }
}

// Render Portfolio Growth Chart using Chart.js
function renderPortfolioChart(chartData) {
    const labels = chartData.map(d => d.filing_date);
    const holdings = chartData.map(d => Number(d.total_holdings.replace(/,/g, '')));
    const costs = chartData.map(d => {
        const raw = d.total_cost.replace(/[$,B,M]/g, '').strip();
        return parseFloat(raw) || 0;
    });

    const ctx = document.getElementById('portfolioChart').getContext('2d');

    if (portfolioChart) {
        portfolioChart.destroy();
    }

    portfolioChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Toplam BTC Varlığı',
                    data: holdings,
                    borderColor: '#22d3ee',
                    backgroundColor: 'rgba(34, 211, 238, 0.04)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: 'Toplam Kümülatif Maliyet ($ Milyar)',
                    data: costs,
                    borderColor: '#60a5fa',
                    backgroundColor: 'rgba(96, 165, 250, 0.02)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    fill: false,
                    tension: 0.3,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#97a3b6',
                        font: { family: 'Inter', size: 11 }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(148,163,184,0.05)' },
                    ticks: { color: '#97a3b6', font: { family: 'Inter', size: 10 } }
                },
                y: {
                    position: 'left',
                    grid: { color: 'rgba(148,163,184,0.08)' },
                    ticks: {
                        color: '#22d3ee',
                        font: { family: 'Inter', size: 10 },
                        callback: function(value) { return value.toLocaleString('tr-TR'); }
                    },
                    title: { display: true, text: 'BTC Miktarı', color: '#22d3ee' }
                },
                y1: {
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: {
                        color: '#60a5fa',
                        font: { family: 'Inter', size: 10 },
                        callback: function(value) { return '$' + value + 'B'; }
                    },
                    title: { display: true, text: 'Maliyet ($ Milyar)', color: '#60a5fa' }
                }
            }
        }
    });
}

// Render the BTC flow vs ATM financing chart: BTC change as up/down bars
// (left axis, BTC) and per-security ATM net proceeds as DOWNWARD stacked
// bars (right axis, $M) — "security sold → cash raised → bar goes down",
// so weeks like "BTC bought, financed by STRC sales" read at a glance.
function renderFlowChart(chartData) {
    const canvas = document.getElementById('flowChart');
    if (!canvas) return;

    const labels = chartData.map(d => d.filing_date);
    const btcDeltas = chartData.map(d => {
        const num = parseFloat(String(d.btc_acquired || '0').replace(/,/g, ''));
        return isNaN(num) ? 0 : num;
    });

    // Categorical identity per security — validated as a set (lightness
    // band, CVD adjacent-pair separation, ≥3:1 contrast on the dark
    // surface). Fixed assignment: color follows the ticker, never its rank.
    // Green/red stay reserved for the BTC up/down bars in the same chart.
    const TICKER_COLORS = {
        MSTR: '#3b82f6',
        STRC: '#d97706',
        STRK: '#8b5cf6',
        STRF: '#0891b2',
        STRD: '#db2777'
    };

    const tickerData = {};
    const tickerShares = {};
    Object.keys(TICKER_COLORS).forEach(t => {
        tickerData[t] = new Array(chartData.length).fill(0);
        tickerShares[t] = new Array(chartData.length).fill(null);
    });
    chartData.forEach((d, i) => {
        const secs = (d.atm_sales && Array.isArray(d.atm_sales.securities)) ? d.atm_sales.securities : [];
        secs.forEach(s => {
            if ((s.shares_sold_num || 0) > 0 && TICKER_COLORS[s.ticker]) {
                tickerData[s.ticker][i] = -(s.net_proceeds_num_m || 0);
                tickerShares[s.ticker][i] = s.shares_sold;
            }
        });
    });

    const atmDatasets = Object.keys(TICKER_COLORS)
        .filter(t => tickerData[t].some(v => v !== 0))
        .map(t => ({
            label: `${t} ATM Satışı`,
            data: tickerData[t],
            backgroundColor: TICKER_COLORS[t] + 'B3',
            borderColor: TICKER_COLORS[t],
            borderWidth: 1.5,
            borderRadius: 4,
            stack: 'atm',
            yAxisID: 'yMoney',
            maxBarThickness: 26,
            _shares: tickerShares[t]
        }));

    // Symmetric ranges align both zero lines at mid-height: BTC bars rise
    // from the shared baseline, ATM sale bars hang below it (mirror view)
    const btcPeak = Math.max(1, ...btcDeltas.map(v => Math.abs(v)));
    const moneyPeak = Math.max(1, ...Object.values(tickerData).flat().map(v => Math.abs(v)));

    const ctx = canvas.getContext('2d');
    if (flowChart) {
        flowChart.destroy();
    }

    flowChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'BTC Değişimi',
                    data: btcDeltas,
                    backgroundColor: btcDeltas.map(v => v >= 0 ? 'rgba(52, 211, 153, 0.55)' : 'rgba(248, 113, 113, 0.55)'),
                    borderColor: btcDeltas.map(v => v >= 0 ? '#34d399' : '#f87171'),
                    borderWidth: 1.5,
                    borderRadius: 4,
                    stack: 'btc',
                    yAxisID: 'yBtc',
                    maxBarThickness: 26
                },
                ...atmDatasets
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    labels: { color: '#97a3b6', font: { family: 'Inter', size: 11 } }
                },
                tooltip: {
                    filter: (item) => item.parsed.y !== 0,
                    callbacks: {
                        label: function(context) {
                            const ds = context.dataset;
                            const v = context.parsed.y;
                            if (ds.yAxisID === 'yBtc') {
                                return `BTC: ${v > 0 ? '+' : ''}${v.toLocaleString('tr-TR')}`;
                            }
                            const shares = ds._shares ? ds._shares[context.dataIndex] : null;
                            const amount = Math.abs(v).toLocaleString('tr-TR', { maximumFractionDigits: 1 });
                            return `${ds.label}: $${amount}M net` + (shares ? ` (${shares} adet)` : '');
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { color: 'rgba(148,163,184,0.05)' },
                    ticks: { color: '#97a3b6', font: { family: 'Inter', size: 10 } }
                },
                yBtc: {
                    position: 'left',
                    min: -btcPeak * 1.15,
                    max: btcPeak * 1.15,
                    grid: { color: 'rgba(148,163,184,0.08)' },
                    ticks: {
                        color: '#34d399',
                        font: { family: 'Inter', size: 10 },
                        callback: function(value) { return value.toLocaleString('tr-TR'); }
                    },
                    title: { display: true, text: 'BTC Değişimi', color: '#34d399' }
                },
                yMoney: {
                    position: 'right',
                    stacked: true,
                    min: -moneyPeak * 1.15,
                    max: moneyPeak * 1.15,
                    grid: { drawOnChartArea: false },
                    ticks: {
                        color: '#60a5fa',
                        font: { family: 'Inter', size: 10 },
                        // Only the downward (sale) half is meaningful
                        callback: function(value) { return value > 0 ? '' : '$' + Math.round(Math.abs(value)).toLocaleString('tr-TR') + 'M'; }
                    },
                    title: { display: true, text: 'ATM Net Geliri ($M) ↓', color: '#60a5fa' }
                }
            }
        }
    });
}

function formatUsd(v) {
    if (v >= 1e9) return '$' + (v / 1e9).toLocaleString('tr-TR', { maximumFractionDigits: 2 }) + 'B';
    if (v >= 1e6) return '$' + Math.round(v / 1e6).toLocaleString('tr-TR') + 'M';
    return '$' + Math.round(v).toLocaleString('tr-TR');
}

// Cash reserves: quarterly ACTUALS (SEC XBRL balance sheet) + weekly
// ESTIMATE (ATM proceeds + BTC sales − BTC buys − dividends − calibrated
// other outflows), backtested against the reported quarters.
async function fetchCash() {
    try {
        const [cashResp, flowResp] = await Promise.all([
            fetch('/api/cash'),
            fetch('/api/cashflow')
        ]);
        const actuals = await cashResp.json();
        const flow = await flowResp.json();

        const note = document.getElementById('cashEmptyNote');
        const statCash = document.getElementById('statCash');
        const statCashDate = document.getElementById('statCashDate');

        if (!Array.isArray(actuals) || actuals.length === 0) {
            if (note) note.style.display = 'flex';
            if (statCash) statCash.textContent = '-';
            return;
        }
        if (note) note.style.display = 'none';

        const latest = actuals[actuals.length - 1];
        const official = flow && flow.official;
        const isReserve = flow && flow.cash_source === 'sec-8k';
        // Headline cash = the real USD Reserve (from 8-Ks), else strategy.com
        // override, else the latest quarterly balance.
        if (statCash) {
            statCash.textContent = (isReserve || latest)
                ? formatUsd(latest.value)
                : (official && official.usd_reserve_m != null ? formatUsd(official.usd_reserve_m * 1e6) : '-');
        }
        if (statCashDate) {
            let sub;
            if (isReserve) {
                sub = `USD Reserve (SEC 8-K, ${latest.period_end})`;
            } else if (official && official.usd_reserve_m != null) {
                sub = `Strategy resmi (${official.asof})`;
            } else {
                sub = `${latest.period_end} itibarıyla (çeyreklik)`;
            }
            if (flow && flow.current_estimate && !isReserve) {
                sub += ` • Tahmini: ${formatUsd(flow.current_estimate.cash_m * 1e6)}`;
            }
            if (flow && flow.runway) {
                sub += ` • Dayanma: ${flow.runway.infinite ? '∞' : '~' + flow.runway.weeks + ' hafta'}`;
            }
            statCashDate.textContent = sub;
        }

        // Preferred stock outstanding (nominal) — separate from bond debt:
        // 10-Q per-series notional + ATM issuance since, or strategy.com
        const statPref = document.getElementById('statPrefTotal');
        const statPrefDate = document.getElementById('statPrefDate');
        if (statPref) {
            const p = flow && flow.pref_total;
            statPref.textContent = p && p.total_m != null ? formatUsd(p.total_m * 1e6) : '-';
            if (statPrefDate) {
                statPrefDate.textContent = !p ? '' :
                    (p.source === 'sec-10q'
                        ? `10-Q (${p.asof}) + ATM ihraçları`
                        : `Strategy resmi (${p.asof})`);
            }
        }

        renderCashChart(actuals, flow || {});
        renderCashCalc(flow || {});
        renderBacktestNote(flow || {});
    } catch (e) {
        console.error('Cash fetch error:', e);
    }
}

// Step-by-step reconciliation: from the last reported 10-Q/10-K cash down
// to today's estimate and the runway — every line item spelled out.
function renderCashCalc(flow) {
    const el = document.getElementById('cashCalc');
    if (!el) return;
    const c = flow.change_summary;
    const r = flow.runway;
    const cal = flow.calibration || {};
    if (!c) {
        el.innerHTML = '';
        return;
    }

    const money = (m) => formatUsd(Math.abs(m) * 1e6);
    const row = (label, val, cls = '') =>
        `<tr class="${cls}"><td>${label}</td><td class="calc-amount">${val}</td></tr>`;

    const official = flow.official;
    const isReserve = flow.cash_source === 'sec-8k';
    const r0 = flow.runway;
    const anchorLabel = c.since_form === 'sec-8k'
        ? `USD Reserve (SEC 8-K, ${c.since})`
        : c.since_form === 'strategy.com'
        ? `Strategy resmi nakit (strategy.com, ${c.since})`
        : `Son bilanço nakdi (10-Q/10-K, ${c.since})`;

    let rows = '';
    // Headline: the real current USD Reserve (parsed weekly from the 8-Ks)
    if (isReserve && r0) {
        rows += row(`<strong>USD Reserve — gerçek (SEC 8-K, ${r0.basis_date})</strong>`,
                    `<strong>${formatUsd(r0.basis_cash_m * 1e6)}</strong>`, 'calc-total');
        if (flow.current_estimate) {
            const est = flow.current_estimate.cash_m;
            const diff = est - r0.basis_cash_m;
            rows += row('&nbsp;&nbsp;&nbsp;↳ bizim saf tahmin (kıyas)',
                        `${formatUsd(est * 1e6)} (${diff >= 0 ? '+' : '−'}${formatUsd(Math.abs(diff) * 1e6)} sapma)`,
                        'calc-sub');
        }
    } else if (official && official.usd_reserve_m != null) {
        rows += row(`<strong>Strategy resmi USD Reserve (${official.asof})</strong>`,
                    `<strong>${formatUsd(official.usd_reserve_m * 1e6)}</strong>`, 'calc-total');
    }
    rows += row(anchorLabel, formatUsd(c.from_cash_m * 1e6), 'calc-base');

    if (c.atm_total_m > 0) {
        rows += row(`+ ATM hisse satışları (${c.weeks} hafta)`, '+' + money(c.atm_total_m));
        Object.entries(c.atm_by_ticker || {})
            .filter(([, v]) => v > 0)
            .sort((a, b) => b[1] - a[1])
            .forEach(([t, v]) => {
                rows += row(`&nbsp;&nbsp;&nbsp;↳ ${t}`, money(v), 'calc-sub');
            });
    } else {
        rows += row('+ ATM hisse satışları', 'Yok', 'calc-base');
    }
    rows += row('+ BTC satış geliri', c.btc_sales_m > 0 ? '+' + money(c.btc_sales_m) : 'Yok',
                c.btc_sales_m > 0 ? '' : 'calc-base');
    rows += row('− BTC alımları', c.btc_buys_m > 0 ? '−' + money(c.btc_buys_m) : 'Yok',
                c.btc_buys_m > 0 ? '' : 'calc-base');
    rows += row(`− Pref. temettü (${c.weeks} hafta × ${money(cal.weekly_dividend_m || 0)})`,
                '−' + money(c.dividends_m));
    if (c.other_m !== 0) {
        const otherLabel = c.other_m > 0 ? '− Diğer net giderler (kalibre)' : '+ Diğer net girişler (kalibre)';
        rows += row(otherLabel, (c.other_m > 0 ? '−' : '+') + money(c.other_m));
    }
    rows += row('<strong>= Tahmini nakit (bugün)</strong>',
                `<strong>${formatUsd(c.to_cash_m * 1e6)}</strong>`, 'calc-total');
    if (r) {
        const runwayText = r.infinite
            ? '∞ (net akış pozitif)'
            : `<strong>~${r.weeks} hafta</strong> (tükeniş: ${r.depletion_date || '-'})`;
        rows += row('<strong>→ Satış/ATM olmadan dayanma</strong>', runwayText, 'calc-total');
    }
    if (cal.monthly_dividend_m) {
        const src = cal.dividend_source === 'strategy.com' ? 'Strategy resmi'
                  : cal.dividend_source === 'sec-10q' ? 'SEC 10-Q resmi (notional × oran)'
                  : cal.dividend_source === 'xbrl_actual' ? 'SEC XBRL (ödenen ×4)' : 'model';
        let divText = `${formatUsd(cal.monthly_dividend_m * 1e6)}/ay`;
        if (cal.annual_dividend_m) divText += ` — yıllık ${formatUsd(cal.annual_dividend_m * 1e6)}`;
        divText += ` (${src})`;
        const d = cal.dividend_detail;
        if (d && d.baseline_annual_m != null) {
            const seriesBits = d.series ? Object.entries(d.series)
                .map(([t, s]) => `${t} ${formatUsd(s.notional_m * 1e6)}@%${(s.rate * 100).toFixed(2)}`)
                .join(' · ') : '';
            divText += `<br><span class="calc-sub">= 10-Q pref. tablosu (${cal.dividend_asof}) ` +
                       `${formatUsd(d.baseline_annual_m * 1e6)}/yıl + çeyrek sonrası ATM ihracı ` +
                       `${formatUsd(d.atm_added_annual_m * 1e6)}/yıl` +
                       (seriesBits ? `<br>${seriesBits}` : '') + `</span>`;
        } else if (d && d.atm_added_annual_m > 0) {
            divText += `<br><span class="calc-sub">= son çeyrek ödenen ` +
                       `${formatUsd(d.xbrl_quarter_paid_m * 1e6)} × 4 + ` +
                       `çeyrek sonrası ATM pref. ihracı ${formatUsd(d.atm_added_annual_m * 1e6)}/yıl</span>`;
        }
        rows += row('Pref. hisselere temettü yükü', divText, 'calc-info');
    }
    if (official && (official.pref_m != null || official.debt_m != null)) {
        let bits = [];
        if (official.pref_m != null) bits.push(`Pref: ${formatUsd(official.pref_m * 1e6)}`);
        if (official.debt_m != null) bits.push(`Borç: ${formatUsd(official.debt_m * 1e6)}`);
        if (official.annual_dividends_m != null) bits.push(`Yıllık temettü: ${formatUsd(official.annual_dividends_m * 1e6)}`);
        rows += row(`Strategy resmi (${official.asof})`, bits.join(' · '), 'calc-info');
    }
    if (flow.filing_info) {
        const fi = flow.filing_info;
        rows += row('Son bilanço raporu',
                    `${fi.last_form} — ${fi.last_filed} tarihinde geldi (${fi.last_period_end} dönemi)`,
                    'calc-info');
        rows += row('Sonraki 10-Q (beklenen)',
                    `~${fi.expected_next_filed} (${fi.next_quarter_end} çeyreği; son raporların ort. gecikmesi ${fi.avg_lag_days} gün)`,
                    'calc-info');
    }
    rows += `<tr class="calc-info"><td colspan="2">Not: Konvertibl tahvil ihraç/itfaları haftalık 8-K'larda açıklanmaz; ` +
            `bu akışlar kalibre edilen "diğer" kaleminde emilir. Kesin rakam her çeyrek 10-Q ile yeniden sabitlenir. ` +
            `ATM rakamlarını hafta hafta, filing linkleriyle denetlemek için: <a href="/api/atm_audit" target="_blank" class="table-link">/api/atm_audit</a></td></tr>`;

    el.innerHTML = `<table class="calc-table"><tbody>${rows}</tbody></table>`;
}

function renderBacktestNote(flow) {
    const el = document.getElementById('cashBacktestNote');
    if (!el) return;
    const parts = [];
    if (flow.runway) {
        const r = flow.runway;
        if (r.infinite) {
            parts.push('✅ <strong>Kalibre edilmiş net akış pozitif:</strong> varlık satışı / ATM olmadan da ' +
                       'nakit tükenmiyor (işletme girişleri temettü yükünü karşılıyor).');
        } else if (r.weeks !== null) {
            parts.push(`🔥 <strong>Varlık satışı / ATM olmadan dayanma: ~${r.weeks} hafta</strong> ` +
                       `(haftalık net yükümlülük ${formatUsd(r.net_burn_per_week_m * 1e6)} — ` +
                       `tahmini tükeniş: ${r.depletion_date || '-'})`);
        }
    }
    (flow.backtest || []).forEach(b => {
        parts.push(`Geri-test ${b.quarter_end}: tahmin ${formatUsd(b.predicted_m * 1e6)} vs gerçek ` +
                   `${formatUsd(b.actual_m * 1e6)} (sapma %${b.error_pct !== null ? b.error_pct : '-'})`);
    });
    if (flow.calibration) {
        const c = flow.calibration;
        const srcLabel = c.dividend_source === 'strategy.com' ? 'Strategy resmi'
                       : c.dividend_source === 'sec-10q' ? 'SEC 10-Q resmi'
                       : c.dividend_source === 'xbrl_actual' ? 'SEC XBRL (ödenen ×4)' : 'model';
        const annualBit = c.annual_dividend_m ? ` = yıllık ${formatUsd(c.annual_dividend_m * 1e6)}` : '';
        parts.push(`Temettü: ${formatUsd(c.weekly_dividend_m * 1e6)}/hafta${annualBit} (${srcLabel})` +
                   ` • Kalibre diğer giderler: ${formatUsd(Math.abs(c.other_outflow_per_week_m) * 1e6)}/hafta`);
    }
    el.innerHTML = parts.join('<br>');
}

function renderCashChart(actuals, flow) {
    const canvas = document.getElementById('cashChart');
    if (!canvas) return;

    const estimate = flow.estimate || [];
    const projection = flow.projection || [];

    // Union of dates: actual quarter-ends + weekly estimate + runway projection
    const labelSet = new Set();
    actuals.forEach(a => labelSet.add(a.period_end));
    estimate.forEach(e => labelSet.add(e.date));
    projection.forEach(p => labelSet.add(p.date));
    const labels = [...labelSet].sort();

    const actualByDate = Object.fromEntries(actuals.map(a => [a.period_end, a.value]));
    const estByDate = Object.fromEntries(estimate.map(e => [e.date, e.cash_m * 1e6]));
    const estDetail = Object.fromEntries(estimate.map(e => [e.date, e]));
    const projByDate = Object.fromEntries(projection.map(p => [p.date, p.cash_m * 1e6]));
    // Connect the projection to its starting point (the current estimate)
    if (projection.length && estimate.length) {
        projByDate[estimate[estimate.length - 1].date] = estimate[estimate.length - 1].cash_m * 1e6;
    }

    const actualSeries = labels.map(l => actualByDate[l] !== undefined ? actualByDate[l] : null);
    const estSeries = labels.map(l => estByDate[l] !== undefined ? estByDate[l] : null);
    const projSeries = labels.map(l => projByDate[l] !== undefined ? projByDate[l] : null);

    const ctx = canvas.getContext('2d');
    if (cashChart) {
        cashChart.destroy();
    }

    const gradient = ctx.createLinearGradient(0, 0, 0, 280);
    gradient.addColorStop(0, 'rgba(52, 211, 153, 0.30)');
    gradient.addColorStop(1, 'rgba(52, 211, 153, 0.02)');

    const actualLabel = (flow.cash_source === 'sec-8k')
        ? 'Gerçek USD Reserve (SEC 8-K, haftalık)'
        : 'Gerçek (çeyreklik bilanço)';
    const datasets = [{
        label: actualLabel,
        data: actualSeries,
        borderColor: '#34d399',
        backgroundColor: gradient,
        borderWidth: 3,
        fill: true,
        tension: 0.3,
        spanGaps: true,
        pointRadius: 5,
        pointBackgroundColor: '#34d399'
    }];
    if (estimate.length) {
        datasets.push({
            label: 'Tahmini (haftalık)',
            data: estSeries,
            borderColor: '#22d3ee',
            borderWidth: 2,
            borderDash: [6, 4],
            fill: false,
            tension: 0.2,
            spanGaps: true,
            pointRadius: 0
        });
    }
    if (projection.length) {
        datasets.push({
            label: 'Dayanma projeksiyonu (yeni finansman yok)',
            data: projSeries,
            borderColor: '#f87171',
            borderWidth: 2,
            borderDash: [3, 4],
            fill: false,
            tension: 0,
            spanGaps: true,
            pointRadius: 0
        });
    }

    cashChart = new Chart(ctx, {
        type: 'line',
        data: { labels: labels, datasets: datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    labels: { color: '#97a3b6', font: { family: 'Inter', size: 11 } }
                },
                tooltip: {
                    filter: (item) => item.parsed.y !== null,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${formatUsd(context.parsed.y)}`;
                        },
                        // Weekly driver breakdown: WHY the estimate moved
                        afterBody: function(items) {
                            const e = items.length ? estDetail[items[0].label] : null;
                            if (!e) return [];
                            const lines = ['— Bu haftanın kalemleri —'];
                            (e.atm_detail || []).forEach(d => {
                                lines.push(`+ ATM ${d.ticker}: ${formatUsd(d.net_m * 1e6)}`);
                            });
                            if (e.btc_m > 0) lines.push(`+ BTC satışı: ${formatUsd(e.btc_m * 1e6)}`);
                            if (e.btc_m < 0) lines.push(`− BTC alımı: ${formatUsd(Math.abs(e.btc_m) * 1e6)}`);
                            if (!e.atm_detail?.length && e.btc_m === 0) lines.push('İşlem yok');
                            if (e.div_m > 0) lines.push(`− Temettü: ${formatUsd(e.div_m * 1e6)}`);
                            if (e.other_m !== 0) {
                                lines.push(`${e.other_m > 0 ? '−' : '+'} Diğer: ${formatUsd(Math.abs(e.other_m) * 1e6)}`);
                            }
                            return lines;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(148,163,184,0.05)' },
                    ticks: {
                        color: '#97a3b6',
                        font: { family: 'Inter', size: 10 },
                        maxTicksLimit: 12
                    }
                },
                y: {
                    grid: { color: 'rgba(148,163,184,0.08)' },
                    ticks: {
                        color: '#34d399',
                        font: { family: 'Inter', size: 10 },
                        callback: function(value) { return formatUsd(value); }
                    },
                    title: { display: true, text: 'Nakit ($)', color: '#34d399' }
                }
            }
        }
    });
}

// Dividend-paying products (preferred series) + total monthly expense
async function fetchDividends() {
    try {
        const d = await (await fetch('/api/dividends')).json();
        const tbody = document.getElementById('dividendTableBody');
        if (!tbody) return;

        if (!d.series || !d.series.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-cell">Temettü verisi bulunamadı.</td></tr>';
            return;
        }

        tbody.innerHTML = d.series.map(s => `
            <tr>
                <td><span class="atm-ticker">${s.ticker}</span> <span class="div-freq">(${s.frequency})</span></td>
                <td>%${(s.rate * 100).toFixed(2)}</td>
                <td>$${s.outstanding_notional_m.toLocaleString('tr-TR', { maximumFractionDigits: 1 })}M</td>
                <td><strong>$${s.monthly_cost_m.toLocaleString('tr-TR', { maximumFractionDigits: 2 })}M</strong></td>
            </tr>`).join('') + `
            <tr class="dividend-total-row">
                <td colspan="3"><strong>Model Toplam (aylık)</strong></td>
                <td><strong>$${d.model_monthly_total_m.toLocaleString('tr-TR', { maximumFractionDigits: 2 })}M</strong></td>
            </tr>`;

        const sum = document.getElementById('dividendSummary');
        if (sum) {
            let html = '';
            if (d.actual_last_quarter) {
                html += `Gerçek ödenen (XBRL, ${d.actual_last_quarter.period_end} çeyreği): ` +
                        `${formatUsd(d.actual_last_quarter.paid_usd)} → aylık ort. ` +
                        `<strong>${formatUsd(d.actual_last_quarter.monthly_avg_usd)}</strong>`;
                if (d.model_vs_actual_pct !== null && d.model_vs_actual_pct !== undefined) {
                    html += ` • Model sapması: %${d.model_vs_actual_pct}`;
                }
            } else {
                html += 'Gerçek temettü verisi ilk XBRL senkronunda yüklenecek.';
            }
            if (!d.baselines_configured) {
                html += '<br>Not: IPO baz nominalleri yapılandırılmadı — model yalnızca izlenen ATM satışlarını ' +
                        'sayar (env: STRF_BASELINE_M, STRK_BASELINE_M, STRD_BASELINE_M, STRC_BASELINE_M).';
            }
            sum.innerHTML = html;
        }
    } catch (e) {
        console.error('Dividend fetch error:', e);
    }
}

// Render Outstanding Debt Bar Chart using Chart.js
function renderDebtChart(chartData) {
    const labels = chartData.map(d => d.filing_date);
    const debts = chartData.map(d => {
        const raw = (d.total_debt || "").replace(/[$,B,M]/g, '').strip();
        return parseFloat(raw) || 0;
    });

    const ctx = document.getElementById('debtChart').getContext('2d');

    if (debtChart) {
        debtChart.destroy();
    }

    const gradient = ctx.createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, 'rgba(167, 139, 250, 0.45)');
    gradient.addColorStop(1, 'rgba(167, 139, 250, 0.02)');

    debtChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Toplam Borç (Tahvil)',
                data: debts,
                backgroundColor: gradient,
                borderColor: '#a78bfa',
                borderWidth: 2,
                borderRadius: 6,
                barThickness: 'flex',
                maxBarThickness: 45
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#97a3b6',
                        font: { family: 'Inter', size: 11 }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(148,163,184,0.05)' },
                    ticks: { color: '#97a3b6', font: { family: 'Inter', size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(148,163,184,0.08)' },
                    ticks: {
                        color: '#a78bfa',
                        font: { family: 'Inter', size: 10 },
                        callback: function(value) { return '$' + value + 'B'; }
                    },
                    title: { display: true, text: 'Tahvil Borç Miktarı ($ Milyar)', color: '#a78bfa' }
                }
            }
        }
    });
}

// Setup Event Listeners for actions
function setupActions() {
    const btnForceCheck = document.getElementById('btnForceCheck');
    const btnSimulateAlert = document.getElementById('btnSimulateAlert');

    btnForceCheck.addEventListener('click', async () => {
        const password = prompt('Lütfen yönetici şifresini girin (Zorla Sorgu):');
        if (password === null) return;
        
        writeConsole('Zorla SEC kontrolü sorgusu gönderiliyor...');
        try {
            const resp = await fetch(`/api/trigger?type=poll&password=${encodeURIComponent(password)}`, { method: 'POST' });
            
            if (resp.status === 401) {
                writeConsole('Hata: Yetkisiz işlem. Şifre hatalı.');
                showToast('Hatalı Şifre!', true);
                return;
            }
            
            const data = await resp.json();
            if (data.status === 'success') {
                writeConsole(`Sorgulama tamamlandı: ${data.message}`);
                showToast(data.message);
                fetchStatus();
                fetchHistory();
            } else {
                writeConsole(`Hata: ${data.message}`);
                showToast(data.message, true);
            }
        } catch (e) {
            writeConsole(`Hata: Sunucuya bağlanılamadı (${e.message})`);
            showToast('Sunucu hatası', true);
        }
    });

    btnSimulateAlert.addEventListener('click', async () => {
        const password = prompt('Lütfen yönetici şifresini girin (Test Alımı):');
        if (password === null) return;
        
        writeConsole('Groq ve Telegram entegrasyonu test ediliyor. Son SEC bildirimi okunuyor...');
        try {
            const resp = await fetch(`/api/trigger?type=test&password=${encodeURIComponent(password)}`, { method: 'POST' });
            
            if (resp.status === 401) {
                writeConsole('Hata: Yetkisiz işlem. Şifre hatalı.');
                showToast('Hatalı Şifre!', true);
                return;
            }
            
            const data = await resp.json();
            if (data.status === 'success') {
                writeConsole(`Test Başarılı! Rapor Analizi:\n\n${data.preview}`);
                showToast('Test alım bildirimi Telegram\'a atıldı!');
            } else {
                writeConsole(`Test Hatası: ${data.message}`);
                showToast(data.message, true);
            }
        } catch (e) {
            writeConsole(`Hata: Sunucuya bağlanılamadı (${e.message})`);
            showToast('Sunucu hatası', true);
        }
    });
}

// Initial initialization
document.addEventListener('DOMContentLoaded', () => {
    if (typeof String.prototype.strip === 'undefined') {
        String.prototype.strip = function() {
            return this.trim();
        };
    }

    fetchStatus();
    fetchHistory();
    fetchCash();
    fetchDividends();
    setupActions();

    // Auto-refresh status every 20 seconds
    setInterval(() => {
        fetchStatus();
    }, 20000);

    // Refresh the data panels every 60s so new filings/quarters and the
    // recalculated estimate appear without a manual reload
    setInterval(() => {
        fetchHistory();
        fetchCash();
        fetchDividends();
    }, 60000);
});

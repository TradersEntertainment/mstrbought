let portfolioChart = null;
let debtChart = null;

// Helper to show toast messages
function showToast(message, isError = false) {
    const toast = document.getElementById('notificationToast');
    const toastIcon = toast.querySelector('i');
    const toastMsg = toast.querySelector('.toast-message');

    toastMsg.textContent = message;
    if (isError) {
        toast.style.borderColor = 'rgba(239, 68, 68, 0.4)';
        toastIcon.className = 'fa-solid fa-circle-xmark';
        toastIcon.style.color = '#ef4444';
    } else {
        toast.style.borderColor = 'rgba(0, 229, 255, 0.3)';
        toastIcon.className = 'fa-solid fa-circle-check';
        toastIcon.style.color = '#00e5ff';
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
                    acquiredBadgeHtml = `<span class="badge-acquired">+${acqNum.toLocaleString('tr-TR')} BTC</span>`;
                } else {
                    acquiredBadgeHtml = `<span class="badge-acquired">+${rawAcq} BTC</span>`;
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
            const financingBadgeHtml = `<span class="badge-source ${fBadgeClass}">${fSource}</span>`;

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
        const chartData = [...data].reverse(); // Chronological order
        renderPortfolioChart(chartData);
        renderDebtChart(chartData);

    } catch (error) {
        console.error('History fetch error:', error);
        document.getElementById('historyTableBody').innerHTML = `<tr><td colspan="5" class="loading-cell" style="color: #ef4444;">Veriler yüklenirken hata oluştu!</td></tr>`;
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
                    borderColor: '#00e5ff',
                    backgroundColor: 'rgba(0, 229, 255, 0.04)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    label: 'Toplam Kümülatif Maliyet ($ Milyar)',
                    data: costs,
                    borderColor: '#2979ff',
                    backgroundColor: 'rgba(41, 121, 255, 0.02)',
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
                        color: '#9ca3af',
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
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { color: '#9ca3af', font: { family: 'Inter', size: 10 } }
                },
                y: {
                    position: 'left',
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        color: '#00e5ff',
                        font: { family: 'Inter', size: 10 },
                        callback: function(value) { return value.toLocaleString('tr-TR'); }
                    },
                    title: { display: true, text: 'BTC Miktarı', color: '#00e5ff' }
                },
                y1: {
                    position: 'right',
                    grid: { drawOnChartArea: false },
                    ticks: {
                        color: '#2979ff',
                        font: { family: 'Inter', size: 10 },
                        callback: function(value) { return '$' + value + 'B'; }
                    },
                    title: { display: true, text: 'Maliyet ($ Milyar)', color: '#2979ff' }
                }
            }
        }
    });
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
    gradient.addColorStop(0, 'rgba(124, 77, 255, 0.45)');
    gradient.addColorStop(1, 'rgba(124, 77, 255, 0.02)');

    debtChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Toplam Borç (Tahvil)',
                data: debts,
                backgroundColor: gradient,
                borderColor: '#7c4dff',
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
                        color: '#9ca3af',
                        font: { family: 'Inter', size: 11 }
                    }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    ticks: { color: '#9ca3af', font: { family: 'Inter', size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        color: '#7c4dff',
                        font: { family: 'Inter', size: 10 },
                        callback: function(value) { return '$' + value + 'B'; }
                    },
                    title: { display: true, text: 'Tahvil Borç Miktarı ($ Milyar)', color: '#7c4dff' }
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
    setupActions();

    // Auto-refresh status and history every 20 seconds
    setInterval(() => {
        fetchStatus();
    }, 20000);
});

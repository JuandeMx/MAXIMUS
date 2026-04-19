/* ==========================================
   MAXIMUS LIVE ENGINE v3.1
   Custom SSE Real-Time Monitor
   ========================================== */

let mainChart;
let history = { cpu: Array(30).fill(0), ram: Array(30).fill(0) };

document.addEventListener('DOMContentLoaded', () => {
    console.log("Maximus v3.1 Engine Starting...");
    initChart();
    startStream();
});

function startStream() {
    const dot = document.getElementById('stream-dot');
    const txt = document.getElementById('stream-text');

    const es = new EventSource('/api/stream');

    es.onmessage = (e) => {
        const data = JSON.parse(e.data);
        console.log("Data:", data);
        updateUI(data);
        
        dot.style.background = '#10b981';
        dot.style.boxShadow = '0 0 10px #10b981';
        txt.innerText = 'EN VIVO';
    };

    es.onerror = () => {
        dot.style.background = '#ef4444';
        dot.style.boxShadow = '0 0 10px #ef4444';
        txt.innerText = 'RECONECTANDO...';
    };
}

function updateUI(data) {
    if (!data) return;

    // CPU
    const cpu = data.cpu?.load || 0;
    document.getElementById('val-cpu').innerText = `${cpu}%`;
    document.getElementById('fill-cpu').style.width = `${cpu}%`;
    document.getElementById('val-cpu-detail').innerText = `${data.cpu?.cores || '--'} cores · ${data.cpu?.model || '--'}`;

    // RAM
    const ramPerc = data.ram?.percent || 0;
    document.getElementById('val-ram').innerText = `${ramPerc}%`;
    document.getElementById('fill-ram').style.width = `${ramPerc}%`;
    document.getElementById('val-ram-detail').innerText = `${data.ram?.used || 0} / ${data.ram?.total || 1} MB`;

    // DISK
    const diskPerc = data.disk?.percent || 0;
    document.getElementById('val-disk').innerText = `${diskPerc}%`;
    document.getElementById('fill-disk').style.width = `${diskPerc}%`;
    document.getElementById('val-disk-detail').innerText = `${data.disk?.used || '--'} / ${data.disk?.total || '--'}`;

    // ONLINE
    document.getElementById('val-online').innerText = data.online || '0';
    document.getElementById('val-users').innerText = data.total_users || '0';

    // NET
    document.getElementById('val-rx').innerText = `${data.net?.rx || 0} GB`;
    document.getElementById('val-tx').innerText = `${data.net?.tx || 0} GB`;

    // SYS
    document.getElementById('val-uptime').innerText = data.sys?.uptime || '--';
    document.getElementById('val-host').innerText = data.sys?.hostname || '--';
    document.getElementById('val-kernel').innerText = data.sys?.kernel || '--';
    document.getElementById('val-os').innerText = data.sys?.os || '--';
    document.getElementById('display-ip').innerText = data.sys?.ip || '0.0.0.0';

    // CHART
    history.cpu.push(cpu);
    history.cpu.shift();
    history.ram.push(parseFloat(ramPerc));
    history.ram.shift();
    if (mainChart) mainChart.update('none');
}

function initChart() {
    const canvas = document.getElementById('mainChart');
    if (!canvas) return;

    try {
        const ctx = canvas.getContext('2d');
        mainChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array(30).fill(''),
                datasets: [
                    {
                        label: 'CPU',
                        data: history.cpu,
                        borderColor: '#06b6d4',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 0,
                        fill: true,
                        backgroundColor: 'rgba(6, 182, 212, 0.1)'
                    },
                    {
                        label: 'RAM',
                        data: history.ram,
                        borderColor: '#8b5cf6',
                        borderWidth: 2,
                        tension: 0.4,
                        pointRadius: 0,
                        fill: true,
                        backgroundColor: 'rgba(139, 92, 246, 0.1)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: false },
                    y: { 
                        beginAtZero: true, 
                        max: 100, 
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#475569', font: { size: 10 } }
                    }
                }
            }
        });
    } catch (e) {
        console.warn("Chart.js failed:", e);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize Calibration Chart
    const ctxCal = document.getElementById('calibrationChart').getContext('2d');
    new Chart(ctxCal, {
        type: 'line',
        data: {
            labels: ['1.0', '0.9', '0.8', '0.7', '0.6', '0.5', '0.4'],
            datasets: [{
                label: 'Actual Accuracy %',
                data: [98, 92, 85, 71, 55, 42, 30], // Mocked for demo visualization
                borderColor: '#7c4dff',
                backgroundColor: 'rgba(124, 77, 255, 0.1)',
                fill: true,
                tension: 0.4
            }, {
                label: 'Perfect Calibration',
                data: [100, 90, 80, 70, 60, 50, 40],
                borderColor: 'rgba(255, 255, 255, 0.2)',
                borderDash: [5, 5],
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } },
                x: { grid: { display: false }, ticks: { color: '#888' } }
            },
            plugins: { legend: { labels: { color: '#fff', font: { family: 'Outfit' } } } }
        }
    });

    // 2. Initialize Heatmap (Mocked Bar)
    const ctxHeat = document.getElementById('heatmapChart').getContext('2d');
    new Chart(ctxHeat, {
        type: 'bar',
        data: {
            labels: ['Gemini Flash', 'Sarvam-1', 'Sonnet 3.5', 'GPT-4o'],
            datasets: [{
                label: 'Hallucination Rate %',
                data: [12, 8, 4, 2],
                backgroundColor: 'rgba(255, 82, 82, 0.5)'
            }, {
                label: 'Reasoning Failure %',
                data: [18, 14, 2, 1],
                backgroundColor: 'rgba(124, 77, 255, 0.5)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { stacked: true, beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#888' } },
                x: { stacked: true, grid: { display: false }, ticks: { color: '#888' } }
            },
            plugins: { legend: { labels: { color: '#fff' } } }
        }
    });

    // 3. Fetch Real Traces (Priority 04 Integration)
    const fetchTraces = async () => {
        try {
            const response = await fetch('/admin/traces');
            if (response.ok) {
                const data = await response.json();
                const traceBody = document.getElementById('traceBody');
                traceBody.innerHTML = '';
                
                data.traces.forEach(trace => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${new Date(trace.timestamp).toLocaleTimeString()}</td>
                        <td>${trace.initial_route}</td>
                        <td>${trace.complexity.toFixed(2)}</td>
                        <td>${trace.confidence.toFixed(2)}</td>
                        <td>${trace.latency_ms.toFixed(0)}ms</td>
                        <td><span class="tag ${trace.escalated ? 'escalated' : 'cheap'}">${trace.escalated ? 'Escalated' : 'Frugal'}</span></td>
                    `;
                    traceBody.appendChild(row);
                });
            }
        } catch (e) {
            console.error("Dashboard fetch failed: ", e);
        }
    };

    fetchTraces();
    setInterval(fetchTraces, 5000); // Live poll every 5s
});

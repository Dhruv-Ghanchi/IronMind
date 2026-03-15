document.getElementById('analyzeBtn')?.addEventListener('click', async () => {
    const url = document.getElementById('repoUrl').value;
    const status = document.getElementById('status');
    
    if (!url) return alert('Enter a GitHub URL');
    
    status.innerText = 'Initializing Architect Brain...';
    
    try {
        const response = await fetch('http://localhost:8005/analyze', {
            method: 'POST',
            body: JSON.stringify({ url })
        });
        
        if (response.ok) {
            window.location.href = 'graph.html';
        }
    } catch (e) {
        status.innerText = 'Simulation Mode: Redirecting to Graph...';
        setTimeout(() => window.location.href = 'graph.html', 1500);
    }
});

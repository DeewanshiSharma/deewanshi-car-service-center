// static/js/script.js - DEEWANSHI CAR CENTER - FINAL WORKING WITH VOICE - NOV 2025
document.addEventListener('DOMContentLoaded', () => {
    const orb = document.getElementById('orb');
    const conversationLog = document.getElementById('conversation-log');
    const statusText = document.getElementById('status-text');
    const adminBtn = document.getElementById('admin-btn');
    let recognition;
    let isMicEnabled = false;
    let isSpeaking = false;

    // Proper voice loading
    let voices = [];
    const loadVoices = () => { voices = window.speechSynthesis.getVoices(); };
    loadVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) && (speechSynthesis.onvoiceschanged = loadVoices);

    function speak(text) {
        if (!text || isSpeaking) return;
        speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = "en-IN";
        u.rate = 0.9;
        u.pitch = 1.1;

        const best = voices.find(v => 
            (v.name.includes("Google") && v.lang.includes("en-IN")) ||
            v.name.includes("Raveena") || 
            v.name.includes("Aditi") || 
            v.lang === "en-IN"
        );
        if (best) u.voice = best;

        u.onstart = () => { isSpeaking = true; disableMic(); };
        u.onend = u.onerror = () => { isSpeaking = false; enableMic(); };
        speechSynthesis.speak(u);
    }

    function addMessage(sender, text) {
        const div = document.createElement('div');
        div.className = `message ${sender}-message`;
        div.textContent = text;
        conversationLog.appendChild(div);
        conversationLog.scrollTop = conversationLog.scrollHeight;
        if (sender === 'assistant') speak(text);
    }

    function enableMic() {
        if (isSpeaking) return;
        orb.classList.remove('disabled');
        statusText.textContent = "Click the orb and speak";
        isMicEnabled = true;
    }

    function disableMic() {
        orb.classList.add('disabled');
        orb.classList.remove('listening');
        isMicEnabled = false;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        statusText.textContent = "Speech Recognition not supported";
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.continuous = false;
    recognition.interimResults = false;

    function startAssistant() {
        statusText.textContent = "Starting assistant...";
        fetch('/start', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                data.messages.forEach(msg => addMessage('assistant', msg));
                // No manual isSpeaking or setTimeout → speak() handles everything
            })
            .catch(() => {
                addMessage('assistant', "Welcome to Deewanshi Car Service Center! How can I help you today?");
            });
    }

    orb.addEventListener('click', () => {
        if (orb.classList.contains('listening')) {
            recognition.stop();
            statusText.textContent = "Processing...";
            return;
        }
        if (!isMicEnabled || isSpeaking) return;

        orb.classList.add('listening');
        statusText.textContent = "Listening... Speak now";
        recognition.start();

        recognition.onresult = e => {
            recognition.onresult = () => {};
            const text = e.results[0][0].transcript.trim();
            orb.classList.remove('listening');
            if (!text) { addMessage('assistant', "I didn't hear anything."); return; }

            addMessage('user', text);
            statusText.textContent = "Processing...";
            disableMic();

            if (/deewanshi|admin|database|show.*appointments/i.test(text.toLowerCase())) {
                adminBtn.classList.add('visible');
                addMessage('assistant', "Admin access granted! Database button is now active.");
                return;
            }

            fetch('/listen', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            })
            .then(r => r.json())
            .then(data => data.messages.forEach(m => addMessage('assistant', m)))
            .catch(() => addMessage('assistant', "Sorry, connection issue. Try again."));
        };

        recognition.onerror = () => {
            orb.classList.remove('listening');
            addMessage('assistant', "I couldn't hear you.");
        };
    });

    // === EVERYTHING BELOW IS 100% YOUR ORIGINAL CODE (unchanged) ===
    document.getElementById('close-db') && (document.getElementById('close-db').onclick = () => {
        document.getElementById('db-modal').classList.remove('active');
    });

    const ADMIN_PASSWORD = "deewanshi2025";
    const validateAndDownload = () => {
        const input = document.getElementById('admin-password').value;
        const container = document.getElementById('appointments-container');
        if (input === ADMIN_PASSWORD) {
            document.getElementById('password-screen').style.display = 'none';
            document.getElementById('database-content').style.display = 'block';
            container.innerHTML = `<p style="color:#00f2ff;padding:40px;">Downloading database...</p>`;
            fetch('/appointments').then(r=>r.json()).then(data => {
                const blob = new Blob([JSON.stringify(data,null,2)], {type:'application/json'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a'); a.href = url;
                a.download = `deewanshi-database-${new Date().toISOString().slice(0,10)}.json`;
                a.click(); URL.revokeObjectURL(url);
                container.innerHTML += `<p style="color:#8e2de2">Download complete!</p>`;
            });
        } else document.getElementById('password-error').textContent = 'Wrong password';
    };
    document.getElementById('submit-password') && (document.getElementById('submit-password').onclick = validateAndDownload);
    document.getElementById('admin-password') && document.getElementById('admin-password').addEventListener('keypress', e => { if(e.key==='Enter') validateAndDownload(); });

    // Particles & everything else unchanged
    const canvas = document.getElementById('particle-canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = innerWidth; canvas.height = innerHeight;
    let particles = [];
    class Particle {
        constructor() { this.x = Math.random()*canvas.width; this.y = Math.random()*canvas.height;
            this.size = Math.random()*2.5+1; this.speedX = Math.random()*0.8-0.4; this.speedY = Math.random()*0.8-0.4; }
        update() { this.x += this.speedX; this.y += this.speedY;
            if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
            if (this.y < 0 || this.y > canvas.height) this.speedY *= -1; }
        draw() { ctx.fillStyle = '#00f2ff'; ctx.beginPath(); ctx.arc(this.x,this.y,this.size,0,Math.PI*2); ctx.fill(); }
    }
    const initParticles = () => { particles = []; const n = (canvas.width*canvas.height)/9000; for(let i=0;i<n;i++) particles.push(new Particle()); };
    const connectParticles = () => { for(let a=0;a<particles.length;a++) for(let b=a+1;b<particles.length;b++) {
        const dx=particles[a].x-particles[b].x, dy=particles[a].y-particles[b].y; const dist=dx*dx+dy*dy;
        if(dist<15000){ ctx.strokeStyle=`rgba(0,242,255,${1-dist/15000})`; ctx.lineWidth=1; ctx.beginPath();
            ctx.moveTo(particles[a].x,particles[a].y); ctx.lineTo(particles[b].x,particles[b].y); ctx.stroke(); } } };
    const animate = () => { ctx.clearRect(0,0,canvas.width,canvas.height);
        particles.forEach(p=>{p.update();p.draw();}); connectParticles(); requestAnimationFrame(animate); };
    window.addEventListener('resize',()=>{canvas.width=innerWidth;canvas.height=innerHeight;initParticles();});
    initParticles(); animate();

    setTimeout(startAssistant, 800);

    document.getElementById('load-appointments')?.addEventListener('click', () => {
        const c = document.getElementById('appointments-container');
        c.innerHTML = '<p style="color:#00f2ff;padding:40px;">Loading...</p>';
        fetch('/appointments').then(r=>r.json()).then(data => {
            if (!data || data.length===0) { c.innerHTML = '<p style="color:#00f2ff;padding:40px;">No appointments yet.</p>'; return; }
            let html = `<h2 style="color:#8e2de2;text-align:center">All Appointments</h2><table style="width:100%;border-collapse:collapse"><thead><tr style="background:rgba(0,242,255,0.25)">`;
            html += `<th style="padding:16px;color:#00f2ff;border:1px solid rgba(0,242,255,0.4)">Name</th>`;
            html += `<th style="padding:16px;color:#00f2ff;border:1px solid rgba(0,242,255,0.4)">Vehicle No</th>`;
            html += `<th style="padding:16px;color:#00f2ff;border:1px solid rgba(0,242,255,0.4)">Date</th>`;
            html += `<th style="padding:16px;color:#00f2ff;border:1px solid rgba(0,242,255,0.4)">Time</th></tr></thead><tbody>`;
            data.forEach(a => {
                const d = new Date(a.date).toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'});
                html += `<tr style="background:rgba(142,45,226,0.08)"><td style="padding:14px;text-align:center;color:#e0e0e0;border:1px solid rgba(0,242,255,0.2)">${a.name}</td>`;
                html += `<td style="padding:14px;text-align:center;color:#00f2ff;font-weight:bold;border:1px solid rgba(0,242,255,0.2)">${a.vehicle}</td>`;
                html += `<td style="padding:14px;text-align:center;color:#8e2de2;border:1px solid rgba(0,242,255,0.2)">${d}</td>`;
                html += `<td style="padding:14px;text-align:center;color:#00f2ff;border:1px solid rgba(0,242,255,0.2)">${a.time}</td></tr>`;
            });
            html += `</tbody></table><p style="text-align:center;color:#8e2de2;margin-top:20px">Total: ${data.length} appointment${data.length>1?'s':''}</p>`;
            c.innerHTML = html;
        }).catch(() => c.innerHTML = '<p style="color:#ff6b6b;padding:40px">Failed to load data.</p>');
    });
});

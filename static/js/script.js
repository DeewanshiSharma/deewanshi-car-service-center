// static/js/script.js - DEEWANSHI CAR CENTER - FINAL FIXED (NO DUPLICATE SPEECH) - 2025

document.addEventListener('DOMContentLoaded', () => {
    const orb = document.getElementById('orb');
    const conversationLog = document.getElementById('conversation-log');
    const statusText = document.getElementById('status-text');
    const adminBtn = document.getElementById('admin-btn');

    let recognition;
    let isMicEnabled = false;
    let isSpeaking = false;  // Now only used to block mic during backend speech

    // === ONLY DISPLAY TEXT — NO BROWSER SPEECH ===
    function addMessage(sender, text) {
        const div = document.createElement('div');
        div.className = `message ${sender}-message`;
        div.textContent = text;
        conversationLog.appendChild(div);
        conversationLog.scrollTop = conversationLog.scrollHeight;
        
        // NO speak() here anymore → only backend speaks!
    }

    // === MIC CONTROL (blocks while backend is speaking) ===
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

    // === Speech Recognition ===
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        statusText.textContent = "Speech Recognition not supported";
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.continuous = false;
    recognition.interimResults = false;

    // === Start Assistant ===
    function startAssistant() {
        statusText.textContent = "Starting assistant...";
        fetch('/start', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                isSpeaking = true;
                disableMic();
                data.messages.forEach(msg => addMessage('assistant', msg));
                setTimeout(() => {
                    isSpeaking = false;
                    enableMic();
                }, 4000); // Adjust based on your welcome message length
            });
    }

        // === Orb Click - Now with Manual Stop (click again to send instantly) ===
    orb.addEventListener('click', () => {
        // Case 1: Already listening → Click = STOP listening and send what was heard
        if (orb.classList.contains('listening')) {
            recognition.stop();                // Forces onresult with current transcript
            statusText.textContent = "Processing...";
            return;                            // onresult will handle the rest
        }

        // Case 2: Not allowed to start (speaking or mic disabled)
        if (!isMicEnabled || isSpeaking) return;

        // Case 3: Normal start listening
        orb.classList.add('listening');
        statusText.textContent = "Listening... Speak now (click again to send)";

        recognition.start();

        // ──────────────────────────────────────────────────────────────
        // These handlers are re-attached every time we start (safe & clean)
        // ──────────────────────────────────────────────────────────────
        recognition.onresult = (e) => {
    // Prevent this handler from running multiple times (safety)
    recognition.onresult = () => {};
    recognition.onerror = () => {};
    
    const userText = e.results[0][0].transcript.trim();

    // Always clean up visual state first
    orb.classList.remove('listening');

    // Empty input (user clicked orb but said nothing)
    if (!userText) {
        addMessage('assistant', "I didn't hear anything. Please try again.");
        setTimeout(() => {
            isSpeaking = false;
            enableMic();
        }, 2200);
        return;
    }

    // Show user's message
    addMessage('user', userText);
    statusText.textContent = "Processing...";
    isSpeaking = true;
    disableMic();

    // === ADMIN ACCESS TRIGGER ===
    if (/deewanshi|admin|database|show.*appointments/i.test(userText.toLowerCase())) {
        adminBtn.classList.add('visible');
        addMessage('assistant', "Admin access granted! Database button is now active.");
        setTimeout(() => {
            isSpeaking = false;
            enableMic();
        }, 2800);
        return;
    }

    // === NORMAL CONVERSATION FLOW ===
    fetch('/listen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText })
    })
    .then(r => {
        if (!r.ok) throw new Error('Network response not ok');
        return r.json();
    })
    .then(data => {
        // Display all assistant messages
        data.messages.forEach(msg => addMessage('assistant', msg));

        // Smart delay based on response length
        // === ULTRA-FAST RESPONSE (2025 Edition) ===
        const speechDelay = data.done ? 1800 : Math.min(1500, data.messages.length * 800);

        setTimeout(() => {
        isSpeaking = false;
        if (!data.done) enableMic();
        }, speechDelay);
    })
    .catch(err => {
        console.error('Listen endpoint error:', err);
        addMessage('assistant', "Sorry, I'm having trouble connecting. Please try again.");
                setTimeout(() => {
            isSpeaking = false;
            enableMic();
        }, 1800);   // ← 1.8 seconds instead of 4
    });
};
        recognition.onerror = (event) => {
            orb.classList.remove('listening');
            addMessage('assistant', "I couldn't hear you. Try again.");
            setTimeout(() => { isSpeaking = false; enableMic(); }, 1200);
        };

        recognition.onend = () => {
            // Only remove visual if not already handled by manual stop
            if (orb.classList.contains('listening')) {
                orb.classList.remove('listening');
            }
        };
    });


    // Close modal
    document.getElementById('close-db').onclick = () => {
        document.getElementById('db-modal').classList.remove('active');
    };

    // Password check + AUTO DOWNLOAD
    const ADMIN_PASSWORD = "deewanshi2025";  // Change this to your secret password!

    function validateAndDownload() {
        const input = document.getElementById('admin-password').value;
        const error = document.getElementById('password-error');
        const container = document.getElementById('appointments-container');

        if (input === ADMIN_PASSWORD) {
            error.textContent = '';
            document.getElementById('password-screen').style.display = 'none';
            document.getElementById('database-content').style.display = 'block';

            container.innerHTML = `
                <p style="color:#00f2ff; font-size:1.4em; padding:40px;">
                    Authentication successful!<br><br>
                    Downloading full database now...
                </p>
            `;

            // AUTO DOWNLOAD THE DATABASE
            fetch('/appointments')
                .then(r => r.json())
                .then(data => {
                    const json = JSON.stringify(data, null, 2);
                    const blob = new Blob([json], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `deewanshi-full-database-${new Date().toISOString().slice(0,10)}.json`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);

                    container.innerHTML += `
                        <p style="color:#8e2de2; margin-top:20px;">
                            Download complete! File saved.
                        </p>
                    `;
                })
                .catch(() => {
                    container.innerHTML += `<p style="color:#ff6b6b;">Failed to fetch data.</p>`;
                });

        } else {
            error.textContent = 'Incorrect password!';
            document.getElementById('admin-password').value = '';
            document.getElementById('admin-password').focus();
        }
    }

    // Trigger on button click or Enter key
    document.getElementById('submit-password').onclick = validateAndDownload;
    document.getElementById('admin-password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') validateAndDownload();
    });

    // === Particle Background (Your beautiful neon effect - unchanged) ===
    const canvas = document.getElementById('particle-canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = innerWidth;
    canvas.height = innerHeight;
    let particles = [];

    class Particle {
        constructor() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 2.5 + 1;
            this.speedX = Math.random() * 0.8 - 0.4;
            this.speedY = Math.random() * 0.8 - 0.4;
        }
        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
            if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
        }
        draw() {
            ctx.fillStyle = '#00f2ff';
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    function initParticles() {
        particles = [];
        const count = (canvas.width * canvas.height) / 9000;
        for (let i = 0; i < count; i++) particles.push(new Particle());
    }

    function connectParticles() {
        for (let a = 0; a < particles.length; a++) {
            for (let b = a + 1; b < particles.length; b++) {
                const dx = particles[a].x - particles[b].x;
                const dy = particles[a].y - particles[b].y;
                const distance = dx * dx + dy * dy;
                if (distance < 15000) {
                    ctx.strokeStyle = `rgba(0, 242, 255, ${1 - distance / 15000})`;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(particles[a].x, particles[a].y);
                    ctx.lineTo(particles[b].x, particles[b].y);
                    ctx.stroke();
                }
            }
        }
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => { p.update(); p.draw(); });
        connectParticles();
        requestAnimationFrame(animate);
    }

    window.addEventListener('resize', () => {
        canvas.width = innerWidth;
        canvas.height = innerHeight;
        initParticles();
    });

    initParticles();
    animate();

    // === START ===
    setTimeout(startAssistant, 800);

        // === FIXED: LOAD ALL APPOINTMENTS BUTTON (Beautiful Table) ===
    document.getElementById('load-appointments')?.addEventListener('click', () => {
        const container = document.getElementById('appointments-container');
        container.innerHTML = '<p style="color:#00f2ff; padding:40px;">Loading appointments...</p>';

        fetch('/appointments')
            .then(r => r.json())
            .then(data => {
                if (!data || data.length === 0) {
                    container.innerHTML = '<p style="color:#00f2ff; padding:40px;">No appointments yet.</p>';
                    return;
                }

                let table = `
                    <h2 style="color:#8e2de2; text-align:center; margin:20px 0;">All Appointments</h2>
                    <table style="width:100%; border-collapse:collapse; font-size:1.1em;">
                        <thead>
                            <tr style="background:rgba(0,242,255,0.25);">
                                <th style="padding:16px; color:#00f2ff; border:1px solid rgba(0,242,255,0.4);">Name</th>
                                <th style="padding:16px; color:#00f2ff; border:1px solid rgba(0,242,255,0.4);">Vehicle No</th>
                                <th style="padding:16px; color:#00f2ff; border:1px solid rgba(0,242,255,0.4);">Date</th>
                                <th style="padding:16px; color:#00f2ff; border:1px solid rgba(0,242,255,0.4);">Time</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                data.forEach(appt => {
                    const niceDate = new Date(appt.date).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric'
                    });

                    table += `
                        <tr style="background:rgba(142,45,226,0.08);">
                            <td style="padding:14px; text-align:center; border:1px solid rgba(0,242,255,0.2); color:#e0e0e0;">${appt.name}</td>
                            <td style="padding:14px; text-align:center; border:1px solid rgba(0,242,255,0.2); color:#00f2ff; font-weight:bold;">${appt.vehicle}</td>
                            <td style="padding:14px; text-align:center; border:1px solid rgba(0,242,255,0.2); color:#8e2de2;">${niceDate}</td>
                            <td style="padding:14px; text-align:center; border:1px solid rgba(0,242,255,0.2); color:#00f2ff;">${appt.time}</td>
                        </tr>
                    `;
                });

                table += `
                        </tbody>
                    </table>
                    <p style="text-align:center; margin-top:20px; color:#8e2de2;">
                        Total: ${data.length} appointment${data.length > 1 ? 's' : ''}
                    </p>
                `;

                container.innerHTML = table;
            })
            .catch(() => {
                container.innerHTML = '<p style="color:#ff6b6b; text-align:center; padding:40px;">Failed to load data.</p>';
            });
    });
});

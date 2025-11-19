// static/js/script.js - DEEWANSHI CAR CENTER - FINAL FIXED (NO DUPLICATE SPEECH) - 2025
document.addEventListener('DOMContentLoaded', () => {
    const orb = document.getElementById('orb');
    const conversationLog = document.getElementById('conversation-log');
    const statusText = document.getElementById('status-text');
    const adminBtn = document.getElementById('admin-btn');
    let recognition;
    let isMicEnabled = false;
    let isSpeaking = false;

    // FIXED: Proper voice loading (required for Google Indian voice)
    let voices = [];
    const loadVoices = () => {
        voices = window.speechSynthesis.getVoices();
    };
    loadVoices();
    if (speechSynthesis.onvoiceschanged !== undefined) {
        speechSynthesis.onvoiceschanged = loadVoices;
    }

    // FIXED: speak() + addMessage() with real Indian female voice
    function speak(text) {
        if (!text || isSpeaking) return;
        speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "en-IN";
        utterance.rate = 0.9;
        utterance.pitch = 1.1;

        const bestVoice = voices.find(v =>
            (v.name.includes("Google") && v.lang.includes("en-IN")) ||
            v.name.includes("Raveena") ||
            v.name.includes("Aditi") ||
            v.lang === "en-IN"
        );
        if (bestVoice) utterance.voice = bestVoice;

        utterance.onstart = () => { isSpeaking = true; disableMic(); };
        utterance.onend = utterance.onerror = () => { isSpeaking = false; enableMic(); };

        speechSynthesis.speak(utterance);
    }

    function addMessage(sender, text) {
        const div = document.createElement('div');
        div.className = `message ${sender}-message`;
        div.textContent = text;
        conversationLog.appendChild(div);
        conversationLog.scrollTop = conversationLog.scrollHeight;

        if (sender === 'assistant') {
            speak(text);
        }
    }

    // === MIC CONTROL ===
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

    // === Start Assistant - REMOVED hardcoded delay ===
    function startAssistant() {
        statusText.textContent = "Starting assistant...";
        fetch('/start', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                data.messages.forEach(msg => addMessage('assistant', msg));
                // No setTimeout needed - speak() controls isSpeaking automatically
            });
    }

    // === Orb Click ===
    orb.addEventListener('click', () => {
        if (orb.classList.contains('listening')) {
            recognition.stop();
            statusText.textContent = "Processing...";
            return;
        }
        if (!isMicEnabled || isSpeaking) return;

        orb.classList.add('listening');
        statusText.textContent = "Listening... Speak now (click again to send)";
        recognition.start();

        recognition.onresult = (e) => {
            recognition.onresult = () => {};
            recognition.onerror = () => {};

            const userText = e.results[0][0].transcript.trim();
            orb.classList.remove('listening');

            if (!userText) {
                addMessage('assistant', "I didn't hear anything. Please try again.");
                return;
            }

            addMessage('user', userText);
            statusText.textContent = "Processing...";
            disableMic();

            if (/deewanshi|admin|database|show.*appointments/i.test(userText.toLowerCase())) {
                adminBtn.classList.add('visible');
                addMessage('assistant', "Admin access granted! Database button is now active.");
                return;
            }

            fetch('/listen', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userText })
            })
            .then(r => {
                if (!r.ok) throw new Error('Network error');
                return r.json();
            })
            .then(data => {
                data.messages.forEach(msg => addMessage('assistant', msg));
                // No setTimeout - speak() handles timing
            })
            .catch(err => {
                console.error('Listen error:', err);
                addMessage('assistant', "Sorry, I'm having trouble connecting. Please try again.");
            });
        };

        recognition.onerror = () => {
            orb.classList.remove('listening');
            addMessage('assistant', "I couldn't hear you. Try again.");
        };

        recognition.onend = () => {
            if (orb.classList.contains('listening')) {
                orb.classList.remove('listening');
            }
        };
    });

    // === Rest of your code 100% UNCHANGED from here ↓ ===
    document.getElementById('close-db').onclick = () => {
        document.getElementById('db-modal').classList.remove('active');
    };

    const ADMIN_PASSWORD = "deewanshi2025";
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
    document.getElementById('submit-password').onclick = validateAndDownload;
    document.getElementById('admin-password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') validateAndDownload();
    });

    // Particle Background - untouched
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

    // START
    setTimeout(startAssistant, 800);

    // Load appointments table - untouched
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
                        { day: 'numeric', month: 'long', year: 'numeric' });
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

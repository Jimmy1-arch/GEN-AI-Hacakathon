let currentState = {
    patient_statement: "",
    current_case: null,
    initial_statement: "",
    pending_questions: []
};

const chatHistory = document.getElementById('chatHistory');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');

function startDemo(type) {
    if (type === 'fever') {
        chatInput.value = "I have had a mild fever since yesterday.";
    } else if (type === 'chest_pain') {
        chatInput.value = "I have severe chest pain and I'm having difficulty breathing right now.";
    } else if (type === 'null_case') {
        chatInput.value = "My shoulder feels strange when I sit for a long time.";
    }
    sendMessage();
}

function handleEnter(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function appendUserMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message user-message';
    msgDiv.innerHTML = `
        <div class="avatar user-avatar">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
        </div>
        <div class="bubble">${text}</div>
    `;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function appendAiMessage(text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message ai-message';
    msgDiv.innerHTML = `
        <div class="avatar ai-avatar">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 0 1 10 10v4a2 2 0 0 1-2 2h-2.5a2.5 2.5 0 0 1-2.5-2.5v-3a2.5 2.5 0 0 1 2.5-2.5h2.5A8 8 0 0 0 12 4a8 8 0 0 0-8 8h2.5a2.5 2.5 0 0 1 2.5 2.5v3a2.5 2.5 0 0 1-2.5 2.5H4a2 2 0 0 1-2-2v-4a10 10 0 0 1 10-10z"/></svg>
        </div>
        <div class="bubble">${text}</div>
    `;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    
    appendUserMessage(text);
    chatInput.value = '';
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<div class="loading"></div>';
    
    if (currentState.pending_questions.length > 0) {
        // It's a follow-up answer
        const q = currentState.pending_questions[0];
        currentState.patient_statement = `Patient answered: "${text}" in response to: "${q}"`;
    } else {
        // Initial statement
        currentState.patient_statement = text;
        currentState.initial_statement = text;
        currentState.current_case = null;
    }
    
    await sendAssessmentRequest();
}

async function sendAssessmentRequest() {
    try {
        const res = await fetch('/api/assess', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentState)
        });
        
        if (!res.ok) throw new Error("Server Error");
        const data = await res.json();
        
        // Play TTS Voice
        if (data.audio_base64) {
            try {
                const audio = new Audio("data:audio/mp3;base64," + data.audio_base64);
                audio.play();
            } catch (err) {
                console.error("Audio playback failed", err);
            }
        }
        
        // Save current case context for multi-turn
        currentState.current_case = data.current_case;
        
        const statusText = document.getElementById('statusText');
        const statusIcon = document.getElementById('statusIcon');
        statusText.textContent = data.case_status;
        
        if (data.case_status.includes("🔴")) statusIcon.textContent = "🔴";
        else if (data.case_status.includes("🟡")) statusIcon.textContent = "🟡";
        else if (data.case_status.includes("⚪")) statusIcon.textContent = "⚪";
        else statusIcon.textContent = "🟢";

        if (data.follow_up_questions && data.follow_up_questions.length > 0) {
            currentState.pending_questions = data.follow_up_questions;
            appendAiMessage(data.follow_up_questions[0]);
        } else {
            currentState.pending_questions = [];
            
            // Generate final summary message in chat
            appendAiMessage(`Triage evaluation complete. Decision: ${data.urgency}. Please see the triage note on the right.`);
            
            // Show result panel
            document.getElementById('emptyState').classList.add('hidden');
            document.getElementById('resultContent').classList.remove('hidden');
            
            document.getElementById('resUrgency').textContent = data.urgency;
            document.getElementById('resDepartment').textContent = data.recommended_department;
            document.getElementById('resRule').textContent = data.rule_id || "None";
            document.getElementById('resReason').textContent = data.decision;
            document.getElementById('resUnknowns').textContent = data.still_unknown.length ? data.still_unknown.join(", ") : "None";
            
            buildTrace(data);
        }
        
    } catch (e) {
        appendAiMessage("Sorry, an error occurred communicating with the triage engine.");
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
    }
}

function buildTrace(data) {
    const list = document.getElementById('traceList');
    list.innerHTML = "";
    
    const steps = [
        `Patient initially reported: ${data.patient_initially_reported.join(', ')}`,
        `Evidence matched: ${data.evidence_text}`,
        `Rule conditions: ${data.reason}`,
        `Final recommendation: ${data.urgency} - ${data.recommended_department}`
    ];
    
    steps.forEach(s => {
        const li = document.createElement('li');
        li.textContent = s;
        list.appendChild(li);
    });
}

function toggleTrace() {
    const box = document.getElementById('decisionTrace');
    box.classList.toggle('hidden');
}

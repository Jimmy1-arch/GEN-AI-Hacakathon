let currentState = {
    patient_statement: "",
    current_case: null,
    initial_statement: "",
    pending_questions: []
};

function loadDemo(type) {
    const textarea = document.getElementById('patientInput');
    if (type === 'normal') {
        textarea.value = "I have had a mild fever since yesterday.";
    } else if (type === 'high_risk') {
        textarea.value = "I have severe chest pain and I'm having difficulty breathing right now.";
    } else if (type === 'null_case') {
        textarea.value = "My shoulder feels strange when I sit for a long time.";
    }
}

async function startAssessment() {
    const input = document.getElementById('patientInput').value.trim();
    if (!input) return;

    currentState.patient_statement = input;
    currentState.initial_statement = input;
    currentState.current_case = null;
    
    document.getElementById('startBtn').disabled = true;
    document.getElementById('startBtn').textContent = "EVALUATING...";
    
    await sendAssessmentRequest();
}

async function submitFollowup() {
    const answer = document.getElementById('followupAnswer').value.trim();
    if (!answer) return;

    // Combine original statement with follow-up answer context
    currentState.patient_statement = `Patient answered: "${answer}" in response to: "${currentState.pending_questions[0]}"`;
    
    document.getElementById('followupPanel').classList.add('hidden');
    document.getElementById('startBtn').textContent = "RE-EVALUATING...";
    
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
        
        handleResult(data);
    } catch (e) {
        alert("An error occurred during assessment. Please try again.");
    } finally {
        document.getElementById('startBtn').disabled = false;
        document.getElementById('startBtn').textContent = "START ASSESSMENT";
    }
}

function handleResult(data) {
    // Update status
    const statusText = document.getElementById('statusText');
    const statusIcon = document.getElementById('statusIcon');
    statusText.textContent = data.case_status;
    
    if (data.case_status.includes("🔴")) {
        statusIcon.textContent = "🔴";
    } else if (data.case_status.includes("🟡")) {
        statusIcon.textContent = "🟡";
    } else if (data.case_status.includes("⚪")) {
        statusIcon.textContent = "⚪";
    } else {
        statusIcon.textContent = "🟢";
    }
    
    // Play audio if provided
    if (data.audio_base64) {
        try {
            const audio = new Audio("data:audio/mp3;base64," + data.audio_base64);
            audio.play();
        } catch (err) {
            console.error("Failed to play audio", err);
        }
    }

    if (data.follow_up_questions && data.follow_up_questions.length > 0) {
        // Show follow-up
        currentState.pending_questions = data.follow_up_questions;
        document.getElementById('followupPanel').classList.remove('hidden');
        document.getElementById('followupQuestion').textContent = currentState.pending_questions[0];
        document.getElementById('followupAnswer').value = "";
        document.getElementById('resultContent').classList.add('hidden');
    } else {
        // Show final result
        document.getElementById('resultContent').classList.remove('hidden');
        document.getElementById('resUrgency').textContent = data.urgency;
        document.getElementById('resDepartment').textContent = data.recommended_department;
        document.getElementById('resRule').textContent = data.rule_id || "None";
        document.getElementById('resReason').textContent = data.decision;
        document.getElementById('resUnknowns').textContent = data.still_unknown.length ? data.still_unknown.join(", ") : "None";
        
        // Build trace
        buildTrace(data);
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

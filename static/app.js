let currentState = {
    patient_statement: "",
    conversation_state: "NEW_CASE",
    current_case: null,
    initial_statement: "",
    pending_questions: []
};

const chatHistory = document.getElementById('chatHistory');
const chatInput = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');

let demoSequence = [];
let demoInProgress = false;

function resetIntake() {
    currentState = {
        patient_statement: "",
        conversation_state: "NEW_CASE",
        current_case: null,
        initial_statement: "",
        pending_questions: []
    };
    
    chatHistory.innerHTML = `
        <div class="message ai-message">
            <div class="avatar ai-avatar">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle><path d="M9 11v2a3 3 0 0 0 6 0v-2"></path><path d="M12 16v3"></path><circle cx="12" cy="20" r="1" fill="currentColor"></circle></svg>
            </div>
            <div class="bubble">
                Hello. Please describe your primary complaint or symptoms.
            </div>
        </div>
    `;
    
    chatInput.value = '';
    sendBtn.disabled = false;
    
    document.getElementById('emptyState').classList.remove('hidden');
    document.getElementById('resultContent').classList.add('hidden');
    
    document.getElementById('globalStage').textContent = "Waiting to begin";
    document.getElementById('statusText').textContent = "Awaiting Input";
    document.getElementById('statusIcon').className = "status-pulse gray";
    
    // Generate new case ID to make it feel realistic
    const caseIdDisplay = document.querySelector('.workspace-meta span:first-child');
    if(caseIdDisplay) {
        const randId = Math.floor(1000 + Math.random() * 9000);
        caseIdDisplay.textContent = `Case #PS01-${randId}`;
    }
}

function startDemo(type) {
    if (demoInProgress) return;
    
    resetIntake();
    
    if (type === 'fever') {
        demoSequence = [
            "I have had a mild fever since yesterday.",
            "My temperature is 100 degrees.",
            "No, I don't have any breathing difficulty."
        ];
    } else if (type === 'chest_pain') {
        demoSequence = [
            "I have chest pain.",
            "It feels like an 8 out of 10.",
            "Yes, I am having trouble breathing."
        ];
    } else if (type === 'null_case') {
        demoSequence = [
            "My shoulder feels strange when I sit for a long time."
        ];
    }
    
    demoInProgress = true;
    chatInput.value = demoSequence.shift();
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
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle><path d="M9 11v2a3 3 0 0 0 6 0v-2"></path><path d="M12 16v3"></path><circle cx="12" cy="20" r="1" fill="currentColor"></circle></svg>
        </div>
        <div class="bubble">${text}</div>
    `;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function setGenAiActivity(text) {
    const act = document.getElementById('genaiActivity');
    const txt = document.getElementById('genaiActivityText');
    if (!act || !txt) return;
    if (text) {
        act.classList.remove('hidden');
        txt.innerHTML = text;
    } else {
        act.classList.add('hidden');
    }
}

function updateWorkflow(stepId) {
    const steps = ['wf-report', 'wf-collect', 'wf-rule', 'wf-result', 'wf-human'];
    let reached = false;
    steps.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (id === stepId) {
                el.className = 'workflow-step active';
                el.querySelector('.step-icon').textContent = '●';
                reached = true;
            } else if (!reached) {
                el.className = 'workflow-step completed';
                el.querySelector('.step-icon').textContent = '✓';
            } else {
                el.className = 'workflow-step';
                el.querySelector('.step-icon').textContent = '○';
            }
        }
    });
}

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;
    
    appendUserMessage(text);
    chatInput.value = '';
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<div class="loading"></div>';
    
    if (currentState.current_case && currentState.current_case.conversation_state === "FOLLOW_UP_REQUIRED") {
        currentState.patient_statement = text;
        currentState.conversation_state = "FOLLOW_UP_REQUIRED";
        updateWorkflow('wf-collect');
        setGenAiActivity("● Identifying missing information...");
    } else if (currentState.pending_questions.length > 0) {
        currentState.patient_statement = text;
        currentState.conversation_state = "FOLLOW_UP_REQUIRED";
        updateWorkflow('wf-collect');
        setGenAiActivity("● Identifying missing information...");
    } else {
        currentState.patient_statement = text;
        currentState.initial_statement = text;
        currentState.conversation_state = "NEW_CASE";
        currentState.current_case = null;
        updateWorkflow('wf-report');
        setGenAiActivity("● Extracting complaint information...");
    }
    
    document.getElementById('globalStage').textContent = "Processing...";
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
        
        if (data.audio_base64) {
            try {
                const audio = new Audio("data:audio/mp3;base64," + data.audio_base64);
                audio.play();
            } catch (err) {
                console.error("Audio playback failed", err);
            }
        }
        
        currentState.current_case = data.current_case;
        
        const statusText = document.getElementById('statusText');
        const statusIcon = document.getElementById('statusIcon');
        
        let cleanedText = data.case_status;
        if (cleanedText.includes("🔴") || cleanedText.includes("🟡") || cleanedText.includes("⚪") || cleanedText.includes("🟢")) {
            cleanedText = cleanedText.substring(2).trim();
        }
        statusText.textContent = cleanedText;
        
        if (data.case_status.includes("🔴")) statusIcon.className = "status-pulse red";
        else if (data.case_status.includes("🟡")) statusIcon.className = "status-pulse yellow";
        else if (data.case_status.includes("⚪")) statusIcon.className = "status-pulse gray";
        else statusIcon.className = "status-pulse";

        // Show clinical summary
        document.getElementById('emptyState').classList.add('hidden');
        document.getElementById('resultContent').classList.remove('hidden');

        if (data.follow_up_questions && data.follow_up_questions.length > 0) {
            // FOLLOW UP NEEDED
            currentState.pending_questions = data.follow_up_questions;
            appendAiMessage(data.follow_up_questions[0]);
            document.getElementById('globalStage').textContent = "Follow-up required";
            setGenAiActivity("✓ Follow-up question generated");
            updateWorkflow('wf-collect');
            
            document.getElementById('ruleStatus').textContent = "WAITING FOR INFORMATION";
            document.getElementById('ruleStatus').style.color = "var(--warning)";
            document.getElementById('ruleDetails').classList.add('hidden');
            document.getElementById('triageResultSection').classList.add('hidden');
            document.getElementById('humanReviewContainer').innerHTML = "";
            
            if (demoInProgress && demoSequence.length > 0) {
                setTimeout(() => {
                    chatInput.value = demoSequence.shift();
                    sendMessage();
                }, 2000);
            } else {
                demoInProgress = false;
            }
        } else {
            // COMPLETE
            currentState.pending_questions = [];
            demoInProgress = false;
            
            if (data.case_status.includes("Human escalation") || data.case_status.includes("Outside coverage")) {
                appendAiMessage(`Thank you. I have processed your responses, but this case requires human review.`);
            } else {
                appendAiMessage(`Thank you. I have enough information to evaluate this case against the applicable triage rules.`);
            }
            
            document.getElementById('globalStage').textContent = data.human_review_required ? "Human review required" : "Triage complete";
            setGenAiActivity("✓ Information structured");
            
            if (data.human_review_required) {
                updateWorkflow('wf-human');
            } else {
                updateWorkflow('wf-result');
            }
            
            // Render Rules & Results
            document.getElementById('ruleStatus').textContent = "RULE VERIFIED";
            document.getElementById('ruleStatus').style.color = "var(--success)";
            document.getElementById('ruleDetails').classList.remove('hidden');
            document.getElementById('triageResultSection').classList.remove('hidden');
            
            document.getElementById('resUrgency').textContent = data.urgency;
            if (data.urgency === "HIGH" || data.urgency === "HUMAN ESCALATION") {
                document.getElementById('resUrgency').style.color = "var(--danger)";
            } else {
                document.getElementById('resUrgency').style.color = "var(--warning)";
            }
            document.getElementById('resDepartment').textContent = data.recommended_department;
            document.getElementById('resRule').textContent = data.rule_id || "N/A";
            
            let conditionHtml = "";
            if (data.rule_conditions && Object.keys(data.rule_conditions).length > 0) {
                conditionHtml += `<ul class="rule-condition-list">`;
                for (const [k, v] of Object.entries(data.rule_conditions)) {
                    conditionHtml += `<li>${k}: ${v}</li>`;
                }
                conditionHtml += `</ul>`;
            }
            document.getElementById('resReason').innerHTML = conditionHtml || data.reason;
            
            const hrContainer = document.getElementById('humanReviewContainer');
            if (data.human_review_required) {
                hrContainer.innerHTML = `
                    <div class="human-review-banner">
                        <div class="title">⚠ HUMAN REVIEW REQUIRED</div>
                        <p style="font-size: 0.85rem; margin-bottom: 0.75rem;">This case requires assessment by authorized healthcare staff.</p>
                        <p style="font-size: 0.85rem; font-weight: 600; margin-bottom: 1rem;">Reason: ${data.decision || "Unmet criteria"}</p>
                        <button onclick="navigate('cases', 'human_escalation')" class="ghost-btn" style="background:white; color:var(--danger); border:1px solid var(--danger); border-radius:6px; padding:8px 16px; font-weight:600; cursor:pointer; width:auto; display:inline-block;">Open Review</button>
                    </div>
                `;
            } else {
                hrContainer.innerHTML = "";
            }
        }
        
        // Common Rendering
        document.getElementById('resComplaint').textContent = currentState.initial_statement;
        document.getElementById('resCategory').textContent = data.current_case.complaints.join(", ") || "Unknown";
        
        const formatSourceBadge = (source) => {
            if (source === "INITIAL_REPORT") return `<span class="source-badge patient">PATIENT REPORTED</span>`;
            if (source === "FOLLOW_UP") return `<span class="source-badge followup">FOLLOW-UP</span>`;
            return `<span class="source-badge system">SYSTEM</span>`;
        };

        const collectedEl = document.getElementById('resCollected');
        collectedEl.innerHTML = "";
        let collectedCount = 0;
        const skipKeys = ['conversation_state', 'complaints', 'unknowns'];
        
        if (data.current_case && data.current_case.field_sources) {
            for (const [key, source] of Object.entries(data.current_case.field_sources)) {
                if (key.includes(':') || skipKeys.includes(key)) continue;
                const val = data.current_case[key];
                if (val && val !== "UNKNOWN") {
                    const li = document.createElement('li');
                    li.style.display = "flex";
                    li.style.justifyContent = "space-between";
                    li.style.alignItems = "flex-start";
                    li.style.marginBottom = "0.5rem";
                    li.style.gap = "0.5rem";
                    li.innerHTML = `<div><strong style="text-transform:capitalize;">${key}</strong>: ${val}</div> ${formatSourceBadge(source)}`;
                    collectedEl.appendChild(li);
                    collectedCount++;
                }
            }
        }
        if (collectedCount === 0) collectedEl.innerHTML = "<li><em>No information collected yet</em></li>";
        
        const resUnknowns = document.getElementById('resUnknowns');
        resUnknowns.innerHTML = "";
        if (data.still_unknown && data.still_unknown.length > 0) {
            data.still_unknown.forEach(u => {
                const li = document.createElement('li');
                li.innerHTML = `⚠ <span style="text-transform:capitalize;">${u}</span>`;
                resUnknowns.appendChild(li);
            });
        } else {
            resUnknowns.innerHTML = "<li><em>None</em></li>";
        }

        // Trace
        const traceList = document.getElementById('decisionTrace');
        traceList.innerHTML = "";
        if (data.decision_trace) {
            data.decision_trace.forEach(step => {
                const li = document.createElement('li');
                if (step.includes("REQUIRED") || step.includes("No rules matched")) {
                    li.className = "warn";
                } else {
                    li.className = "done";
                }
                li.textContent = step;
                traceList.appendChild(li);
            });
        }
        
    } catch (e) {
        console.error("Assessment request failed", e);
        document.getElementById('globalStage').textContent = "Error";
        appendAiMessage("Sorry, there was an error processing your request.");
    } finally {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>';
    }
}

async function updateBadges() {
    try {
        const res = await fetch('/api/cases');
        if (!res.ok) return;
        const data = await res.json();
        
        const highRiskCount = data.filter(c => c.urgency === 'HIGH' || c.urgency === 'URGENT').length;
        const humanEscalationCount = data.filter(c => c.human_review_required).length;
        
        document.getElementById('badge-high-risk').textContent = highRiskCount;
        document.getElementById('badge-human-escalation').textContent = humanEscalationCount;
    } catch (e) {
        console.error("Failed to fetch cases for badges", e);
    }
}

// Update badges on load
document.addEventListener("DOMContentLoaded", () => {
    updateBadges();
});

async function navigate(view, filter = 'all') {
    // Remove active class from all nav items
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    
    if (view === 'intake') {
        const navIntake = document.getElementById('nav-intake');
        if (navIntake) navIntake.classList.add('active');
        
        document.getElementById('dashboardPanel').classList.add('hidden');
        document.getElementById('intakePanel').classList.remove('hidden');
        document.getElementById('triagePanel').classList.remove('hidden');
        
        // Reset the intake to start a fresh case
        resetIntake();
    } else if (view === 'cases') {
        if (filter === 'all') document.getElementById('nav-cases').classList.add('active');
        if (filter === 'high_risk') document.getElementById('nav-high-risk').classList.add('active');
        if (filter === 'human_escalation') document.getElementById('nav-human-escalation').classList.add('active');
        
        document.getElementById('intakePanel').classList.add('hidden');
        document.getElementById('triagePanel').classList.add('hidden');
        document.getElementById('dashboardPanel').classList.remove('hidden');
        
        // Update Dashboard Header
        const dashTitle = document.getElementById('dashTitle');
        const dashDesc = document.getElementById('dashDesc');
        if (filter === 'all') {
            dashTitle.textContent = "Clinician Dashboard";
            dashDesc.textContent = "Active and pending cases";
        } else if (filter === 'high_risk') {
            dashTitle.textContent = "High Risk Queue";
            dashDesc.textContent = "Cases requiring immediate attention";
        } else if (filter === 'human_escalation') {
            dashTitle.textContent = "Human Escalation";
            dashDesc.textContent = "Cases awaiting human oversight";
        }
        
        updateBadges(); // Refresh badges whenever navigating to cases
        
        try {
            const res = await fetch('/api/cases');
            let data = await res.json();
            
            if (filter === 'high_risk') {
                data = data.filter(c => c.urgency === 'HIGH' || c.urgency === 'URGENT');
            } else if (filter === 'human_escalation') {
                data = data.filter(c => c.human_review_required);
            }
            
            const tbody = document.getElementById('casesTableBody');
            tbody.innerHTML = "";
            
            if (!data || data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:2rem; color:var(--text-muted);">No cases found for this view.</td></tr>`;
                return;
            }
            
            data.forEach(c => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = "1px solid var(--border)";
                
                const time = new Date(c.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                tr.innerHTML = `
                    <td style="padding: 10px 8px;">${time}</td>
                    <td style="padding: 10px 8px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${c.initial_complaint}">${c.initial_complaint}</td>
                    <td style="padding: 10px 8px; font-weight:600; color: ${c.urgency==='HIGH'?'var(--danger)':'inherit'};">${c.urgency || '-'}</td>
                    <td style="padding: 10px 8px;">${c.human_review_required ? '🔴 Yes' : '⚪ No'}</td>
                    <td style="padding: 10px 8px;">${c.department || '-'}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error("Failed to fetch cases", e);
        }
    }
}

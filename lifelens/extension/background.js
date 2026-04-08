const API_URL = "http://localhost:8000";

chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: "save-to-lifelens",
        title: "Save selection to LifeLens",
        contexts: ["selection"]
    });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
    const data = await chrome.storage.local.get(['token', 'activePatient', 'user']);

    if (!data.token) return; // User must log in via popup

    const user = data.user || {};
    // Determine patient ID: explicit selection > first patient > self
    let patientId = data.activePatient;
    if (!patientId && user.patients && user.patients.length > 0) {
        patientId = user.patients[0];
    }
    if (!patientId) patientId = user.username;

    if (info.menuItemId === "save-to-lifelens") {
        try {
            await fetch(`${API_URL}/api/memory/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${data.token}`
                },
                body: JSON.stringify({
                    content: info.selectionText,
                    patient_id: patientId,
                    url: tab.url,
                    title: tab.title
                })
            });
            chrome.action.setBadgeText({ text: "OK" });
            setTimeout(() => chrome.action.setBadgeText({ text: "" }), 2000);
        } catch (e) {
            console.error(e);
            chrome.action.setBadgeText({ text: "ERR" });
        }
    }
});

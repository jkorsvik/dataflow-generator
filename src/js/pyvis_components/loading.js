// src/js/pyvis_components/loading.js

// --- Function to hide loading bar ---
function hideLoadingBar() {
    const loadingBar = document.getElementById("loadingBar");
    if (loadingBar) {
        loadingBar.style.display = "none";
        console.log("Loading bar hidden"); // Modified log for clarity
    }
}

// Also hide it when it reaches 100%
function setupLoadingBarObserver() {
    const loadingBar = document.getElementById("loadingBar");
    if (!loadingBar) {
        console.warn("Loading bar element not found");
        return;
    }

    // Setup mutation observer to watch for text content or style changes
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            const textElement = loadingBar.querySelector("#text");
            const bar = loadingBar.querySelector("#bar");

            if (
                (textElement && textElement.textContent === "100%") ||
                (bar && bar.style.width === "100%")
            ) {
                hideLoadingBar();
                observer.disconnect(); // Disconnect once hidden
                console.log("Loading bar hidden by observer (100%).");
            }
        });
    });

    observer.observe(loadingBar, {
        attributes: true,
        childList: true,
        subtree: true,
        attributeFilter: ["style"], // Observe style changes for the bar width
    });

    console.log("Loading bar observer set up");

    // Initial attempt to hide if already 100%
    const textElement = loadingBar.querySelector("#text");
    const bar = loadingBar.querySelector("#bar");
    if (
        (textElement && textElement.textContent === "100%") ||
        (bar && bar.style.width === "100%")
    ) {
        hideLoadingBar();
        observer.disconnect();
        console.log("Loading bar hidden by observer (initial check).");
    }
}


// --- Loading Overlay Functions ---
function showLoadingOverlay(message = "Loading Network...") {
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) {
        const messageDiv = overlay.querySelector("div:last-child");
        if (messageDiv) messageDiv.textContent = message;
        overlay.style.display = "flex";
    }
    clearTimeout(loadingTimeout);
    loadingTimeout = setTimeout(hideLoadingOverlay, 15000); // Safety timeout
    console.log("Loading overlay shown.");
}

function hideLoadingOverlay() {
    clearTimeout(loadingTimeout);
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) {
        overlay.style.display = "none";
    }
    console.log("Loading overlay hidden.");
}
// src/js/pyvis_components/panels.js

// --- Panel Toggle ---
function togglePanel() {
    const panel = document.getElementById("controlPanel");
    const networkContainer = document.getElementById("mynetwork");

    if (!panel) {
        console.error("Control panel element not found");
        return;
    }

    isPanelExpanded = !isPanelExpanded;
    panel.classList.toggle("expanded", isPanelExpanded); // Use second arg for toggle

    if (networkContainer) {
        networkContainer.style.right = isPanelExpanded ? panelWidth + "px" : "0px";
    }
    // Icon state is managed by CSS based on .expanded class of the panel
}

// --- Search Panel Toggle ---
function toggleSearchPanel() {
    searchPanel = searchPanel || document.getElementById("searchPanel"); // Initialize if null
    if (!searchPanel) {
        console.error("Search panel element not found.");
        return;
    }

    isSearchPanelOpen = !isSearchPanelOpen;
    searchPanel.classList.toggle("expanded", isSearchPanelOpen);

    if (isSearchPanelOpen) {
        searchInput = searchInput || document.getElementById("searchInput"); // Initialize if null
        if (searchInput) {
            searchInput.focus();
            initializeSearch(); // Ensure search is ready
        }
    } else {
        clearSearch(); // Clear search when closing
    }
}

function closeSearchPanel() {
    searchPanel = searchPanel || document.getElementById("searchPanel"); // Initialize if null
    if (!searchPanel || !isSearchPanelOpen) return;

    searchPanel.classList.remove("expanded");
    isSearchPanelOpen = false;
    clearSearch(); // Clear highlights and results when closing
}
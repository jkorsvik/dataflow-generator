// src/js/pyvis_components/keyboard.js

// --- Setup global keyboard shortcuts ---
function setupKeyboardShortcuts() {
    document.addEventListener("keydown", function (e) {
        // Check if we should ignore the event (e.g., typing in input fields)
        if (shouldIgnoreKeyboardEvent(e)) return;

        // Ctrl+F or Cmd+F for search panel
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
            e.preventDefault(); // Prevent browser's default find action
            toggleSearchPanel();
        }

        // Escape key to close search panel (if it's open)
        if (e.key === "Escape") {
            if (isSearchPanelOpen) {
                e.preventDefault(); // Prevent other escape actions if search panel is main target
                closeSearchPanel();
            } else if (persistentTooltip) { // Also allow Esc to close persistent tooltip
                e.preventDefault();
                hidePersistentTooltip();
            } else if (document.getElementById("addNodeModal")?.style.display === 'block') {
                e.preventDefault();
                document.getElementById("addNodeModal").style.display = 'none';
            } else if (selectionOverlay?.style.display === 'block') {
                e.preventDefault();
                cancelSelectionMode();
            }
        }


        // Navigation in search results when search panel is open and has results
        if (isSearchPanelOpen && currentSearchResults.length > 0) {
            if (e.key === "Enter") {
                // This is handled by the searchInput's keyup listener to avoid double-triggering.
                // If searchInput is not focused, this provides an alternative.
                // However, the primary listener is on the input itself.
                if (document.activeElement !== searchInput) {
                    e.preventDefault();
                    if (e.shiftKey) {
                        navigateSearchResult(-1); // Previous
                    } else {
                        navigateSearchResult(1); // Next
                    }
                }
            }
        }
    });
    console.log("Global keyboard shortcuts set up.");
}

function shouldIgnoreKeyboardEvent(e) {
    const target = e.target;
    const tagName = target.tagName.toLowerCase();

    // Ignore keyboard events when typing in standard input elements
    if (tagName === "input" || tagName === "textarea" || tagName === "select") {
        // Allow Escape key for inputs unless it's specifically for search panel input
        if (e.key === "Escape" && target.id === "searchInput" && isSearchPanelOpen) {
            return false; // Allow search input to handle its own Escape
        }
        return true;
    }

    // Ignore events with contentEditable elements
    if (target.isContentEditable) {
        return true;
    }

    return false;
}
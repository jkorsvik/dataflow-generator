// src/js/pyvis_components/init.js

// This script should be the last one to be included/run.

// --- Main Event Listener Setup ---
function setupEventListeners() {
    console.log("Setting up event listeners for UI controls...");

    // Slider value displays
    document.querySelectorAll('.control-panel input[type="range"]').forEach(input => {
        // Initialize display first
        updateValueDisplay(input.id, input.value);
        // Then set oninput listener
        input.oninput = () => updateValueDisplay(input.id, input.value);
    });

    // Search options checkboxes (if they exist)
    const searchOptionCheckboxes = document.querySelectorAll('.search-option input[type="checkbox"]');
    searchOptionCheckboxes.forEach(checkbox => {
        checkbox.addEventListener("change", function () {
            if (currentSearchQuery && currentSearchResults.length > 0) {
                performSearch(currentSearchQuery); // Re-run search with new options
            } else if (currentSearchQuery) {
                // If there's a query but no results, re-running might find some with new options (e.g. case sensitivity)
                performSearch(currentSearchQuery);
            }
        });
    });

    // Global keyboard shortcuts
    setupKeyboardShortcuts(); // Defined in keyboard.js

    // Buttons in control panel (Apply, Reset) - Assuming they exist with these IDs
    const applyBtn = document.getElementById("applySettingsBtn"); // Assuming an ID for apply
    if (applyBtn) applyBtn.onclick = applyUISettings;

    const resetBtn = document.getElementById("resetSettingsBtn"); // Assuming an ID for reset
    if (resetBtn) resetBtn.onclick = resetToInitialOptions;


    // Export buttons (if they exist)
    const pngFullBtn = document.getElementById("exportPNGFullBtn");
    if (pngFullBtn) pngFullBtn.onclick = () => saveFullNetworkPNG(); // Default scale

    const svgFullBtn = document.getElementById("exportSVGFullBtn");
    if (svgFullBtn) svgFullBtn.onclick = saveFullNetworkSVG;

    const exportSelectionBtn = document.getElementById("exportSelectionBtn"); // Button to start selection
    if (exportSelectionBtn) exportSelectionBtn.onclick = startSelectionMode;


    // Export choice modal buttons (if they exist)
    const exportSelPNG = document.getElementById("exportSelectionPNG");
    if (exportSelPNG) exportSelPNG.onclick = () => exportSelection('png');

    const exportSelSVG = document.getElementById("exportSelectionSVG");
    if (exportSelSVG) exportSelSVG.onclick = () => exportSelection('svg');

    const cancelSelExport = document.getElementById("cancelSelectionExport");
    if (cancelSelExport) cancelSelExport.onclick = cancelSelectionMode;


    // Control panel toggle button
    const panelToggle = document.getElementById("panelToggleButton");
    if (panelToggle) panelToggle.onclick = togglePanel;

    // Search panel toggle button
    const searchToggle = document.getElementById("searchToggleButton");
    if (searchToggle) searchToggle.onclick = toggleSearchPanel;

    // Search navigation buttons
    if (prevSearchResultBtn) prevSearchResultBtn.onclick = () => navigateSearchResult(-1);
    if (nextSearchResultBtn) nextSearchResultBtn.onclick = () => navigateSearchResult(1);


    console.log("All general event listeners set up.");
}


// --- Network Ready & Initialization ---
function onNetworkReady() {
    if (networkReady && listenersAttached) {
        console.log("Network ready called but listeners already attached.");
        return;
    }

    if (window.network && typeof window.network.on === "function") {
        networkReady = true; // Mark network as ready
        console.log("Network object found and ready.");

        // Attempt to hide loading bar and overlay as early as possible
        hideLoadingBar(); // From loading.js
        // Initial overlay hide, stabilization might show it again if lengthy
        setTimeout(hideLoadingOverlay, 200); // From loading.js

        if (!listenersAttached) {
            // Assign global DOM elements from core.js if not already assigned by other modules
            selectionOverlay = selectionOverlay || document.getElementById("selectionOverlay");
            selectionRectangle = selectionRectangle || document.getElementById("selectionRectangle");
            exportChoiceModal = exportChoiceModal || document.getElementById("exportChoiceModal");
            searchPanel = searchPanel || document.getElementById("searchPanel");
            searchInput = searchInput || document.getElementById("searchInput");
            searchResultCount = searchResultCount || document.getElementById("searchResultCount");
            searchStatus = searchStatus || document.getElementById("searchStatus");
            prevSearchResultBtn = prevSearchResultBtn || document.getElementById("prevSearchResult");
            nextSearchResultBtn = nextSearchResultBtn || document.getElementById("nextSearchResult");

            setupEventListeners(); // Setup all UI event listeners
            patchVisTooltip(); // Setup custom tooltips (from tooltips.js)
            if (typeof initHoverTooltips === 'function') {
                initHoverTooltips(network);
            }
            listenersAttached = true;
            console.log("All event listeners and patches applied after network ready.");
        }

        // Network event handlers
        window.network.on("stabilizationIterationsDone", () => {
            console.log("Network stabilization finished.");
            hideLoadingOverlay(); // Hide overlay after stabilization
            hideLoadingBar();     // Ensure loading bar is also hidden
            // Optionally fit network to view after stabilization
            // window.network.fit();
        });

        window.network.on("stabilizationProgress", (params) => {
            // console.log(`Stabilization progress: ${params.iterations}/${params.total} iterations.`);
            // Optionally update a more detailed loading message or progress bar here
        });

        window.network.on("startStabilizing", () => {
            console.log("Network stabilization started...");
        });

        // If physics is disabled, stabilization events might not fire, ensure overlay is hidden.
        // Check current physics state.
        if (window.network.options && window.network.options.physics && !window.network.options.physics.enabled) {
            console.log("Physics is disabled, ensuring loading overlay is hidden.");
            setTimeout(hideLoadingOverlay, 500); // Give a bit of time for initial render
        }

        // Initialize search engine once network is confirmed ready
        initializeSearchEngine(); // from search.js

    } else {
        console.warn("onNetworkReady called, but network object is not (yet) valid.");
    }
}

// --- DOMContentLoaded Listener ---
document.addEventListener("DOMContentLoaded", () => {
    console.log("DOM Content Loaded. Initializing Pyvis enhancements.");

    // Ensure the network container has a default right style if panel is not expanded.
    const networkContainer = document.getElementById("mynetwork");
    if (networkContainer) {
        networkContainer.style.right = isPanelExpanded ? panelWidth + "px" : "0px";
    }

    // Create loading overlay if it doesn't exist (e.g. if HTML is minimal)
    if (!document.getElementById("loadingOverlay")) {
        const overlay = document.createElement("div");
        overlay.id = "loadingOverlay";
        overlay.innerHTML = '<div class="spinner"></div><div style="margin-top: 10px;">Loading Network...</div>';
        // Basic styling, should be enhanced with CSS classes from pyvis_mod.py
        overlay.style.cssText = "position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(220, 220, 220, 0.7); z-index: 10002; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 1.2em; color: #333; text-align: center; transition: opacity 0.3s;";
        document.body.appendChild(overlay);
    }
    // Show loading overlay initially, it will be hidden by network events or timeouts.
    showLoadingOverlay(); // from loading.js

    // Setup observer for the vis.js loading bar as early as possible
    setupLoadingBarObserver(); // from loading.js
    hideLoadingBar(); // Attempt to hide it if it's already 100% or not needed.

    // Check for network object periodically.
    // Vis.js might take a moment to initialize `window.network`.
    let checkNetworkIntervalCounter = 0;
    const maxChecks = 150; // Max 15 seconds (150 * 100ms)

    const checkNetworkInterval = setInterval(() => {
        checkNetworkIntervalCounter++;
        if (window.network && typeof window.network.on === "function") {
            clearInterval(checkNetworkInterval);
            onNetworkReady();
        } else if (checkNetworkIntervalCounter > maxChecks) {
            clearInterval(checkNetworkInterval);
            console.warn("Network object (window.network) failed to initialize within the timeout period (15s). UI features depending on it may not work.");
            hideLoadingOverlay(); // Hide loading overlay if network fails to init
            hideLoadingBar();
            // display a more permanent error message on the UI?
            const errorMsg = document.createElement("div");
            errorMsg.innerHTML = "Error: Network graph failed to load. Please refresh or check console.";
            errorMsg.style.cssText = "position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); color:red; background:white; padding:20px; border:1px solid red; z-index:10003;";
            document.body.appendChild(errorMsg);

        }
    }, 100); // Check every 100ms
});

// --- Window Load Listener ---
window.addEventListener("load", () => {
    console.log("Window Load event fired. Final checks for Pyvis setup.");
    // This is a fallback in case network object was ready before DOMContentLoaded fully processed our script.
    if (!networkReady && window.network && typeof window.network.on === "function") {
        console.log("Network object found on window.load, running onNetworkReady.");
        onNetworkReady();
    } else if (networkReady) {
        console.log("Network already processed, window.load is just a confirmation.");
    } else {
        console.warn("Window load event: Network still not ready.");
    }

    // Ensure loading bar and overlay are hidden after everything is loaded.
    // Use a timeout to ensure this runs after any final rendering/stabilization starts.
    setTimeout(() => {
        hideLoadingBar();
        if (networkReady && !(window.network.options && window.network.options.physics && window.network.options.physics.enabled && window.network.isStabilizing())) {
            // Only hide overlay if network is ready AND not currently stabilizing with physics enabled
            hideLoadingOverlay();
        } else if (!networkReady) {
            // If network never got ready, hide the overlay too
            hideLoadingOverlay();
        }
    }, 1000); // Delay of 1s

    // Dynamically load Fuse.js if not already loaded (e.g., by search.js)
    // This is a fallback. search.js should ideally handle its own dependency.
    if (typeof Fuse === "undefined") {
        console.log("Fuse.js not detected on window.load, attempting to load it for search functionality.");
        const fuseScript = document.createElement("script");
        fuseScript.src = "https://cdn.jsdelivr.net/npm/fuse.js@7.1.0"; // Consider a more recent version or local copy
        fuseScript.onload = () => {
            console.log("Fuse.js library loaded successfully via window.load fallback.");
            // If search was attempted before Fuse loaded, it might need re-initialization or a search re-trigger.
            if (isSearchPanelOpen && searchInput && searchInput.value) {
                console.log("Re-initializing search after late Fuse.js load.");
                initializeSearchEngine(); // from search.js
                performSearch(searchInput.value.trim());
            } else if (isSearchPanelOpen) {
                initializeSearchEngine();
            }
        };
        fuseScript.onerror = (err) => {
            console.error("Failed to load Fuse.js via window.load fallback:", err);
            if (searchStatus) searchStatus.textContent = "Search library failed to load.";
        };
        document.head.appendChild(fuseScript);
    }
});

// --- Window Resize Handler ---
let resizeTimeout;
window.addEventListener("resize", () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        console.log("Window resized. Adjusting network view.");
        const networkContainer = document.getElementById("mynetwork");
        if (networkContainer) {
            // Adjust right margin based on control panel state
            networkContainer.style.right = isPanelExpanded ? panelWidth + "px" : "0px";
        }
        if (window.network) {
            // Vis.js's 'fit' can be used, or just let it be.
            // Calling redraw might be useful if custom elements depend on viewport size.
            // window.network.redraw();
            // window.network.fit({ animation: false }); // Fit without animation can be jarring.
            // Usually, vis.js handles resizing of its canvas automatically.
            // This is more about adjusting elements *around* the network.
        }
    }, 250); // Debounce resize events
});

// Set up a recurring timer to hide the loading bar if it somehow reappears or gets stuck
// This is a more aggressive fallback.
// setInterval(hideLoadingBar, 10000); // Every 10 seconds (from loading.js)
// This was in the original script, might be too aggressive or unnecessary if observer works well.
// Consider if it's truly needed. For now, relying on observer and specific hide calls.

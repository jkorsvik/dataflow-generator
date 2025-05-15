// src/js/pyvis_components/settings.js

// --- Helper to get value from UI element ---
function getElementValue(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return undefined;

    if (el.type === "checkbox") return el.checked;
    if (el.type === "range" || el.type === "number") {
        // Ensure numerical values are parsed correctly
        const val = parseFloat(el.value);
        return isNaN(val) ? el.value : val; // Return original string if not a number (e.g. for empty number input)
    }
    return el.value;
}

// --- Nested Property Helper ---
function setNestedProperty(obj, path, value) {
    const keys = path.split(".");
    let current = obj;
    for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        current[key] = current[key] || {}; // Create nested object if it doesn't exist
        current = current[key];
    }
    current[keys[keys.length - 1]] = value;
}

// --- Helper to update value display for sliders ---
function updateValueDisplay(rangeInputId, value) {
    const displayElement = document.getElementById(rangeInputId + "_value");
    if (displayElement) {
        // Attempt to parse as float and format, otherwise display original value
        const numValue = parseFloat(value);
        if (!isNaN(numValue) && Number.isFinite(numValue)) {
            displayElement.textContent = numValue.toFixed(2);
        } else {
            displayElement.textContent = value;
        }
    }
}

// --- Apply Settings Button Logic ---
function applyUISettings() {
    if (!window.network || typeof window.network.setOptions !== "function") {
        console.error("Network not ready or setOptions not available.");
        showLoadingOverlay("Error: Network not available.");
        setTimeout(hideLoadingOverlay, 2000);
        return;
    }
    console.log("Applying UI settings...");
    showLoadingOverlay("Applying settings...");

    const newOptions = {}; // Intentionally using a different name from global `initialNetworkOptions`
    const controlElements = document.querySelectorAll(
        ".control-panel [id^='physics.'], .control-panel [id^='layout.'], .control-panel [id^='edges.'], .control-panel [id^='nodes.'], .control-panel [id^='interaction.']"
    ); // More specific selectors

    controlElements.forEach((el) => {
        if (el.id && (el.tagName === "INPUT" || el.tagName === "SELECT")) {
            const optionPath = el.id;
            const value = getElementValue(el.id);
            if (value !== undefined) {
                // Handle specific cases like 'physics.enabled' which might be a string "true"/"false" from select
                if (typeof value === 'string' && (value.toLowerCase() === 'true' || value.toLowerCase() === 'false')) {
                    setNestedProperty(newOptions, optionPath, value.toLowerCase() === 'true');
                } else {
                    setNestedProperty(newOptions, optionPath, value);
                }
            }
        }
    });

    console.log("Applying options:", JSON.stringify(newOptions, null, 2));

    try {
        // Use a short timeout to allow the loading overlay to render
        setTimeout(() => {
            window.network.setOptions(newOptions);
            // Check if physics or hierarchical layout is being enabled, as they require stabilization
            const physicsEnabled = newOptions.physics?.hasOwnProperty('enabled') ? newOptions.physics.enabled : window.network.options.physics.enabled;
            const hierarchicalEnabled = newOptions.layout?.hierarchical?.hasOwnProperty('enabled') ? newOptions.layout.hierarchical.enabled : window.network.options.layout.hierarchical.enabled;

            if (physicsEnabled || hierarchicalEnabled) {
                console.log("Stabilizing network after applying changes...");
                window.network.stabilize(); // stabilizationIterationsDone event will hide overlay
            } else {
                console.log("Redrawing network (no stabilization needed)...");
                window.network.redraw();
                hideLoadingOverlay(); // Hide manually if not stabilizing
            }
        }, 50);
    } catch (error) {
        console.error("Error applying settings:", error, "Attempted options:", newOptions);
        showLoadingOverlay("Error applying settings.");
        setTimeout(hideLoadingOverlay, 2000);
    }
}

// --- Reset Function ---
function resetToInitialOptions() {
    if (!window.network || typeof window.network.setOptions !== "function") {
        console.error("Network not ready for reset.");
        showLoadingOverlay("Error: Network not available.");
        setTimeout(hideLoadingOverlay, 2000);
        return;
    }
    console.log("Resetting to initial options...");
    showLoadingOverlay("Resetting to defaults...");

    // Reset UI elements to match initialNetworkOptions
    const controlElements = document.querySelectorAll(
        ".control-panel [id^='physics.'], .control-panel [id^='layout.'], .control-panel [id^='edges.'], .control-panel [id^='nodes.'], .control-panel [id^='interaction.']"
    );

    // Parse initialNetworkOptions if it's still a string
    let parsedInitialOptions = initialNetworkOptions;
    if (typeof initialNetworkOptions === 'string') {
        try {
            parsedInitialOptions = JSON.parse(initialNetworkOptions);
        } catch (e) {
            console.error("Failed to parse initialNetworkOptions string:", e);
            hideLoadingOverlay();
            return;
        }
    }


    controlElements.forEach((el) => {
        if (el.id && (el.tagName === "INPUT" || el.tagName === "SELECT")) {
            const optionPath = el.id;
            let valueFromInitial = parsedInitialOptions;
            try {
                optionPath.split(".").forEach((k) => {
                    if (valueFromInitial && typeof valueFromInitial === 'object' && k in valueFromInitial) {
                        valueFromInitial = valueFromInitial[k];
                    } else {
                        throw new Error("Path not found");
                    }
                });
            } catch (e) {
                // console.warn(`Path ${optionPath} not found in initial options. Skipping reset for this element.`);
                valueFromInitial = undefined; // Path does not exist in initial options
            }

            if (valueFromInitial !== undefined) {
                if (el.type === "checkbox") {
                    el.checked = valueFromInitial;
                } else if (el.type === "range") {
                    el.value = valueFromInitial;
                    updateValueDisplay(el.id, valueFromInitial); // Update the associated display
                } else if (el.tagName === "SELECT") {
                    // For select, ensure the value is a string for comparison
                    el.value = String(valueFromInitial);
                }
                else {
                    el.value = valueFromInitial;
                }
            } else {
                // If no initial value, maybe reset to a common default or leave as is
                if (el.type === "checkbox") el.checked = false;
                // else if (el.type !== "range") el.value = ""; // Don't reset range if no specific initial value
            }
        }
    });

    // Apply initial options to the network
    setTimeout(() => {
        try {
            window.network.setOptions(parsedInitialOptions);
            console.log("Stabilizing network after reset...");
            // Check if physics or hierarchical layout is enabled in initial options
            const physicsEnabled = parsedInitialOptions.physics?.enabled;
            const hierarchicalEnabled = parsedInitialOptions.layout?.hierarchical?.enabled;

            if (physicsEnabled || hierarchicalEnabled) {
                window.network.stabilize(); // stabilizationIterationsDone event will hide overlay
            } else {
                window.network.redraw();
                hideLoadingOverlay();
            }
        } catch (error) {
            console.error("Error resetting options:", error);
            showLoadingOverlay("Error resetting options.");
            setTimeout(hideLoadingOverlay, 2000);
        }
    }, 50);
}
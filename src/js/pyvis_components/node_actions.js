// src/js/pyvis_components/node_actions.js

document.addEventListener("DOMContentLoaded", function () {
    const fab = document.getElementById("addNodeFab");
    const modal = document.getElementById("addNodeModal");
    const errorDiv = document.getElementById("addNodeError");
    const idInput = document.getElementById("addNodeId");
    const labelInput = document.getElementById("addNodeLabel"); // Assuming you might add a label input
    const typeInput = document.getElementById("addNodeType");
    const dbInput = document.getElementById("addNodeDatabase");
    const addBtn = document.getElementById("addNodeModalAddBtn");
    const cancelBtn = document.getElementById("addNodeModalCancelBtn");

    if (!fab || !modal || !errorDiv || !idInput || !typeInput || !dbInput || !addBtn || !cancelBtn) {
        console.warn("One or more 'Add Node' modal elements are missing. FAB functionality will be limited.");
        if (fab) fab.style.display = "none"; // Hide FAB if modal isn't functional
        return;
    }

    fab.onclick = function () {
        errorDiv.textContent = ""; // Clear previous errors
        idInput.value = "";
        if (labelInput) labelInput.value = ""; // Clear label if exists
        typeInput.value = typeInput.querySelector('option[selected]')?.value || typeInput.options[0]?.value || "table"; // Reset to default or first option
        dbInput.value = "";
        modal.style.display = "block";
        idInput.focus(); // Focus the first input field
    };

    cancelBtn.onclick = function () {
        modal.style.display = "none";
    };

    // Close modal if clicking outside of it
    modal.addEventListener('click', function (event) {
        if (event.target === modal) { // Check if the click is on the modal background itself
            modal.style.display = "none";
        }
    });


    addBtn.onclick = function () {
        const nodeId = idInput.value.trim();
        const nodeLabel = labelInput ? labelInput.value.trim() : nodeId; // Use label if provided, else ID
        const nodeType = typeInput.value;
        const nodeDb = dbInput.value.trim();

        // Validation
        if (!nodeId) {
            errorDiv.textContent = "Node ID is required.";
            idInput.focus();
            return;
        }

        // Check if node ID already exists in the network
        if (window.network && window.network.body && window.network.body.data && window.network.body.data.nodes) {
            if (window.network.body.data.nodes.get(nodeId)) {
                errorDiv.textContent = `Node ID "${nodeId}" already exists.`;
                idInput.focus();
                return;
            }
        } else {
            console.warn("Network data not available to check for existing node ID. Proceeding with caution.");
        }

        // If all checks pass
        errorDiv.textContent = ""; // Clear error message

        const newNodeData = {
            id: nodeId, // Vis.js uses 'id'
            label: nodeLabel || nodeId, // Vis.js uses 'label'
            // Custom properties for pyvis - these might be used to generate the 'title' or other node attributes
            pyvis_type: nodeType, // Store original type if needed
            pyvis_database: nodeDb,
            // Standard vis.js properties that might be derived from type/db or set by default
            shape: 'dot', // Example default shape
            group: nodeType, // Example: use type as group for styling
            title: `<b>${nodeLabel || nodeId}</b><br>Type: ${nodeType}<br>Database: ${nodeDb || '(default)'}<br>Connections: 0` // Basic title
        };

        // Output to console for external processing (e.g., Python backend to actually add it)
        // The Python side would then decide how to reconstruct the full node object for vis.js
        console.log('[NODE_CREATE]', JSON.stringify({
            nodeId: newNodeData.id,
            label: newNodeData.label,
            type: newNodeData.pyvis_type,
            database: newNodeData.pyvis_database
            // any other raw attributes needed by Python
        }));


        // Optional: If you want to add the node directly to the client-side graph for immediate feedback
        // (This would be a temporary addition unless the backend also confirms and adds it)
        // if (window.network && window.network.body.data.nodes) {
        //   try {
        //     window.network.body.data.nodes.add(newNodeData);
        //     console.log("Node added to client-side graph (temporary).");
        //   } catch (e) {
        //     console.error("Error adding node to client-side graph:", e);
        //     errorDiv.textContent = "Error adding node locally: " + e.message;
        //     return; // Don't close modal if local add failed
        //   }
        // }

        modal.style.display = "none"; // Close modal on successful data emission
    };

    // Allow Enter key to submit from text input fields within the modal
    const inputs = [idInput, labelInput, dbInput].filter(Boolean); // Filter out null if labelInput isn't there
    inputs.forEach(input => {
        input.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Prevent default form submission if it were in a form
                addBtn.click();
            }
        });
    });

    // Allow Escape key to close the modal
    // This is now also handled by the global keyboard shortcut in keyboard.js
    // modal.addEventListener('keydown', function(event) {
    //   if (event.key === 'Escape') {
    //     modal.style.display = 'none';
    //   }
    // });
    console.log("Add Node FAB and modal listeners set up.");
});
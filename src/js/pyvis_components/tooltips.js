// src/js/pyvis_components/tooltips.js

function makeDraggable(el) {
    let isDragging = false,
        offsetX = 0,
        offsetY = 0;
    const header = el.querySelector(".custom-persistent-tooltip-header");

    if (!header) {
        console.warn("Draggable element is missing a header.");
        return; // Cannot make it draggable without a header
    }
    header.style.cursor = "move";

    function onMouseDown(e) {
        // Only drag with left mouse button, and not on buttons/inputs inside header
        if (e.button !== 0 || e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;

        e.preventDefault(); // Prevent text selection during drag
        e.stopPropagation(); // Prevent triggering network events if tooltip is over canvas

        isDragging = true;
        // Calculate offset from the element's current top-left corner to mouse position
        offsetX = e.clientX - el.getBoundingClientRect().left;
        offsetY = e.clientY - el.getBoundingClientRect().top;

        // Add listeners to document/window to catch mouse movements anywhere on the page
        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp);
    }

    function onMouseMove(e) {
        if (!isDragging) return;
        e.preventDefault(); // Important during active drag

        // New position is mouse position minus the initial offset
        let newLeft = e.clientX - offsetX;
        let newTop = e.clientY - offsetY;

        // Boundary checks (optional, to keep tooltip within viewport)
        const elRect = el.getBoundingClientRect();
        if (newLeft < 0) newLeft = 0;
        if (newTop < 0) newTop = 0;
        if (newLeft + elRect.width > window.innerWidth) newLeft = window.innerWidth - elRect.width;
        if (newTop + elRect.height > window.innerHeight) newTop = window.innerHeight - elRect.height;


        el.style.left = `${newLeft}px`;
        el.style.top = `${newTop}px`;
    }

    function onMouseUp(e) {
        if (!isDragging) return;
        e.preventDefault();
        isDragging = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
    }

    header.addEventListener("mousedown", onMouseDown);
}


function showPersistentTooltip(nodeId, htmlContent, event) {
    hidePersistentTooltip(); // Remove any existing tooltip

    if (!window.network || !window.network.body || !window.network.body.data.nodes) {
        console.error("Network not ready for persistent tooltip.");
        return;
    }
    const node = window.network.body.data.nodes.get(nodeId);
    if (!node) {
        console.warn(`Node ${nodeId} not found for persistent tooltip.`);
        return;
    }

    persistentTooltip = document.createElement("div");
    persistentTooltip.className = "custom-persistent-tooltip";
    persistentTooltip.setAttribute("data-node-id", nodeId);


    const allNodes = window.network.body.data.nodes.get({ returnType: 'Array' });
    const allNodeIds = allNodes.map(n => n.id);
    const edges = window.network.body.data.edges.get({ returnType: 'Array' });

    // Filter edges more carefully: an edge object might have 'from' and 'to' as objects in some vis.js versions/setups
    const parentIds = edges.filter(e => String(e.to) === String(nodeId)).map(e => String(e.from));
    const childIds = edges.filter(e => String(e.from) === String(nodeId)).map(e => String(e.to));

    // Reset edit state for this node
    nodeEditState = {
        nodeId: String(nodeId),
        addParents: [],
        addChildren: [],
        removeParents: [],
        removeChildren: [],
        deleted: false,
    };

    // Create a datalist of all other nodes for easier selection
    const otherNodeOptions = allNodeIds
        .filter(id => String(id) !== String(nodeId))
        .map(id => `<option value="${id}"></option>`)
        .join('');

    let editHtml = `
      <div class="custom-tooltip-section" style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;">
        <h4>Edit Node Connections</h4>
        <div class="tooltip-edit-group">
          <label for="addParentInput-${nodeId}">Add Parent:</label>
          <input type="text" id="addParentInput-${nodeId}" placeholder="Node ID..." list="allNodeList-${nodeId}" class="tooltip-edit-input">
          <button class="tooltip-edit-button" data-action="add-parent">Add</button>
        </div>
        <div class="tooltip-edit-group">
          <label for="addChildInput-${nodeId}">Add Child:</label>
          <input type="text" id="addChildInput-${nodeId}" placeholder="Node ID..." list="allNodeList-${nodeId}" class="tooltip-edit-input">
          <button class="tooltip-edit-button" data-action="add-child">Add</button>
        </div>
        <datalist id="allNodeList-${nodeId}">${otherNodeOptions}</datalist>
  
        <div class="tooltip-edit-group">
          <strong>Current Parents:</strong> <span id="parentList-${nodeId}"></span>
        </div>
        <div class="tooltip-edit-group">
          <strong>Current Children:</strong> <span id="childList-${nodeId}"></span>
        </div>
        <div class="tooltip-edit-group" style="margin-top:15px;">
          <button class="tooltip-edit-button tooltip-delete-button" data-action="delete-node">Delete This Node</button>
        </div>
        <div id="editWarning-${nodeId}" class="tooltip-edit-warning" style="display:none;"></div>
        <div style="margin-top:15px; text-align: right;">
          <button id="commitNodeEditBtn-${nodeId}" class="tooltip-edit-button tooltip-commit-button" style="display:none;">Commit Changes</button>
        </div>
      </div>
    `;

    // Ensure node.label or nodeId is used for the title
    const tooltipTitle = node.label || nodeId;

    persistentTooltip.innerHTML =
        `<div class="custom-persistent-tooltip-header">
         <h3>${tooltipTitle}</h3>
         <button class="custom-persistent-tooltip-close" title="Close (Esc)">×</button>
       </div>
       <div class="custom-persistent-tooltip-content">
         <div class="custom-tooltip-section">${htmlContent}</div>
         ${editHtml}
       </div>`;

    document.body.appendChild(persistentTooltip);
    persistentTooltipNodeId = String(nodeId); // Store the current node ID

    // Add event listeners for edit controls AFTER innerHTML is set
    persistentTooltip.querySelector('.custom-persistent-tooltip-close').addEventListener('click', hidePersistentTooltip);
    persistentTooltip.querySelector('button[data-action="add-parent"]').addEventListener('click', handleNodeEditAction);
    persistentTooltip.querySelector('button[data-action="add-child"]').addEventListener('click', handleNodeEditAction);
    persistentTooltip.querySelector('button[data-action="delete-node"]').addEventListener('click', handleNodeEditAction);
    persistentTooltip.querySelector(`#commitNodeEditBtn-${nodeId}`).addEventListener('click', handleNodeEditAction);


    // Position tooltip
    let x = event.clientX + 15;
    let y = event.clientY + 15;
    // Call makeDraggable AFTER the element is in the DOM and sized
    // But set initial position first
    persistentTooltip.style.left = x + "px";
    persistentTooltip.style.top = y + "px";
    makeDraggable(persistentTooltip); // Make it draggable by its header

    // Adjust position to ensure it's within viewport AFTER it's rendered and has dimensions
    // Use a microtask to allow rendering
    Promise.resolve().then(() => {
        const ttRect = persistentTooltip.getBoundingClientRect();
        if (x + ttRect.width > window.innerWidth) {
            x = Math.max(0, window.innerWidth - ttRect.width - 10);
        }
        if (y + ttRect.height > window.innerHeight) {
            y = Math.max(0, window.innerHeight - ttRect.height - 10);
        }
        persistentTooltip.style.left = x + "px";
        persistentTooltip.style.top = y + "px";
    });


    if (window.Prism) { // If Prism.js is loaded, highlight content
        Prism.highlightAllUnder(persistentTooltip.querySelector('.custom-persistent-tooltip-content'));
    }
    updateEditUI(); // Populate initial parent/child lists and button states
}

function handleNodeEditAction(event) {
    if (!nodeEditState.nodeId) return;
    const action = event.target.dataset.action;
    const nodeId = nodeEditState.nodeId; // The node being edited

    switch (action) {
        case 'add-parent': {
            const input = document.getElementById(`addParentInput-${nodeId}`);
            const val = input.value.trim();
            if (val && String(val) !== nodeId && !nodeEditState.addParents.includes(val) && !getCurrentParentIds(nodeId).includes(val)) {
                if (window.network.body.data.nodes.get(val)) { // Check if node exists
                    nodeEditState.addParents.push(val);
                    input.value = ''; // Clear input
                } else {
                    alert(`Node "${val}" not found.`);
                }
            }
            break;
        }
        case 'add-child': {
            const input = document.getElementById(`addChildInput-${nodeId}`);
            const val = input.value.trim();
            if (val && String(val) !== nodeId && !nodeEditState.addChildren.includes(val) && !getCurrentChildIds(nodeId).includes(val)) {
                if (window.network.body.data.nodes.get(val)) { // Check if node exists
                    nodeEditState.addChildren.push(val);
                    input.value = ''; // Clear input
                } else {
                    alert(`Node "${val}" not found.`);
                }
            }
            break;
        }
        case 'remove-parent': {
            const parentId = event.target.dataset.id;
            const currentParents = getCurrentParentIds(nodeId);
            if (parentId) {
                // Removing a specific parent
                if (!nodeEditState.removeParents.includes(parentId)) {
                    nodeEditState.removeParents.push(parentId);
                }
            } else {
                // Add all current parents to removal list
                currentParents.forEach(pid => {
                    if (!nodeEditState.removeParents.includes(pid)) {
                        nodeEditState.removeParents.push(pid);
                    }
                });
            }
            break;
        }
        case 'remove-child': {
            const childId = event.target.dataset.id;
            const currentChildren = getCurrentChildIds(nodeId);
            if (childId) {
                // Removing a specific child
                if (!nodeEditState.removeChildren.includes(childId)) {
                    nodeEditState.removeChildren.push(childId);
                }
            } else {
                // Add all current children to removal list
                currentChildren.forEach(cid => {
                    if (!nodeEditState.removeChildren.includes(cid)) {
                        nodeEditState.removeChildren.push(cid);
                    }
                });
            }
            break;
        }
        case 'delete-node':
            const warnDiv = document.getElementById(`editWarning-${nodeId}`);
            const currentParents = getCurrentParentIds(nodeId);
            const currentChildren = getCurrentChildIds(nodeId);
            // Check only original connections, not pending additions/removals for this warning
            if (currentParents.length > 0 || currentChildren.length > 0) {
                if (event.target.dataset.confirmed !== "true") {
                    warnDiv.textContent = 'Warning: This node has existing connections. Deleting it will also remove these edges. Click "Delete This Node" again to confirm.';
                    warnDiv.style.display = 'block';
                    event.target.dataset.confirmed = "true"; // Mark for next click
                    return; // Don't delete yet
                }
            }
            nodeEditState.deleted = true;
            warnDiv.style.display = 'none'; // Hide warning after confirmation or if no connections
            event.target.dataset.confirmed = "false"; // Reset confirmation state
            break;
        case 'commit-node-edit':
            commitNodeChanges();
            return; // updateEditUI will be called by commit or hide
    }
    updateEditUI();
}

function getCurrentParentIds(nodeId) {
    if (!window.network || !window.network.body.data.edges) return [];
    return window.network.body.data.edges.get({
        filter: edge => String(edge.to) === String(nodeId),
        fields: ['from']
    }).map(e => String(e.from));
}

function getCurrentChildIds(nodeId) {
    if (!window.network || !window.network.body.data.edges) return [];
    return window.network.body.data.edges.get({
        filter: edge => String(edge.from) === String(nodeId),
        fields: ['to']
    }).map(e => String(e.to));
}


function updateEditUI() {
    if (!persistentTooltip || !nodeEditState.nodeId) return;

    const nodeId = nodeEditState.nodeId;
    const parentListEl = document.getElementById(`parentList-${nodeId}`);
    const childListEl = document.getElementById(`childList-${nodeId}`);
    const commitBtn = document.getElementById(`commitNodeEditBtn-${nodeId}`);
    const editWarningEl = document.getElementById(`editWarning-${nodeId}`);

    // Display current parents + pending removals/additions
    let parentHtml = '';
    const currentParents = getCurrentParentIds(nodeId);
    const pendingAddParents = nodeEditState.addParents.filter(pid => !currentParents.includes(pid));
    const pendingRemoveParents = nodeEditState.removeParents;

    // Show current parents, mark those pending removal
    currentParents.forEach(pid => {
        const isRemoving = pendingRemoveParents.includes(pid);
        parentHtml += `<span class="tooltip-chip ${isRemoving ? 'removing' : ''}" data-action="remove-parent" data-id="${pid}">${pid} <span class="chip-remove" title="Mark for removal">×</span></span> `;
    });
    // Show pending added parents (not yet in currentParents)
    pendingAddParents.forEach(pid => {
        parentHtml += `<span class="tooltip-chip adding" style="background:#e0ffe0;border:1px solid #388E3C;" title="Pending add">${pid} <span class="chip-remove" title="Undo add" data-action="undo-add-parent" data-id="${pid}">×</span></span> `;
    });
    if (parentListEl) parentListEl.innerHTML = parentHtml || '<i>None</i>';

    // Display current children + pending removals/additions
    let childHtml = '';
    const currentChildren = getCurrentChildIds(nodeId);
    const pendingAddChildren = nodeEditState.addChildren.filter(cid => !currentChildren.includes(cid));
    const pendingRemoveChildren = nodeEditState.removeChildren;

    // Show current children, mark those pending removal
    currentChildren.forEach(cid => {
        const isRemoving = pendingRemoveChildren.includes(cid);
        childHtml += `<span class="tooltip-chip ${isRemoving ? 'removing' : ''}" data-action="remove-child" data-id="${cid}">${cid} <span class="chip-remove" title="Mark for removal">×</span></span> `;
    });
    // Show pending added children (not yet in currentChildren)
    pendingAddChildren.forEach(cid => {
        childHtml += `<span class="tooltip-chip adding" style="background:#e0ffe0;border:1px solid #388E3C;" title="Pending add">${cid} <span class="chip-remove" title="Undo add" data-action="undo-add-child" data-id="${cid}">×</span></span> `;
    });
    if (childListEl) childListEl.innerHTML = childHtml || '<i>None</i>';

    // Add listeners to newly created chips for removal and undo add
    persistentTooltip.querySelectorAll('.tooltip-chip[data-action="remove-parent"] .chip-remove').forEach(icon => {
        icon.onclick = (e) => {
            e.stopPropagation();
            const parentId = icon.parentElement.parentElement.getAttribute('data-id');
            handleNodeEditAction({ target: { dataset: { action: 'remove-parent', id: parentId } } });
        };
    });
    persistentTooltip.querySelectorAll('.tooltip-chip[data-action="remove-child"] .chip-remove').forEach(icon => {
        icon.onclick = (e) => {
            e.stopPropagation();
            const childId = icon.parentElement.parentElement.getAttribute('data-id');
            handleNodeEditAction({ target: { dataset: { action: 'remove-child', id: childId } } });
        };
    });
    // Undo pending add parent/child
    persistentTooltip.querySelectorAll('.tooltip-chip.adding .chip-remove[data-action="undo-add-parent"]').forEach(icon => {
        icon.onclick = (e) => {
            e.stopPropagation();
            const parentId = icon.parentElement.textContent.trim().split(' ')[0];
            nodeEditState.addParents = nodeEditState.addParents.filter(pid => pid !== parentId);
            updateEditUI();
        };
    });
    persistentTooltip.querySelectorAll('.tooltip-chip.adding .chip-remove[data-action="undo-add-child"]').forEach(icon => {
        icon.onclick = (e) => {
            e.stopPropagation();
            const childId = icon.parentElement.textContent.trim().split(' ')[0];
            nodeEditState.addChildren = nodeEditState.addChildren.filter(cid => cid !== childId);
            updateEditUI();
        };
    });
    // Also keep the whole chip clickable for legacy support
    persistentTooltip.querySelectorAll('.tooltip-chip[data-action="remove-parent"]').forEach(chip => chip.onclick = handleNodeEditAction);
    persistentTooltip.querySelectorAll('.tooltip-chip[data-action="remove-child"]').forEach(chip => chip.onclick = handleNodeEditAction);

    // Show/hide commit button
    const hasChanges = nodeEditState.addParents.length > 0 ||
        nodeEditState.addChildren.length > 0 ||
        nodeEditState.removeParents.length > 0 ||
        nodeEditState.removeChildren.length > 0 ||
        nodeEditState.deleted;
    if (commitBtn) commitBtn.style.display = hasChanges ? 'inline-block' : 'none';

    // Pending changes summary section
    let pendingSummary = '';
    if (hasChanges) {
        pendingSummary += '<div class="tooltip-edit-group" style="margin-top:10px;"><strong>Pending Changes:</strong><ul style="margin:4px 0 0 18px;padding:0;">';
        nodeEditState.addParents.forEach(pid => {
            if (pid) pendingSummary += `<li style="color:#388E3C;">Add Parent: ${pid}</li>`;
        });
        nodeEditState.addChildren.forEach(cid => {
            if (cid) pendingSummary += `<li style="color:#388E3C;">Add Child: ${cid}</li>`;
        });
        // Show removals
        const currentParents = getCurrentParentIds(nodeId);
        const currentChildren = getCurrentChildIds(nodeId);
        nodeEditState.removeParents.forEach(pid => {
            if (currentParents.includes(pid)) {
                pendingSummary += `<li style="color:#D32F2F;">Remove Parent: ${pid}</li>`;
            }
        });
        nodeEditState.removeChildren.forEach(cid => {
            if (currentChildren.includes(cid)) {
                pendingSummary += `<li style="color:#D32F2F;">Remove Child: ${cid}</li>`;
            }
        });
        if (nodeEditState.deleted) {
            pendingSummary += `<li style="color:#D32F2F;">Node marked for deletion</li>`;
        }
        pendingSummary += '</ul></div>';
    }
    // Insert or update the pending changes summary in the tooltip
    let summaryDiv = persistentTooltip.querySelector('.tooltip-pending-summary');
    if (!summaryDiv) {
        summaryDiv = document.createElement('div');
        summaryDiv.className = 'tooltip-pending-summary';
        const contentDiv = persistentTooltip.querySelector('.custom-persistent-tooltip-content');
        if (contentDiv) contentDiv.appendChild(summaryDiv);
    }
    summaryDiv.innerHTML = pendingSummary;

    // Log pending changes summary to console
    if (hasChanges) {
        let summaryLog = `[NODE EDIT] Pending changes for node ${nodeId}:`;
        nodeEditState.addParents.forEach(pid => {
            if (pid) summaryLog += `\n  + Parent: ${pid}`;
        });
        nodeEditState.addChildren.forEach(cid => {
            if (cid) summaryLog += `\n  + Child: ${cid}`;
        });
        // Show removals for existing connections only
        const currentParents = getCurrentParentIds(nodeId);
        const currentChildren = getCurrentChildIds(nodeId);
        nodeEditState.removeParents.forEach(pid => {
            if (currentParents.includes(pid)) {
                summaryLog += `\n  - Parent: ${pid}`;
            }
        });
        nodeEditState.removeChildren.forEach(cid => {
            if (currentChildren.includes(cid)) {
                summaryLog += `\n  - Child: ${cid}`;
            }
        });
        if (nodeEditState.deleted) {
            summaryLog += `\n  [Node marked for deletion]`;
        }
        console.log('%c' + summaryLog, 'color: #5C6BC0; background: #E8EAF6; font-weight: bold; font-size: 13px; padding: 2px 8px;');
    }

    // Handle "deleted" state
    const contentDiv = persistentTooltip.querySelector('.custom-persistent-tooltip-content');
    const deleteBtn = persistentTooltip.querySelector('button[data-action="delete-node"]');

    if (nodeEditState.deleted) {
        if (contentDiv) contentDiv.style.opacity = '0.5';
        if (editWarningEl) {
            editWarningEl.textContent = 'Node marked for deletion. Commit to apply.';
            editWarningEl.style.display = 'block';
        }
        if (deleteBtn) deleteBtn.innerHTML = "Undo Delete Mark"; // Change button text
        deleteBtn.onclick = () => { // Special handler to unmark deletion
            nodeEditState.deleted = false;
            if (deleteBtn) deleteBtn.innerHTML = "Delete This Node";
            deleteBtn.dataset.confirmed = "false"; // Reset confirmation
            updateEditUI(); // Re-render UI
        };

    } else {
        if (contentDiv) contentDiv.style.opacity = '1';
        // editWarningEl might still show other messages, don't hide it unconditionally
        if (deleteBtn) {
            deleteBtn.innerHTML = "Delete This Node";
            deleteBtn.onclick = handleNodeEditAction; // Restore original handler
        }
    }
}

function commitNodeChanges() {
    if (!nodeEditState.nodeId) return;

    const changes = {
        nodeId: nodeEditState.nodeId,
        addParents: [...new Set(nodeEditState.addParents)], // Ensure unique
        addChildren: [...new Set(nodeEditState.addChildren)],
        removeParents: [...new Set(nodeEditState.removeParents)],
        removeChildren: [...new Set(nodeEditState.removeChildren)],
        deleted: nodeEditState.deleted,
    };

    // Basic validation: prevent adding self as parent/child (already handled in add logic)
    // Prevent adding a non-existent node (already handled in add logic)

    // --- SHOUT OUT NODE EDITS TO CONSOLE ---
    if (changes.deleted) {
        console.log(
            '%c[NODE EDIT COMMIT] Node deleted: ' + changes.nodeId,
            'color: #fff; background: #C62828; font-weight: bold; font-size: 16px; padding: 2px 8px; border-radius: 2px;'
        );
    } else if (
        changes.addParents.length > 0 ||
        changes.addChildren.length > 0 ||
        changes.removeParents.length > 0 ||
        changes.removeChildren.length > 0
    ) {
        let msg = `[NODE EDIT COMMIT] Changes for node ${changes.nodeId}:`;
        if (changes.addParents.length > 0) msg += `\n  + Parents: ${changes.addParents.join(', ')}`;
        if (changes.addChildren.length > 0) msg += `\n  + Children: ${changes.addChildren.join(', ')}`;
        if (changes.removeParents.length > 0) msg += `\n  - Parents: ${changes.removeParents.join(', ')}`;
        if (changes.removeChildren.length > 0) msg += `\n  - Children: ${changes.removeChildren.join(', ')}`;
        console.log(
            '%c' + msg,
            'color: #fff; background: #F57C00; font-weight: bold; font-size: 15px; padding: 2px 8px; border-radius: 2px;'
        );
    } else {
        console.log(
            '%c[NODE EDIT COMMIT] Node restored: ' + changes.nodeId,
            'color: #fff; background: #2E7D32; font-weight: bold; font-size: 15px; padding: 2px 8px; border-radius: 2px;'
        );
    }

    // --- Apply changes to vis.js DataSets ---
    applyDirectNetworkChanges(changes);

    // --- Apply visual updates to the node on the client-side after commit ---
    if (window.network && window.network.body && window.network.body.data && window.network.body.data.nodes) {
        const nodeIdToUpdate = changes.nodeId;
        const nodeObject = window.network.body.nodes[nodeIdToUpdate]; // Get the vis.js node object

        if (nodeObject) {
            let updateOptions = {};
            // Retrieve the original label, attempt to strip any "❌ " prefix if it was previously marked.
            let originalLabel = nodeObject.options.label || nodeIdToUpdate;
            if (typeof originalLabel === 'string' && originalLabel.startsWith("❌ ")) {
                originalLabel = originalLabel.substring(2).trim();
            }
            
            // Store original colors if not already stored, for proper reset
            if (nodeObject.options.originalColor === undefined) {
                nodeObject.options.originalColor = JSON.parse(JSON.stringify(nodeObject.options.color || {}));
            }
            if (nodeObject.options.originalFont === undefined) {
                nodeObject.options.originalFont = JSON.parse(JSON.stringify(nodeObject.options.font || {}));
            }
            if (nodeObject.options.originalOpacity === undefined) {
                nodeObject.options.originalOpacity = nodeObject.options.opacity !== undefined ? nodeObject.options.opacity : 1.0;
            }
            // Store original shape and image for proper reset
            if (nodeObject.options.originalShape === undefined) {
                nodeObject.options.originalShape = nodeObject.options.shape || "ellipse";
            }
            if (nodeObject.options.originalImage === undefined && nodeObject.options.image !== undefined) {
                nodeObject.options.originalImage = nodeObject.options.image;
            }


            if (changes.deleted) {
                updateOptions = {
                    shape: "image",
                    image: "https://cdn-icons-png.flaticon.com/512/1828/1828665.png",
                    imagePadding: { top: 0, bottom: 10, left: 0, right: 0 },
                    imageAlignment: "top",
                    label: originalLabel,
                    opacity: 0.4,
                    font: { color: '#D32F2F' },
                    color: {
                        background: '#E0E0E0',
                        border: '#D32F2F',
                        highlight: {
                            background: '#EEEEEE',
                            border: '#D32F2F'
                        }
                    }
                };
            } else if (changes.addParents.length > 0 || changes.addChildren.length > 0 || changes.removeParents.length > 0 || changes.removeChildren.length > 0) {
                updateOptions = {
                    label: originalLabel,
                    opacity: 0.75,
                    color: {
                        ...(nodeObject.options.originalColor || {}),
                        border: '#FF8F00',
                        highlight: {
                            ...(nodeObject.options.originalColor?.highlight || {}),
                            border: '#FF8F00'
                        }
                    },
                    font: { ...(nodeObject.options.originalFont || {}), color: (nodeObject.options.originalFont?.color || '#343434') }
                };
            } else {
                 // No structural changes, or an "undo delete" without other changes. Reset to original appearance.
                updateOptions = {
                    label: originalLabel,
                    opacity: nodeObject.options.originalOpacity !== undefined ? nodeObject.options.originalOpacity : 1.0,
                    color: JSON.parse(JSON.stringify(nodeObject.options.originalColor || {})),
                    font: JSON.parse(JSON.stringify(nodeObject.options.originalFont || {})),
                    shape: nodeObject.options.originalShape || "ellipse",
                    image: nodeObject.options.originalImage || undefined,
                    imagePadding: undefined,
                    imageAlignment: undefined
                };
            }

            if (Object.keys(updateOptions).length > 0) {
                nodeObject.setOptions(updateOptions);
                // Shout out visual update
                console.log(
                    '%c[VISUAL UPDATE] Node ' + nodeIdToUpdate + ' updated.',
                    'color: #fff; background: #1565C0; font-weight: bold; font-size: 13px; padding: 2px 8px; border-radius: 2px;'
                );
                // window.network.redraw(); // May not be needed if setOptions triggers redraw
            }
        } else {
            console.warn(`Node ${nodeIdToUpdate} not found in network.body.nodes for visual update.`);
        }
    }
    // --- End of visual updates ---

    hidePersistentTooltip(); // Close tooltip after committing
    // Optionally, re-select the node or refresh parts of the graph if changes were applied locally
}
// Apply changes directly to vis.js DataSets (client-side only)
function applyDirectNetworkChanges(changes) {
  if (!window.network) return;
  const { nodeId, addParents, addChildren, removeParents, removeChildren, deleted } = changes;
  const edgesDataSet = window.network.body.data.edges;
  const nodesDataSet = window.network.body.data.nodes;

  if (deleted) {
    try { 
      // Remove all edges connected to this node
      const connectedEdges = edgesDataSet.get({
        filter: e => e.from === nodeId || e.to === nodeId
      });
      if (connectedEdges.length) edgesDataSet.remove(connectedEdges.map(e => e.id));
      nodesDataSet.remove(nodeId); 
    } catch (e) { 
      console.warn("Error removing node:", e); 
    }
  } else {
    addParents.forEach(parentId => {
      if (nodesDataSet.get(parentId)) { // Check if parent node exists
        edgesDataSet.add({ from: parentId, to: nodeId, arrows: 'to' });
      }
    });
    addChildren.forEach(childId => {
      if (nodesDataSet.get(childId)) { // Check if child node exists
        edgesDataSet.add({ from: nodeId, to: childId, arrows: 'to' });
      }
    });
    removeParents.forEach(parentId => {
      const edges = edgesDataSet.get({
        filter: e => String(e.from) === String(parentId) && String(e.to) === String(nodeId)
      });
      if (edges.length) edgesDataSet.remove(edges.map(e => e.id));
    });
    removeChildren.forEach(childId => {
      const edges = edgesDataSet.get({
        filter: e => String(e.from) === String(nodeId) && String(e.to) === String(childId)
      });
      if (edges.length) edgesDataSet.remove(edges.map(e => e.id));
    });
  }
}

// Example of how one might apply changes directly (for client-side only demo)
// function applyDirectNetworkChanges(changes) {
//   if (!window.network) return;
//   const { nodeId, addParents, addChildren, removeParents, removeChildren, deleted } = changes;
//   const edgesDataSet = window.network.body.data.edges;
//   const nodesDataSet = window.network.body.data.nodes;

//   if (deleted) {
//     try { nodesDataSet.remove(nodeId); } catch (e) { console.warn("Error removing node:", e); }
//     // Edges connected to this node are typically removed automatically by vis.js if configured,
//     // or would need to be manually found and removed.
//   } else {
//     addParents.forEach(parentId => {
//       if (nodesDataSet.get(parentId)) { // Check if parent node exists
//         edgesDataSet.add({ from: parentId, to: nodeId, arrows: 'to' });
//       }
//     });
//     addChildren.forEach(childId => {
//       if (nodesDataSet.get(childId)) { // Check if child node exists
//         edgesDataSet.add({ from: nodeId, to: childId, arrows: 'to' });
//       }
//     });
//     removeParents.forEach(parentId => {
//       const edge = edgesDataSet.get({ filter: e => e.from === parentId && e.to === nodeId });
//       if (edge.length) edgesDataSet.remove(edge.map(e=>e.id));
//     });
//     removeChildren.forEach(childId => {
//       const edge = edgesDataSet.get({ filter: e => e.from === nodeId && e.to === childId });
//       if (edge.length) edgesDataSet.remove(edge.map(e=>e.id));
//     });
//   }
// }


function hidePersistentTooltip() {
    if (persistentTooltip) {
        persistentTooltip.remove();
        persistentTooltip = null;
        persistentTooltipNodeId = null;
        // Reset node edit state as well, or ensure it's reset when a new tooltip opens
        nodeEditState = { nodeId: null, addParents: [], addChildren: [], removeParents: [], removeChildren: [], deleted: false };
    }
}

function patchVisTooltip() {
    if (!window.network) {
        console.warn("Network not available for patching tooltips.");
        return;
    }

    // Hide Vis.js default tooltip by preventing its creation/showing
    // This is a bit of a hack. A cleaner way would be to configure vis.js tooltips to be minimal or off if possible.
    // However, we still need the 'title' attribute on nodes for our custom tooltip.
    // One common approach is to set tooltipDelay to a very high number,
    // but we want to react on click.

    // Instead of disabling, we'll just manage our own on click.
    // Clear any default 'hover' or 'click' tooltip behavior that might interfere.
    // This depends on how vis.js is configured initially.
    // For now, we assume the default title popup is either acceptable or minor.

    window.network.on("click", function (params) {
        // If click is on a node, show our custom tooltip
        if (params.nodes && params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = window.network.body.data.nodes.get(nodeId);

            if (node) {
                // Use the node's original title for the content part
                // The 'title' can be HTML. If it's a string, it will be displayed as is.
                const contentHTML = node.title || `Details for node ${nodeId}`;

                // Use the click event's pointer coordinates for positioning
                let eventForPosition = params.event && params.event.center ? { clientX: params.event.center.x, clientY: params.event.center.y } : (params.pointer && params.pointer.DOM ? { clientX: params.pointer.DOM.x, clientY: params.pointer.DOM.y } : null);

                if (!eventForPosition && params.event && params.event.srcEvent) { // Fallback for older vis versions or different event structures
                    eventForPosition = { clientX: params.event.srcEvent.clientX, clientY: params.event.srcEvent.clientY };
                }
                if (!eventForPosition) { // Absolute fallback
                    eventForPosition = { clientX: window.innerWidth / 2, clientY: window.innerHeight / 3 };
                }

                // If a persistent tooltip is already shown for this node, perhaps just bring to front or do nothing.
                // For simplicity, we'll always recreate it, ensuring it's on top and has fresh data.
                hidePersistentTooltip(); // Hide previous before showing new
                showPersistentTooltip(nodeId, contentHTML, eventForPosition);
            }
        } else {
            // Click was not on a node (e.g., on canvas background or edge)
            hidePersistentTooltip(); // Hide any visible persistent tooltip
        }
    });

    // Optional: Hide persistent tooltip on drag start to avoid interference
    window.network.on("dragStart", function () {
        if (persistentTooltip) {
            // Only hide if the dragged node is NOT the one in the tooltip,
            // or if dragging the canvas. For simplicity, hide always.
            // hidePersistentTooltip();
        }
    });

    // Optional: Hide on zoom/pan for a cleaner experience
    // window.network.on("zoom", hidePersistentTooltip);
    // window.network.on("dragEnd", function(params) { if (params.nodes.length === 0) hidePersistentTooltip(); }); // Hide if canvas drag

    console.log("Persistent tooltip event handling patched.");
}

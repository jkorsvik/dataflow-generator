// src/js/pyvis_components/tooltips.js

// REMOVED: let persistentTooltip = null;
// REMOVED: let persistentTooltipNodeId = null;
// REMOVED: let nodeEditState = { ... };
// These are now globally managed by core.js

function makeDraggable(el) {
    let isDragging = false,
        offsetX = 0,
        offsetY = 0;
    const header = el.querySelector(".custom-persistent-tooltip-header");

    if (!header) {
        console.warn("Draggable element is missing a header.");
        return;
    }
    header.style.cursor = "move";

    function onMouseDown(e) {
        if (e.button !== 0 || e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;
        e.preventDefault();
        e.stopPropagation();
        isDragging = true;
        offsetX = e.clientX - el.getBoundingClientRect().left;
        offsetY = e.clientY - el.getBoundingClientRect().top;
        document.addEventListener("mousemove", onMouseMove);
        document.addEventListener("mouseup", onMouseUp);
    }

    function onMouseMove(e) {
        if (!isDragging) return;
        e.preventDefault();
        let newLeft = e.clientX - offsetX;
        let newTop = e.clientY - offsetY;
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
    hidePersistentTooltip();

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
    // const edges = window.network.body.data.edges.get({ returnType: 'Array' }); // Not directly used here anymore for initial parents/children display, use getCurrent...

    // Reset edit state for this node (using the global nodeEditState from core.js)
    Object.assign(nodeEditState, { // Use Object.assign to modify the global state object
        nodeId: String(nodeId),
        addParents: [],
        addChildren: [],
        removeParents: [],
        removeChildren: [],
        deleted: false,
    });


    const otherNodeOptions = allNodeIds
        .filter(id => String(id) !== String(nodeId))
        .map(id => `<option value="${id}">${id}</option>`) // Added label to option for better UX if datalist dropdown shows it
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
          <button id="commitNodeEditBtn-${nodeId}" class="tooltip-edit-button tooltip-commit-button" data-action="commit-node-edit" style="display:none;">Commit Changes</button>
        </div>
      </div>
    `;

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
    persistentTooltipNodeId = String(nodeId);

    persistentTooltip.querySelector('.custom-persistent-tooltip-close').addEventListener('click', hidePersistentTooltip);
    persistentTooltip.querySelector('button[data-action="add-parent"]').addEventListener('click', handleNodeEditAction);
    persistentTooltip.querySelector('button[data-action="add-child"]').addEventListener('click', handleNodeEditAction);
    persistentTooltip.querySelector('button[data-action="delete-node"]').addEventListener('click', handleNodeEditAction);
    persistentTooltip.querySelector(`#commitNodeEditBtn-${nodeId}`).addEventListener('click', handleNodeEditAction);

    let x = event.clientX + 15;
    let y = event.clientY + 15;
    persistentTooltip.style.left = x + "px";
    persistentTooltip.style.top = y + "px";
    makeDraggable(persistentTooltip);

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

    if (window.Prism) {
        Prism.highlightAllUnder(persistentTooltip.querySelector('.custom-persistent-tooltip-content'));
    }
    updateEditUI();
}

function handleNodeEditAction(event) {
    if (!nodeEditState.nodeId) return;
    const action = event.target.dataset.action;
    console.log(`Node edit action: ${action} for node ${nodeEditState.nodeId}`);
    const nodeId = nodeEditState.nodeId;

    switch (action) {
        case 'add-parent': {
            const input = document.getElementById(`addParentInput-${nodeId}`);
            const val = input.value.trim();
            if (val && String(val) !== nodeId && !nodeEditState.addParents.includes(val) && !getCurrentParentIds(nodeId).includes(val)) {
                if (window.network.body.data.nodes.get(val)) {
                    nodeEditState.addParents.push(val);
                    input.value = '';
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
                if (window.network.body.data.nodes.get(val)) {
                    nodeEditState.addChildren.push(val);
                    input.value = '';
                } else {
                    alert(`Node "${val}" not found.`);
                }
            }
            break;
        }
        case 'remove-parent': {
            const parentIdToRemove = event.target.dataset.id; // ID of the specific parent to remove
            if (parentIdToRemove) { // Ensure an ID is provided
                if (!nodeEditState.removeParents.includes(parentIdToRemove)) {
                    nodeEditState.removeParents.push(parentIdToRemove);
                }
            } else {
                console.warn("Remove parent action called without a specific ID.");
            }
            break;
        }
        case 'remove-child': {
            const childIdToRemove = event.target.dataset.id; // ID of the specific child to remove
            if (childIdToRemove) { // Ensure an ID is provided
                if (!nodeEditState.removeChildren.includes(childIdToRemove)) {
                    nodeEditState.removeChildren.push(childIdToRemove);
                }
            } else {
                console.warn("Remove child action called without a specific ID.");
            }
            break;
        }
        case 'delete-node':
            const warnDiv = document.getElementById(`editWarning-${nodeId}`);
            const currentParents = getCurrentParentIds(nodeId);
            const currentChildren = getCurrentChildIds(nodeId);
            if (currentParents.length > 0 || currentChildren.length > 0) {
                if (event.target.dataset.confirmed !== "true") {
                    warnDiv.textContent = 'Warning: This node has existing connections. Deleting it will also remove these edges. Click "Delete This Node" again to confirm.';
                    warnDiv.style.display = 'block';
                    event.target.dataset.confirmed = "true";
                    return;
                }
            }
            nodeEditState.deleted = true;
            warnDiv.style.display = 'none';
            event.target.dataset.confirmed = "false";
            break;
        case 'commit-node-edit':
            commitNodeChanges();
            return; // updateEditUI will be called by commit or hide if successful
    }
    updateEditUI(); // Update UI after any action (except commit which handles its own flow)
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

    let parentHtml = '';
    const currentParents = getCurrentParentIds(nodeId);
    // Display only parents that are NOT yet committed for addition (they are 'current' once committed)
    const pendingAddParents = nodeEditState.addParents.filter(pid => !currentParents.includes(pid));

    currentParents.forEach(pid => {
        const isRemoving = nodeEditState.removeParents.includes(pid);
        // The chip-remove icon now correctly has data-action and data-id
        parentHtml += `<span class="tooltip-chip ${isRemoving ? 'removing' : ''}" data-id="${pid}">${pid} <span class="chip-remove" title="Mark for removal" data-action="remove-parent" data-id="${pid}">×</span></span> `;
    });
    pendingAddParents.forEach(pid => {
        // The chip-remove icon for undoing an add action
        parentHtml += `<span class="tooltip-chip adding" title="Pending add: ${pid}" data-id="${pid}">${pid} <span class="chip-remove" title="Undo add" data-action="undo-add-parent" data-id="${pid}">×</span></span> `;
    });
    if (parentListEl) parentListEl.innerHTML = parentHtml || '<i>None</i>';

    let childHtml = '';
    const currentChildren = getCurrentChildIds(nodeId);
    const pendingAddChildren = nodeEditState.addChildren.filter(cid => !currentChildren.includes(cid));

    currentChildren.forEach(cid => {
        const isRemoving = nodeEditState.removeChildren.includes(cid);
        childHtml += `<span class="tooltip-chip ${isRemoving ? 'removing' : ''}" data-id="${cid}">${cid} <span class="chip-remove" title="Mark for removal" data-action="remove-child" data-id="${cid}">×</span></span> `;
    });
    pendingAddChildren.forEach(cid => {
        childHtml += `<span class="tooltip-chip adding" title="Pending add: ${cid}" data-id="${cid}">${cid} <span class="chip-remove" title="Undo add" data-action="undo-add-child" data-id="${cid}">×</span></span> `;
    });
    if (childListEl) childListEl.innerHTML = childHtml || '<i>None</i>';

    // Event listeners for chip actions (now targeting the icons with data-id)
    persistentTooltip.querySelectorAll('.chip-remove[data-action="remove-parent"]').forEach(icon => {
        icon.onclick = (e) => {
            e.stopPropagation(); // Prevent event bubbling
            const parentId = icon.dataset.id; // Correctly get id from the icon
            handleNodeEditAction({ target: { dataset: { action: 'remove-parent', id: parentId } } });
        };
    });
    persistentTooltip.querySelectorAll('.chip-remove[data-action="remove-child"]').forEach(icon => {
        icon.onclick = (e) => {
            e.stopPropagation();
            const childId = icon.dataset.id; // Correctly get id from the icon
            handleNodeEditAction({ target: { dataset: { action: 'remove-child', id: childId } } });
        };
    });
    persistentTooltip.querySelectorAll('.chip-remove[data-action="undo-add-parent"]').forEach(icon => {
        icon.onclick = (e) => {
            e.stopPropagation();
            const parentIdToUndo = icon.dataset.id; // Correctly get id from the icon
            nodeEditState.addParents = nodeEditState.addParents.filter(pid => pid !== parentIdToUndo);
            updateEditUI();
        };
    });
    persistentTooltip.querySelectorAll('.chip-remove[data-action="undo-add-child"]').forEach(icon => {
        icon.onclick = (e) => {
            e.stopPropagation();
            const childIdToUndo = icon.dataset.id; // Correctly get id from the icon
            nodeEditState.addChildren = nodeEditState.addChildren.filter(cid => cid !== childIdToUndo);
            updateEditUI();
        };
    });
    
    // REMOVED legacy click handlers for whole chips as they were not functioning correctly with current data-action setup.
    // persistentTooltip.querySelectorAll('.tooltip-chip[data-action="remove-parent"]').forEach(chip => chip.onclick = handleNodeEditAction);
    // persistentTooltip.querySelectorAll('.tooltip-chip[data-action="remove-child"]').forEach(chip => chip.onclick = handleNodeEditAction);


    const hasChanges = nodeEditState.addParents.length > 0 ||
        nodeEditState.addChildren.length > 0 ||
        nodeEditState.removeParents.length > 0 ||
        nodeEditState.removeChildren.length > 0 ||
        nodeEditState.deleted;
    if (commitBtn) commitBtn.style.display = hasChanges ? 'inline-block' : 'none';

    let pendingSummaryHTML = ''; // Renamed to avoid conflict if 'pendingSummary' is a global
    if (hasChanges) {
        pendingSummaryHTML += '<div class="tooltip-edit-group" style="margin-top:10px;"><strong>Pending Changes:</strong><ul style="margin:4px 0 0 18px;padding:0;">';
        // Show only parents/children that are truly *pending* addition (not already existing)
        nodeEditState.addParents.filter(pid => !currentParents.includes(pid)).forEach(pid => {
            if (pid) pendingSummaryHTML += `<li style="color:#388E3C;">Add Parent: ${pid}</li>`;
        });
        nodeEditState.addChildren.filter(cid => !currentChildren.includes(cid)).forEach(cid => {
            if (cid) pendingSummaryHTML += `<li style="color:#388E3C;">Add Child: ${cid}</li>`;
        });
        // Show removals only for parents/children that actually exist currently
        nodeEditState.removeParents.filter(pid => currentParents.includes(pid)).forEach(pid => {
            pendingSummaryHTML += `<li style="color:#D32F2F;">Remove Parent: ${pid}</li>`;
        });
        nodeEditState.removeChildren.filter(cid => currentChildren.includes(cid)).forEach(cid => {
            pendingSummaryHTML += `<li style="color:#D32F2F;">Remove Child: ${cid}</li>`;
        });
        if (nodeEditState.deleted) {
            pendingSummaryHTML += `<li style="color:#D32F2F;">Node marked for deletion</li>`;
        }
        pendingSummaryHTML += '</ul></div>';
    }
    let summaryDiv = persistentTooltip.querySelector('.tooltip-pending-summary');
    if (!summaryDiv) {
        summaryDiv = document.createElement('div');
        summaryDiv.className = 'tooltip-pending-summary';
        const contentDiv = persistentTooltip.querySelector('.custom-persistent-tooltip-content');
        if (contentDiv) contentDiv.appendChild(summaryDiv); // Append to content, not edit HTML directly
    }
    summaryDiv.innerHTML = pendingSummaryHTML;

    // Console logging for pending changes (remains the same logic as before)
    if (hasChanges) {
        let summaryLog = `[NODE EDIT - PENDING] Changes for node ${nodeId}:`;
        nodeEditState.addParents.filter(pid => !currentParents.includes(pid)).forEach(pid => {
            if (pid) summaryLog += `\n  + Add Parent: ${pid}`;
        });
        nodeEditState.addChildren.filter(cid => !currentChildren.includes(cid)).forEach(cid => {
            if (cid) summaryLog += `\n  + Add Child: ${cid}`;
        });
        nodeEditState.removeParents.filter(pid => currentParents.includes(pid)).forEach(pid => {
            summaryLog += `\n  - Mark Remove Parent: ${pid}`;
        });
        nodeEditState.removeChildren.filter(cid => currentChildren.includes(cid)).forEach(cid => {
            summaryLog += `\n  - Mark Remove Child: ${cid}`;
        });
        if (nodeEditState.deleted) {
            summaryLog += `\n  [Node marked for deletion]`;
        }
        // Style for pending logs
        console.log('%c' + summaryLog, 'color: #01579B; background: #E1F5FE; font-style: italic; font-size: 12px; padding: 2px 8px; border-radius: 2px;');
    }


    const contentDiv = persistentTooltip.querySelector('.custom-persistent-tooltip-content');
    const deleteBtn = persistentTooltip.querySelector('button[data-action="delete-node"]');
    if (nodeEditState.deleted) {
        if (contentDiv) contentDiv.style.opacity = '0.5';
        if (editWarningEl) {
            editWarningEl.textContent = 'Node marked for deletion. Commit to apply.';
            editWarningEl.style.display = 'block';
        }
        if (deleteBtn) {
            deleteBtn.innerHTML = "Undo Delete Mark";
            deleteBtn.onclick = () => { // Special handler to unmark deletion
                nodeEditState.deleted = false;
                // deleteBtn.innerHTML = "Delete This Node"; // updateEditUI will reset this
                // deleteBtn.dataset.confirmed = "false"; // updateEditUI might reset this if needed
                updateEditUI();
            };
        }
    } else {
        if (contentDiv) contentDiv.style.opacity = '1';
        if (deleteBtn) {
            deleteBtn.innerHTML = "Delete This Node";
            deleteBtn.onclick = handleNodeEditAction; // Restore original handler
            // deleteBtn.dataset.confirmed = "false"; // Reset confirm state if not deleted
        }
        if (editWarningEl && editWarningEl.textContent.startsWith('Node marked for deletion')) {
             editWarningEl.style.display = 'none'; // Hide only the deletion warning
        }
    }
}


function commitNodeChanges() {
    if (!nodeEditState.nodeId) return;

    // Ensure we are using the global nodeEditState
    const changes = {
        nodeId: nodeEditState.nodeId,
        addParents: [...new Set(nodeEditState.addParents)],
        addChildren: [...new Set(nodeEditState.addChildren)],
        removeParents: [...new Set(nodeEditState.removeParents)],
        removeChildren: [...new Set(nodeEditState.removeChildren)],
        deleted: nodeEditState.deleted,
    };

    let mainActionMessage = "";
    let detailMessages = [];
    let logStyle = "";
    
    const currentParentsBeforeCommit = getCurrentParentIds(changes.nodeId);
    const currentChildrenBeforeCommit = getCurrentChildIds(changes.nodeId);

    if (changes.deleted) {
        mainActionMessage = `[NODE EDIT COMMIT] Node DELETED: ${changes.nodeId}`;
        logStyle = 'color: #fff; background: #C62828; font-weight: bold; font-size: 16px; padding: 2px 8px; border-radius: 2px;';
        
        const attemptedAddParents = changes.addParents.filter(id => !currentParentsBeforeCommit.includes(id));
        if (attemptedAddParents.length > 0) detailMessages.push(`  (Attempted to add parents: ${attemptedAddParents.join(', ')} - voided by node deletion)`);
        
        const attemptedAddChildren = changes.addChildren.filter(id => !currentChildrenBeforeCommit.includes(id));
        if (attemptedAddChildren.length > 0) detailMessages.push(`  (Attempted to add children: ${attemptedAddChildren.join(', ')} - voided by node deletion)`);
        
        const markedRemoveParents = changes.removeParents.filter(id => currentParentsBeforeCommit.includes(id));
        if (markedRemoveParents.length > 0) detailMessages.push(`  (Marked parents for removal: ${markedRemoveParents.join(', ')} - resolved by node deletion)`);

        const markedRemoveChildren = changes.removeChildren.filter(id => currentChildrenBeforeCommit.includes(id));
        if (markedRemoveChildren.length > 0) detailMessages.push(`  (Marked children for removal: ${markedRemoveChildren.join(', ')} - resolved by node deletion)`);

    } else {
        let hasStructuralChanges = false;
        const actualAddParents = changes.addParents.filter(id => !currentParentsBeforeCommit.includes(id) && window.network.body.data.nodes.get(id));
        if (actualAddParents.length > 0) {
            detailMessages.push(`  + Added Parents: ${actualAddParents.join(', ')}`);
            hasStructuralChanges = true;
        }

        const actualAddChildren = changes.addChildren.filter(id => !currentChildrenBeforeCommit.includes(id) && window.network.body.data.nodes.get(id));
        if (actualAddChildren.length > 0) {
            detailMessages.push(`  + Added Children: ${actualAddChildren.join(', ')}`);
            hasStructuralChanges = true;
        }
        
        const actualRemoveParents = changes.removeParents.filter(id => currentParentsBeforeCommit.includes(id));
        if (actualRemoveParents.length > 0) {
            detailMessages.push(`  - Removed Parents: ${actualRemoveParents.join(', ')}`);
            hasStructuralChanges = true;
        }

        const actualRemoveChildren = changes.removeChildren.filter(id => currentChildrenBeforeCommit.includes(id));
        if (actualRemoveChildren.length > 0) {
            detailMessages.push(`  - Removed Children: ${actualRemoveChildren.join(', ')}`);
            hasStructuralChanges = true;
        }

        if (hasStructuralChanges) {
            mainActionMessage = `[NODE EDIT COMMIT] Applied changes for node ${changes.nodeId}:`;
            logStyle = 'color: #fff; background: #F57C00; font-weight: bold; font-size: 15px; padding: 2px 8px; border-radius: 2px;';
        } else {
            mainActionMessage = `[NODE EDIT COMMIT] Node state confirmed for ${changes.nodeId} (no new structural changes).`;
            logStyle = 'color: #fff; background: #2E7D32; font-weight: bold; font-size: 15px; padding: 2px 8px; border-radius: 2px;';
        }
    }

    let fullLogMessage = mainActionMessage;
    if (detailMessages.length > 0) {
        fullLogMessage += "\n" + detailMessages.join("\n");
    }
    console.log('%c' + fullLogMessage, logStyle);

    applyDirectNetworkChanges(changes); // This applies the changes to the vis.js dataset

    // Visual updates (unchanged from your provided working version)
    if (window.network && window.network.body && window.network.body.data && window.network.body.data.nodes) {
        const nodeIdToUpdate = changes.nodeId;
        const nodeObject = window.network.body.nodes[nodeIdToUpdate]; 

        if (nodeObject && !changes.deleted) { // Only try to update if node object exists and was not deleted
            let updateOptions = {};
            let originalLabel = nodeObject.options.label || nodeIdToUpdate;
            if (typeof originalLabel === 'string' && originalLabel.startsWith("❌ ")) {
                originalLabel = originalLabel.substring(2).trim();
            }
            
            if (nodeObject.options.originalColor === undefined) nodeObject.options.originalColor = JSON.parse(JSON.stringify(nodeObject.options.color || {}));
            if (nodeObject.options.originalFont === undefined) nodeObject.options.originalFont = JSON.parse(JSON.stringify(nodeObject.options.font || {}));
            if (nodeObject.options.originalOpacity === undefined) nodeObject.options.originalOpacity = nodeObject.options.opacity !== undefined ? nodeObject.options.opacity : 1.0;
            if (nodeObject.options.originalShape === undefined) nodeObject.options.originalShape = nodeObject.options.shape || "ellipse";
            if (nodeObject.options.originalImage === undefined && nodeObject.options.image !== undefined) nodeObject.options.originalImage = nodeObject.options.image;

            // Determine if there were actual "committed" changes (not just reverting a delete mark)
            const committedStructuralChanges = changes.addParents.length > 0 || changes.addChildren.length > 0 ||
                                             changes.removeParents.length > 0 || changes.removeChildren.length > 0;

            if (committedStructuralChanges) { // If structural changes were made
                updateOptions = {
                    label: originalLabel,
                    opacity: 0.75,
                    color: { ...(nodeObject.options.originalColor || {}), border: '#FF8F00', highlight: { ...(nodeObject.options.originalColor?.highlight || {}), border: '#FF8F00' }},
                    font: { ...(nodeObject.options.originalFont || {}), color: (nodeObject.options.originalFont?.color || '#343434') }
                };
            } else { // No structural changes, or an "undo delete" without other changes. Reset to original.
                updateOptions = {
                    label: originalLabel,
                    opacity: nodeObject.options.originalOpacity !== undefined ? nodeObject.options.originalOpacity : 1.0,
                    color: JSON.parse(JSON.stringify(nodeObject.options.originalColor || {})),
                    font: JSON.parse(JSON.stringify(nodeObject.options.originalFont || {})),
                    shape: nodeObject.options.originalShape || "ellipse",
                    image: nodeObject.options.originalImage || undefined,
                    imagePadding: undefined, imageAlignment: undefined
                };
            }

            if (Object.keys(updateOptions).length > 0) {
                try {
                    nodeObject.setOptions(updateOptions);
                     console.log('%c[VISUAL UPDATE] Node ' + nodeIdToUpdate + ' appearance updated post-commit.', 'color: #fff; background: #1565C0; font-weight: bold; font-size: 13px; padding: 2px 8px; border-radius: 2px;');
                } catch (e) {
                    console.warn(`Error applying visual update to node ${nodeIdToUpdate} post-commit:`, e);
                }
            }
        } else if (changes.deleted) {
             console.log(`%c[VISUAL UPDATE] Node ${nodeIdToUpdate} was deleted. No direct visual style update applied to object.`, 'color: #fff; background: #1565C0; font-style: italic; font-size: 12px; padding: 2px 8px; border-radius: 2px;');
        } else {
            console.warn(`Node ${nodeIdToUpdate} not found for visual update post-commit (it might have been deleted or was never present).`);
        }
    }
    hidePersistentTooltip();
}

function applyDirectNetworkChanges(changes) {
  if (!window.network) return;
  const { nodeId, addParents, addChildren, removeParents, removeChildren, deleted } = changes;
  const edgesDataSet = window.network.body.data.edges;
  const nodesDataSet = window.network.body.data.nodes;

  if (deleted) {
    try { 
      const connectedEdges = edgesDataSet.get({ filter: e => String(e.from) === String(nodeId) || String(e.to) === String(nodeId) });
      if (connectedEdges.length) {
          edgesDataSet.remove(connectedEdges.map(e => e.id));
          console.log(`[NETWORK DATA] Removed ${connectedEdges.length} edges connected to deleted node ${nodeId}.`);
      }
      nodesDataSet.remove(nodeId); 
      console.log(`[NETWORK DATA] Node ${nodeId} removed from dataset.`);
    } catch (e) { console.warn(`Error removing node ${nodeId} from dataset:`, e); }
  } else {
    // Add new parents (create edges from parentId to nodeId)
    addParents.forEach(parentId => {
      if (nodesDataSet.get(parentId)) { // Check if parent node exists
        try { 
            // Avoid adding duplicate edges
            const existingEdge = edgesDataSet.get({ filter: e => String(e.from) === String(parentId) && String(e.to) === String(nodeId) });
            if (existingEdge.length === 0) {
                edgesDataSet.add({ from: parentId, to: nodeId, arrows: 'to' }); 
                console.log(`[NETWORK DATA] Edge added: ${parentId} -> ${nodeId}`);
            }
        } catch(e) { console.warn(`Error adding edge ${parentId} -> ${nodeId}:`, e); }
      } else {
        console.warn(`[NETWORK DATA] Cannot add parent ${parentId} for node ${nodeId}: Parent node not found.`);
      }
    });
    // Add new children (create edges from nodeId to childId)
    addChildren.forEach(childId => {
      if (nodesDataSet.get(childId)) { // Check if child node exists
         try {
            const existingEdge = edgesDataSet.get({ filter: e => String(e.from) === String(nodeId) && String(e.to) === String(childId) });
            if (existingEdge.length === 0) {
                edgesDataSet.add({ from: nodeId, to: childId, arrows: 'to' });
                console.log(`[NETWORK DATA] Edge added: ${nodeId} -> ${childId}`);
            }
         } catch(e) { console.warn(`Error adding edge ${nodeId} -> ${childId}:`, e); }
      } else {
         console.warn(`[NETWORK DATA] Cannot add child ${childId} for node ${nodeId}: Child node not found.`);
      }
    });
    // Remove parent connections
    removeParents.forEach(parentId => {
      const edgesToRemove = edgesDataSet.get({ filter: e => String(e.from) === String(parentId) && String(e.to) === String(nodeId) });
      if (edgesToRemove.length) {
          try { 
              edgesDataSet.remove(edgesToRemove.map(e => e.id)); 
              console.log(`[NETWORK DATA] Edge removed: ${parentId} -> ${nodeId}`);
          } catch(e) { console.warn(`Error removing edge ${parentId} -> ${nodeId}:`, e); }
      }
    });
    // Remove child connections
    removeChildren.forEach(childId => {
      const edgesToRemove = edgesDataSet.get({ filter: e => String(e.from) === String(nodeId) && String(e.to) === String(childId) });
      if (edgesToRemove.length) {
          try { 
              edgesDataSet.remove(edgesToRemove.map(e => e.id)); 
              console.log(`[NETWORK DATA] Edge removed: ${nodeId} -> ${childId}`);
          } catch(e) { console.warn(`Error removing edge ${nodeId} -> ${childId}:`, e); }
      }
    });
  }
}

function hidePersistentTooltip() {
    if (persistentTooltip) {
        persistentTooltip.remove();
        persistentTooltip = null; // Reset global var from core.js
    }
    // Reset global state variables from core.js
    persistentTooltipNodeId = null;
    Object.assign(nodeEditState, { 
        nodeId: null, addParents: [], addChildren: [], 
        removeParents: [], removeChildren: [], deleted: false 
    });
}

function patchVisTooltip() {
    if (!window.network) {
        console.warn("Network not available for patching tooltips.");
        return;
    }
    window.network.on("click", function (params) {
        if (params.nodes && params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = window.network.body.data.nodes.get(nodeId);
            if (node) {
                const contentHTML = node.title || `Details for node ${nodeId}`;
                let eventForPosition = params.event && params.event.center ? { clientX: params.event.center.x, clientY: params.event.center.y } : (params.pointer && params.pointer.DOM ? { clientX: params.pointer.DOM.x, clientY: params.pointer.DOM.y } : null);
                if (!eventForPosition && params.event && params.event.srcEvent) {
                    eventForPosition = { clientX: params.event.srcEvent.clientX, clientY: params.event.srcEvent.clientY };
                }
                if (!eventForPosition) {
                    eventForPosition = { clientX: window.innerWidth / 2, clientY: window.innerHeight / 3 };
                }
                hidePersistentTooltip();
                showPersistentTooltip(nodeId, contentHTML, eventForPosition);
            }
        } else {
            hidePersistentTooltip();
        }
    });
    console.log("Persistent tooltip event handling patched.");
}

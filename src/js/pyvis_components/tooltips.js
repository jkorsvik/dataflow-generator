// file: tooltips.js

// REMOVED: let persistentTooltip = null; // Globally managed by core.js
// REMOVED: let persistentTooltipNodeId = null; // Globally managed by core.js
// REMOVED: let nodeEditState = { ... }; // Globally managed by core.js

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
        isDragging = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
    }
    header.addEventListener("mousedown", onMouseDown);
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


function showPersistentTooltip(nodeId, htmlContent, event) { // htmlContent is node.title
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

    Object.assign(nodeEditState, {
        nodeId: String(nodeId),
        addParents: [], addChildren: [], removeParents: [], removeChildren: [], deleted: false,
    });

    const otherNodeOptions = allNodeIds
        .filter(id => String(id) !== String(nodeId))
        .map(id => `<option value="${id}">${id}</option>`)
        .join('');

    // The 'htmlContent' (node.title) now includes the definition with pre/code tags.
    // The editHtml is appended after this initial content.
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
        <div class="tooltip-edit-group"><strong>Current Parents:</strong> <span id="parentList-${nodeId}"></span></div>
        <div class="tooltip-edit-group"><strong>Current Children:</strong> <span id="childList-${nodeId}"></span></div>
        <div class="tooltip-edit-group" style="margin-top:15px;"><button class="tooltip-edit-button tooltip-delete-button" data-action="delete-node">Delete This Node</button></div>
        <div id="editWarning-${nodeId}" class="tooltip-edit-warning" style="display:none;"></div>
        <div style="margin-top:15px; text-align: right;"><button id="commitNodeEditBtn-${nodeId}" class="tooltip-edit-button tooltip-commit-button" data-action="commit-node-edit" style="display:none;">Commit Changes</button></div>
      </div>
    `;

    const tooltipTitle = node.label || nodeId; // Used for the header
    
    persistentTooltip.innerHTML =
        `<div class="custom-persistent-tooltip-header">
           <h3>${tooltipTitle}</h3>
           <button class="custom-persistent-tooltip-close" title="Close (Esc)">×</button>
         </div>
         <div class="custom-persistent-tooltip-content">
           <div class="custom-tooltip-section">${htmlContent}</div> 
           ${editHtml}
         </div>`;
         // htmlContent (which is node.title from Python) is placed here.
         // It should now contain the definition block with <pre><code class="language-sql">...</code></pre>

    document.body.appendChild(persistentTooltip);
    persistentTooltipNodeId = String(nodeId);

    const safeAddEventListener = (selector, eventType, handlerFn) => {
        const element = persistentTooltip.querySelector(selector);
        if (element) { element.onclick = handlerFn; }
        else { console.warn(`[DEBUG] safeAddEventListener: Element not found for selector "${selector}" in persistent tooltip`); }
    };

    safeAddEventListener('.custom-persistent-tooltip-close', 'click', hidePersistentTooltip);
    safeAddEventListener('button[data-action="add-parent"]', 'click', handleNodeEditAction);
    safeAddEventListener('button[data-action="add-child"]', 'click', handleNodeEditAction);
    safeAddEventListener('button[data-action="delete-node"]', 'click', handleNodeEditAction);
    safeAddEventListener(`#commitNodeEditBtn-${nodeId}`, 'click', handleNodeEditAction);
    
    const mainDeleteButton = persistentTooltip.querySelector('button[data-action="delete-node"]');
    if (mainDeleteButton) { mainDeleteButton.onclick = handleNodeEditAction; }

    let x = event.clientX + 15;
    let y = event.clientY + 15;
    persistentTooltip.style.left = x + "px";
    persistentTooltip.style.top = y + "px";
    makeDraggable(persistentTooltip);

    Promise.resolve().then(() => { /* Position adjustment code */
        const ttRect = persistentTooltip.getBoundingClientRect();
        if (x + ttRect.width > window.innerWidth) x = Math.max(0, window.innerWidth - ttRect.width - 10);
        if (y + ttRect.height > window.innerHeight) y = Math.max(0, window.innerHeight - ttRect.height - 10);
        persistentTooltip.style.left = x + "px";
        persistentTooltip.style.top = y + "px";
    });

    if (window.Prism && persistentTooltip) {
        const contentArea = persistentTooltip.querySelector('.custom-persistent-tooltip-content');
        if (contentArea) {
            console.log("[DEBUG] Calling Prism.highlightAllUnder for persistent tooltip.");
            Prism.highlightAllUnder(contentArea);
        } else {
            console.warn("[DEBUG] Persistent tooltip content area not found for Prism highlighting.");
        }
    } else {
        console.warn("[DEBUG] Prism or persistentTooltip not available for highlighting.");
    }
    updateEditUI();
}

function handleNodeEditAction(event) {
    // !!! PRIMARY FIX: Stop the event immediately !!!
    event.stopPropagation();
    event.preventDefault();

    if (!nodeEditState.nodeId) return;
    const action = event.target.dataset.action;
    console.log(`Node edit action: ${action} for node ${nodeEditState.nodeId}`);
    const nodeId = nodeEditState.nodeId;
    const actionButtonElement = event.target;

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
            const parentIdToRemove = actionButtonElement.dataset.id;
            if (parentIdToRemove) {
                if (!nodeEditState.removeParents.includes(parentIdToRemove)) {
                    nodeEditState.removeParents.push(parentIdToRemove);
                }
            } else {
                console.warn("Remove parent action called without a specific ID.");
            }
            break;
        }
        case 'remove-child': {
            const childIdToRemove = actionButtonElement.dataset.id;
            if (childIdToRemove) {
                if (!nodeEditState.removeChildren.includes(childIdToRemove)) {
                    nodeEditState.removeChildren.push(childIdToRemove);
                }
            } else {
                console.warn("Remove child action called without a specific ID.");
            }
            break;
        }
        case 'delete-node': {
            console.log("[DEBUG] 'delete-node' action initiated by click on button:", actionButtonElement);
            // This button's role is to initiate deletion or confirm it.
            // The "Undo" functionality is handled by a different onclick assigned in updateEditUI.

            const warnDiv = document.getElementById(`editWarning-${nodeId}`);
            const currentParents = getCurrentParentIds(nodeId); // THIS WAS THE MISSING FUNCTION
            const currentChildren = getCurrentChildIds(nodeId); // THIS WAS THE MISSING FUNCTION

            if (currentParents.length > 0 || currentChildren.length > 0) {
                if (actionButtonElement.dataset.confirmed !== "true") {
                    console.log("[DEBUG] Node has connections, needs confirmation.");
                    if (warnDiv) {
                        warnDiv.textContent = 'Warning: This node has existing connections. Deleting it will also remove these edges. Click "Delete This Node" again to confirm.';
                        warnDiv.style.display = 'block';
                    }
                    actionButtonElement.dataset.confirmed = "true";
                    return; // Wait for second click, do not call updateEditUI yet.
                }
                console.log("[DEBUG] Node has connections, confirmation received.");
            } else {
                console.log("[DEBUG] Node has no connections. Proceeding to mark for deletion.");
            }
            
            nodeEditState.deleted = true;
            // dataset.confirmed will be reset by updateEditUI if node is not deleted,
            // or it's irrelevant if it is deleted.
            break;
        }
        case 'commit-node-edit':
            commitNodeChanges();
            return; 
    }
    updateEditUI(); 
}


function updateEditUI() {
    if (!persistentTooltip || !nodeEditState.nodeId) {
        console.log("[DEBUG] updateEditUI called but persistentTooltip or nodeEditState.nodeId is missing. Aborting.");
        return;
    }

    const nodeId = nodeEditState.nodeId;
    console.log(`[DEBUG] updateEditUI running for node: ${nodeId}, deleted state: ${nodeEditState.deleted}`);

    const parentListEl = document.getElementById(`parentList-${nodeId}`);
    const childListEl = document.getElementById(`childList-${nodeId}`);
    const commitBtn = document.getElementById(`commitNodeEditBtn-${nodeId}`);
    const editWarningEl = document.getElementById(`editWarning-${nodeId}`);

    let parentHtml = '';
    const currentParents = getCurrentParentIds(nodeId);
    const pendingAddParents = nodeEditState.addParents.filter(pid => !currentParents.includes(pid));

    currentParents.forEach(pid => {
        const isRemoving = nodeEditState.removeParents.includes(pid);
        parentHtml += `<span class="tooltip-chip ${isRemoving ? 'removing' : ''}" data-id="${pid}">${pid} <span class="chip-remove" title="Mark for removal" data-action="remove-parent" data-id="${pid}">×</span></span> `;
    });
    pendingAddParents.forEach(pid => {
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
    
    const chipSelectorsAndActions = [
        { selector: '.chip-remove[data-action="remove-parent"]', action: 'remove-parent' },
        { selector: '.chip-remove[data-action="remove-child"]', action: 'remove-child' },
        { selector: '.chip-remove[data-action="undo-add-parent"]', specialHandler: (icon) => { nodeEditState.addParents = nodeEditState.addParents.filter(pid => pid !== icon.dataset.id); updateEditUI(); } },
        { selector: '.chip-remove[data-action="undo-add-child"]', specialHandler: (icon) => { nodeEditState.addChildren = nodeEditState.addChildren.filter(cid => cid !== icon.dataset.id); updateEditUI(); } }
    ];

    chipSelectorsAndActions.forEach(item => {
        persistentTooltip.querySelectorAll(item.selector).forEach(icon => {
            icon.onclick = (e) => {
                e.stopPropagation();
                e.preventDefault();
                if (item.specialHandler) {
                    item.specialHandler(icon);
                } else {
                    handleNodeEditAction({ target: { dataset: { action: item.action, id: icon.dataset.id } } });
                }
            };
        });
    });
    
    const hasChanges = nodeEditState.addParents.length > 0 ||
        nodeEditState.addChildren.length > 0 ||
        nodeEditState.removeParents.length > 0 ||
        nodeEditState.removeChildren.length > 0 ||
        nodeEditState.deleted;

    if (commitBtn) {
        console.log(`[DEBUG] commitBtn found for ${nodeId}. hasChanges: ${hasChanges}. Setting display to: ${hasChanges ? 'inline-block' : 'none'}`);
        commitBtn.style.display = hasChanges ? 'inline-block' : 'none';
    } else {
        console.log(`[DEBUG] commitBtn NOT found for node ${nodeId}. Cannot set display.`);
    }

    let pendingSummaryHTML = '';
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
        console.log('%c' + summaryLog, 'color: #01579B; background: #E1F5FE; font-style: italic; font-size: 12px; padding: 2px 8px; border-radius: 2px;');

        pendingSummaryHTML += '<div class="tooltip-edit-group" style="margin-top:10px;"><strong>Pending Changes:</strong><ul style="margin:4px 0 0 18px;padding:0;">';
        nodeEditState.addParents.filter(pid => !currentParents.includes(pid)).forEach(pid => {
            if (pid) pendingSummaryHTML += `<li style="color:#388E3C;">Add Parent: ${pid}</li>`;
        });
        nodeEditState.addChildren.filter(cid => !currentChildren.includes(cid)).forEach(cid => {
            if (cid) pendingSummaryHTML += `<li style="color:#388E3C;">Add Child: ${cid}</li>`;
        });
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
        const editSectionContainer = persistentTooltip.querySelector('.custom-tooltip-section + div'); 
        if (editSectionContainer && editSectionContainer.parentNode) {
             // Insert summaryDiv after the entire edit HTML block.
             // The editHtml block is the second child of .custom-persistent-tooltip-content
            const mainContentDiv = persistentTooltip.querySelector('.custom-persistent-tooltip-content');
            if (mainContentDiv && mainContentDiv.children[1]) { // children[1] should be the div containing editHtml
                 mainContentDiv.children[1].appendChild(summaryDiv);
            } else if (mainContentDiv) { // Fallback
                mainContentDiv.appendChild(summaryDiv);
            }
        } else { 
            const fallbackContentArea = persistentTooltip.querySelector('.custom-persistent-tooltip-content');
            if (fallbackContentArea) fallbackContentArea.appendChild(summaryDiv);
        }
    }
    summaryDiv.innerHTML = pendingSummaryHTML;


    const contentDiv = persistentTooltip.querySelector('.custom-persistent-tooltip-content');
    const deleteBtn = persistentTooltip.querySelector('button[data-action="delete-node"]');

    if (nodeEditState.deleted) {
        console.log(`[DEBUG] updateEditUI for ${nodeId}: nodeEditState.deleted is TRUE. Entering block to update UI for deletion state.`);
        if (contentDiv) {
            console.log(`[DEBUG] updateEditUI for ${nodeId}: Setting contentDiv opacity to 0.5.`);
            contentDiv.style.opacity = '0.5';
        }
        if (editWarningEl) {
            console.log(`[DEBUG] updateEditUI for ${nodeId}: editWarningEl found. Setting text to "Node marked for deletion..." and display to "block".`);
            editWarningEl.textContent = 'Node marked for deletion. Commit to apply.';
            editWarningEl.style.display = 'block';
        } else {
            console.log(`[DEBUG] updateEditUI for ${nodeId}: editWarningEl NOT found when trying to show 'marked for deletion' warning.`);
        }
        if (deleteBtn) {
            console.log(`[DEBUG] updateEditUI for ${nodeId}: deleteBtn found. Setting innerHTML to "Undo Delete Mark" AND FRESH onclick handler.`);
            deleteBtn.innerHTML = "Undo Delete Mark";
            deleteBtn.onclick = function(event) { 
                event.stopPropagation(); 
                event.preventDefault();
                console.log(`[DEBUG] "Undo Delete Mark" button clicked for ${nodeId}.`);
                nodeEditState.deleted = false;
                updateEditUI();
            };
        } else {
            console.log(`[DEBUG] updateEditUI for ${nodeId}: deleteBtn (button[data-action="delete-node"]) NOT found when trying to set "Undo Delete Mark".`);
        }
    } else { 
        console.log(`[DEBUG] updateEditUI for ${nodeId}: nodeEditState.deleted is FALSE. Entering block to reset UI from deletion state.`);
        if (contentDiv) {
            console.log(`[DEBUG] updateEditUI for ${nodeId}: Resetting contentDiv opacity to 1.`);
            contentDiv.style.opacity = '1';
        }
        if (deleteBtn) {
            console.log(`[DEBUG] updateEditUI for ${nodeId}: deleteBtn found. Resetting innerHTML to "Delete This Node" and RESTORING original onclick handler.`);
            deleteBtn.innerHTML = "Delete This Node";
            deleteBtn.onclick = handleNodeEditAction; 
            deleteBtn.dataset.confirmed = "false"; 
        } else {
            console.log(`[DEBUG] updateEditUI for ${nodeId}: deleteBtn (button[data-action="delete-node"]) NOT found when trying to reset to "Delete This Node".`);
        }
        // Clear general "marked for deletion" warning if it's showing and node is no longer marked deleted
        if (editWarningEl && editWarningEl.textContent.includes('Node marked for deletion')) {
            console.log(`[DEBUG] updateEditUI for ${nodeId}: Hiding 'Node marked for deletion' warning.`);
            editWarningEl.style.display = 'none';
        }
        // Also ensure connection-specific warning is hidden if not relevant
        if (editWarningEl && editWarningEl.textContent.includes('existing connections') && !actionButtonElement.dataset.confirmed === "true") {
             editWarningEl.style.display = 'none';
        }
    }
}


// commitNodeChanges, applyDirectNetworkChanges, hidePersistentTooltip, patchVisTooltip
// remain IDENTICAL to the previous DEBUG version.
// It's crucial these are copied VERBATIM from the previous working debug version.

function commitNodeChanges() {
    if (!nodeEditState.nodeId) return;

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

    applyDirectNetworkChanges(changes); 

    if (window.network && window.network.body && window.network.body.data && window.network.body.data.nodes) {
        const nodeIdToUpdate = changes.nodeId;
        const nodeObject = window.network.body.nodes[nodeIdToUpdate]; 

        if (nodeObject && !changes.deleted) { 
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

            const committedStructuralChanges = changes.addParents.length > 0 || changes.addChildren.length > 0 ||
                                             changes.removeParents.length > 0 || changes.removeChildren.length > 0;

            if (committedStructuralChanges) { 
                updateOptions = {
                    label: originalLabel,
                    opacity: 0.75,
                    color: { ...(nodeObject.options.originalColor || {}), border: '#FF8F00', highlight: { ...(nodeObject.options.originalColor?.highlight || {}), border: '#FF8F00' }},
                    font: { ...(nodeObject.options.originalFont || {}), color: (nodeObject.options.originalFont?.color || '#343434') }
                };
            } else { 
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
    addParents.forEach(parentId => {
      if (nodesDataSet.get(parentId)) { 
        try { 
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
    addChildren.forEach(childId => {
      if (nodesDataSet.get(childId)) { 
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
    removeParents.forEach(parentId => {
      const edgesToRemove = edgesDataSet.get({ filter: e => String(e.from) === String(parentId) && String(e.to) === String(nodeId) });
      if (edgesToRemove.length) {
          try { 
              edgesDataSet.remove(edgesToRemove.map(e => e.id)); 
              console.log(`[NETWORK DATA] Edge removed: ${parentId} -> ${nodeId}`);
          } catch(e) { console.warn(`Error removing edge ${parentId} -> ${nodeId}:`, e); }
      }
    });
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
        persistentTooltip = null; 
    }
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
        const realEvt = params.event && params.event.srcEvent;
        if (realEvt && realEvt.target.closest('.custom-persistent-tooltip')) {
            return;
        }
        const pos = params.pointer && params.pointer.DOM;
        const nodeId = pos ? window.network.getNodeAt(pos) : null;
        if (nodeId) {
            const node = window.network.body.data.nodes.get(nodeId);
            if (node) {
                const contentHTML = node.title || `Details for node ${nodeId}`;
                let eventForPosition = params.event && params.event.srcEvent
                    ? { clientX: params.event.srcEvent.clientX, clientY: params.event.srcEvent.clientY }
                    : pos
                        ? { clientX: pos.x, clientY: pos.y }
                        : { clientX: window.innerWidth / 2, clientY: window.innerHeight / 3 };
                hidePersistentTooltip();
                showPersistentTooltip(nodeId, contentHTML, eventForPosition);
            }
        } else {
            hidePersistentTooltip();
        }
    });
    console.log("Persistent tooltip event handling patched.");
}
// src/js/pyvis_components/selection.js

// --- Selection Mode Functions ---
function startSelectionMode() {
    if (!window.network) {
        alert("Network not ready to start selection mode.");
        console.warn("Network not ready for selection mode.");
        return;
    }
    console.log("Starting selection mode...");

    // Ensure elements are fetched (they should be available after DOMContentLoaded)
    selectionOverlay = selectionOverlay || document.getElementById("selectionOverlay");
    selectionRectangle = selectionRectangle || document.getElementById("selectionRectangle");
    exportChoiceModal = exportChoiceModal || document.getElementById("exportChoiceModal");

    if (!selectionOverlay || !selectionRectangle || !exportChoiceModal) {
        console.error("Selection UI elements (overlay, rectangle, or modal) not found.");
        alert("Error: Selection UI components are missing.");
        return;
    }

    selectionOverlay.style.display = "block";
    exportChoiceModal.style.display = "none"; // Hide export choice initially
    selectionRectangle.style.display = "none"; // Hide until first mousedown
    isSelecting = false;
    selectionCanvasCoords = null; // Reset previous selection

    // Add event listeners for selection
    // Use { passive: false } for mousemove to allow preventDefault if needed by underlying logic, though not strictly used here
    selectionOverlay.addEventListener("mousedown", handleMouseDown);
    selectionOverlay.addEventListener("mousemove", handleMouseMove, { passive: false });
    selectionOverlay.addEventListener("mouseup", handleMouseUp);
    selectionOverlay.addEventListener("mouseleave", handleMouseLeave); // Cancel if mouse leaves while dragging

    // Focus the overlay to catch keyboard events like Escape if desired (optional)
    // selectionOverlay.setAttribute('tabindex', '-1');
    // selectionOverlay.focus();
}

function cancelSelectionMode() {
    console.log("Cancelling selection mode...");
    if (selectionOverlay) {
        selectionOverlay.style.display = "none";
        selectionOverlay.removeEventListener("mousedown", handleMouseDown);
        selectionOverlay.removeEventListener("mousemove", handleMouseMove);
        selectionOverlay.removeEventListener("mouseup", handleMouseUp);
        selectionOverlay.removeEventListener("mouseleave", handleMouseLeave);
        // selectionOverlay.removeAttribute('tabindex');
    }
    if (selectionRectangle) {
        selectionRectangle.style.display = "none";
    }
    if (exportChoiceModal) {
        exportChoiceModal.style.display = "none";
    }
    isSelecting = false;
    selectionCanvasCoords = null;
}

function handleMouseDown(event) {
    if (event.button !== 0) return; // Only respond to left-click

    isSelecting = true;
    const overlayRect = selectionOverlay.getBoundingClientRect();
    selectionStartX = event.clientX; // Store initial mouse X relative to viewport
    selectionStartY = event.clientY; // Store initial mouse Y relative to viewport

    // Position of the selection rectangle is relative to the overlay
    selectionRect.x = event.clientX - overlayRect.left;
    selectionRect.y = event.clientY - overlayRect.top;
    selectionRect.width = 0;
    selectionRect.height = 0;

    selectionRectangle.style.left = selectionRect.x + "px";
    selectionRectangle.style.top = selectionRect.y + "px";
    selectionRectangle.style.width = "0px";
    selectionRectangle.style.height = "0px";
    selectionRectangle.style.display = "block";

    event.preventDefault(); // Prevent text selection on the page or other default drag behaviors
}

function handleMouseMove(event) {
    if (!isSelecting) return;

    const overlayRect = selectionOverlay.getBoundingClientRect();
    const currentX = event.clientX - overlayRect.left; // Current mouse X relative to overlay
    const currentY = event.clientY - overlayRect.top;   // Current mouse Y relative to overlay

    // Calculate width and height from the initial mousedown point (selectionRect.x, selectionRect.y)
    let newWidth = currentX - selectionRect.x;
    let newHeight = currentY - selectionRect.y;

    // Handle dragging in all directions (up-left, up-right, down-left, down-right)
    let displayX = selectionRect.x;
    let displayY = selectionRect.y;

    if (newWidth < 0) {
        displayX = currentX;
        newWidth = -newWidth;
    }
    if (newHeight < 0) {
        displayY = currentY;
        newHeight = -newHeight;
    }

    selectionRectangle.style.left = displayX + "px";
    selectionRectangle.style.top = displayY + "px";
    selectionRectangle.style.width = newWidth + "px";
    selectionRectangle.style.height = newHeight + "px";

    // Store the current, potentially negative, width/height to know the drag direction later
    selectionRect.width = currentX - selectionRect.x;
    selectionRect.height = currentY - selectionRect.y;
}

function handleMouseUp(event) {
    if (!isSelecting) return;
    isSelecting = false;

    // Final width and height of the drawn rectangle
    const finalRectWidth = parseFloat(selectionRectangle.style.width);
    const finalRectHeight = parseFloat(selectionRectangle.style.height);

    // If selection is too small, cancel it
    if (finalRectWidth < 5 || finalRectHeight < 5) {
        console.log("Selection too small, cancelled.");
        selectionRectangle.style.display = "none"; // Hide the drawn rectangle
        // Don't hide overlay yet, allow another attempt or explicit cancel
        // For immediate cancel and hide overlay: cancelSelectionMode();
        return;
    }

    // Coordinates for DOMtoCanvas are relative to the viewport
    // The rectangle's `left` and `top` are relative to `selectionOverlay`
    const overlayRect = selectionOverlay.getBoundingClientRect();
    let domX1 = parseFloat(selectionRectangle.style.left) + overlayRect.left;
    let domY1 = parseFloat(selectionRectangle.style.top) + overlayRect.top;
    let domX2 = domX1 + finalRectWidth;
    let domY2 = domY1 + finalRectHeight;

    // Convert DOM coordinates (viewport) to Canvas coordinates
    try {
        const canvasStart = window.network.DOMtoCanvas({ x: domX1, y: domY1 });
        const canvasEnd = window.network.DOMtoCanvas({ x: domX2, y: domY2 });

        selectionCanvasCoords = {
            x: Math.min(canvasStart.x, canvasEnd.x),
            y: Math.min(canvasStart.y, canvasEnd.y),
            width: Math.abs(canvasEnd.x - canvasStart.x),
            height: Math.abs(canvasEnd.y - canvasStart.y),
        };
        console.log("Selection finished. Canvas Coords:", selectionCanvasCoords);

        if (exportChoiceModal) {
            exportChoiceModal.style.display = "block";
            // Position modal near selection or center screen (optional)
        } else {
            console.error("Export choice modal not found! Cannot proceed with export options.");
            // Fallback: maybe directly offer PNG if modal is missing? Or just log.
        }
    } catch (e) {
        console.error("Error converting DOM to Canvas coordinates:", e);
        alert("Could not process selection coordinates. Network might not be stable or view is unusual.");
        selectionCanvasCoords = null;
    }

    selectionRectangle.style.display = "none"; // Hide rectangle after selection attempt
    selectionOverlay.style.display = "none"; // Hide overlay after selection is processed

    // Clean up overlay listeners after selection is done or modal shown
    selectionOverlay.removeEventListener("mousedown", handleMouseDown);
    selectionOverlay.removeEventListener("mousemove", handleMouseMove);
    selectionOverlay.removeEventListener("mouseup", handleMouseUp);
    selectionOverlay.removeEventListener("mouseleave", handleMouseLeave);
}

function handleMouseLeave(event) {
    // If currently dragging a selection and mouse leaves the overlay, cancel the drag
    if (isSelecting) {
        console.log("Mouse left overlay during selection, cancelling current drag.");
        isSelecting = false; // Stop the current drag
        selectionRectangle.style.display = "none"; // Hide the rectangle being drawn
        // Consider if the entire selection mode should be cancelled:
        // cancelSelectionMode();
        // Or just reset the current drag:
        // selectionRect.width = 0; selectionRect.height = 0;
    }
}

// --- Trigger Export based on Choice from Modal ---
function exportSelection(format) {
    if (exportChoiceModal) {
        exportChoiceModal.style.display = "none"; // Hide modal first
    }

    if (!selectionCanvasCoords || selectionCanvasCoords.width <= 0 || selectionCanvasCoords.height <= 0) {
        console.error("No valid selection coordinates available for export.");
        alert("Error: No valid selection was made or selection coordinates are invalid.");
        cancelSelectionMode(); // Ensure everything is reset
        return;
    }

    if (format === "png") {
        // Use a default scale factor, or make it configurable
        exportToPNG(selectionCanvasCoords, 1.5);
    } else if (format === "svg") {
        exportToSVG(selectionCanvasCoords);
    } else {
        console.error("Unknown export format requested:", format);
    }

    // Reset selection state after export attempt (or explicit cancel)
    // cancelSelectionMode(); // This will also clear selectionCanvasCoords
    // Or just clear coords if mode should persist for another selection:
    selectionCanvasCoords = null;
}
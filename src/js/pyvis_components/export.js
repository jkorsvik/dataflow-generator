// src/js/pyvis_components/export.js

// --- SVG Generation ---
async function generateNetworkSVG(cropArea = null) {
    console.log("Generating SVG:", cropArea ? "for selection" : "for full network");
    if (!window.network || !window.network.body || !window.network.getPositions) {
        console.error("Network object or required components not available for SVG export.");
        throw new Error("Network not ready for SVG export.");
    }

    const nodeIds = window.network.body.nodeIndices;
    const edgeIds = window.network.body.edgeIndices;
    const positions = window.network.getPositions(); // Gets all node positions

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    let hasContent = false;

    nodeIds.forEach(nodeId => {
        const node = window.network.body.nodes[nodeId];
        if (!node || node.options.hidden || !positions[nodeId]) return;

        const pos = positions[nodeId];
        const size = (node.options.size || 10) * 2; // diameter
        const borderWidth = (node.options.borderWidth || 1) * 2;
        const extent = size / 2 + borderWidth / 2;

        if (cropArea) {
            // Consider node only if its center is within the crop area
            // A more accurate check would involve the node's bounding box vs cropArea
            if (pos.x < cropArea.x || pos.x > cropArea.x + cropArea.width ||
                pos.y < cropArea.y || pos.y > cropArea.y + cropArea.height) {
                return; // Skip if node center is outside crop area
            }
        }

        minX = Math.min(minX, pos.x - extent);
        maxX = Math.max(maxX, pos.x + extent);
        minY = Math.min(minY, pos.y - extent);
        maxY = Math.max(maxY, pos.y + extent);
        hasContent = true;
    });


    if (cropArea) {
        // If cropping, the viewbox is defined by the cropArea
        minX = cropArea.x;
        minY = cropArea.y;
        maxX = cropArea.x + cropArea.width;
        maxY = cropArea.y + cropArea.height;
        // If hasContent became true, it means at least one node center was in cropArea.
        // If no node centers were in cropArea, hasContent is false.
        // We might still want to export the area if edges cross it.
        // For simplicity, if cropArea is given, we use its bounds.
        hasContent = true; // Assume crop area itself is content.
    } else if (hasContent) {
        const padding = 50; // Padding for full export
        minX -= padding;
        minY -= padding;
        maxX += padding;
        maxY += padding;
    } else { // No content and no crop area (empty graph)
        minX = -200; minY = -200; maxX = 200; maxY = 200; // Default size for empty graph
    }

    let viewboxWidth = maxX - minX;
    let viewboxHeight = maxY - minY;

    if (viewboxWidth <= 0 || viewboxHeight <= 0) {
        console.warn("Calculated SVG bounds are zero or negative. Using default 400x400.");
        // This can happen if cropArea has zero width/height, or if all content is at a single point.
        minX = (minX + maxX - 400) / 2; // Center the default box
        minY = (minY + maxY - 400) / 2;
        viewboxWidth = 400;
        viewboxHeight = 400;
    }

    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("xmlns", svgNS);
    svg.setAttribute("viewBox", `${minX} ${minY} ${viewboxWidth} ${viewboxHeight}`);
    svg.setAttribute("width", viewboxWidth.toString());
    svg.setAttribute("height", viewboxHeight.toString());
    svg.style.backgroundColor = window.getComputedStyle(document.getElementById("mynetwork").querySelector("canvas")).backgroundColor || "#ffffff";
    svg.setAttribute("shape-rendering", "geometricPrecision"); // Crisper shapes

    // Define marker for arrowheads
    const defs = document.createElementNS(svgNS, "defs");
    const marker = document.createElementNS(svgNS, "marker");
    marker.setAttribute("id", "arrowhead_svgexport"); // Unique ID to avoid conflicts
    marker.setAttribute("viewBox", "-5 -5 10 10");
    marker.setAttribute("refX", "5"); // Adjusted for node boundary
    marker.setAttribute("refY", "0");
    marker.setAttribute("markerWidth", "6");
    marker.setAttribute("markerHeight", "6");
    marker.setAttribute("orient", "auto-start-reverse");
    const arrowPath = document.createElementNS(svgNS, "path");
    arrowPath.setAttribute("d", "M -5 -5 L 5 0 L -5 5 z"); // Arrow shape
    // Arrow color will be set per edge
    marker.appendChild(arrowPath);
    defs.appendChild(marker);
    svg.appendChild(defs);

    // Draw Edges
    const edgesGroup = document.createElementNS(svgNS, "g");
    edgesGroup.setAttribute("id", "edges_svgexport");
    edgeIds.forEach(edgeId => {
        const edge = window.network.body.edges[edgeId];
        if (!edge || edge.options.hidden || !edge.fromId || !edge.toId || !positions[edge.fromId] || !positions[edge.toId]) return;

        const fromNode = window.network.body.nodes[edge.fromId];
        const toNode = window.network.body.nodes[edge.toId];
        if (!fromNode || !toNode) return; // Ensure nodes exist

        const fromPos = positions[edge.fromId];
        const toPos = positions[edge.toId];

        // Basic filtering for edges when cropping: if both endpoints are far outside, skip.
        // This is a simplification; true SVG clipping is complex.
        if (cropArea) {
            const margin = Math.max(viewboxWidth, viewboxHeight); // Generous margin
            const isFromOutside = fromPos.x < cropArea.x - margin || fromPos.x > cropArea.x + cropArea.width + margin || fromPos.y < cropArea.y - margin || fromPos.y > cropArea.y + cropArea.height + margin;
            const isToOutside = toPos.x < cropArea.x - margin || toPos.x > cropArea.x + cropArea.width + margin || toPos.y < cropArea.y - margin || toPos.y > cropArea.y + cropArea.height + margin;
            if (isFromOutside && isToOutside) return;
        }

        const edgeOptions = edge.options;
        const pathEl = document.createElementNS(svgNS, "path");
        let dAttr = `M ${fromPos.x} ${fromPos.y}`;

        // Handle smooth curves (cubicBezier)
        if (edgeOptions.smooth && edgeOptions.smooth.enabled && edgeOptions.smooth.type === "cubicBezier" && edge.edgeType.getCtrlPoints) {
            const controlPoints = edge.edgeType.getCtrlPoints(fromPos, toPos, edgeOptions.smooth); // This is an internal vis.js way, might need reimplementation or simplification
            if (controlPoints && controlPoints.length >= 2) { // Assuming two control points for cubic Bezier
                dAttr += ` C ${controlPoints[0].x} ${controlPoints[0].y}, ${controlPoints[1].x} ${controlPoints[1].y}, ${toPos.x} ${toPos.y}`;
            } else { // Fallback to line if control points aren't available as expected
                dAttr += ` L ${toPos.x} ${toPos.y}`;
            }
        } else { // Straight line
            dAttr += ` L ${toPos.x} ${toPos.y}`;
        }
        pathEl.setAttribute("d", dAttr);

        const color = (edgeOptions.color && (edgeOptions.color.color || edgeOptions.color.inherit)) || edgeOptions.color || "#848484"; // Default vis.js edge color
        const opacity = (edgeOptions.color && edgeOptions.color.opacity != null) ? edgeOptions.color.opacity : (edgeOptions.opacity != null ? edgeOptions.opacity : 1.0);
        const strokeWidth = edgeOptions.width || 1;

        pathEl.setAttribute("stroke", color === 'inherit' ? (fromNode.options.color?.border || '#848484') : color); // Handle inherit
        pathEl.setAttribute("stroke-width", strokeWidth.toString());
        pathEl.setAttribute("stroke-opacity", opacity.toString());
        pathEl.setAttribute("fill", "none");

        if (edgeOptions.arrows && (edgeOptions.arrows.to?.enabled || (typeof edgeOptions.arrows === 'string' && edgeOptions.arrows.includes("to")))) {
            pathEl.setAttribute("marker-end", "url(#arrowhead_svgexport)");
            // Set arrowhead color to match edge stroke
            const clonedMarker = marker.cloneNode(true);
            clonedMarker.id = `arrowhead_svgexport_${edgeId}`; // Unique ID per edge for color
            clonedMarker.querySelector("path").setAttribute("fill", pathEl.getAttribute("stroke"));
            defs.appendChild(clonedMarker);
            pathEl.setAttribute("marker-end", `url(#${clonedMarker.id})`);
        }
        edgesGroup.appendChild(pathEl);
    });
    svg.appendChild(edgesGroup);

    // Draw Nodes
    const nodesGroup = document.createElementNS(svgNS, "g");
    nodesGroup.setAttribute("id", "nodes_svgexport");
    nodeIds.forEach(nodeId => {
        const node = window.network.body.nodes[nodeId];
        if (!node || node.options.hidden || !positions[nodeId]) return;

        const pos = positions[nodeId];
        const nodeOptions = node.options;
        const size = nodeOptions.size || 10; // 'size' in vis.js is roughly half the width/height for circle/dot

        // Basic filtering for nodes when cropping
        if (cropArea) {
            // Check if any part of the node's bounding box is within the cropArea
            const nodeMinX = pos.x - size;
            const nodeMaxX = pos.x + size;
            const nodeMinY = pos.y - size;
            const nodeMaxY = pos.y + size;

            if (nodeMaxX < cropArea.x || nodeMinX > cropArea.x + cropArea.width ||
                nodeMaxY < cropArea.y || nodeMinY > cropArea.y + cropArea.height) {
                return; // Node is entirely outside the crop area
            }
        }

        // Default shape: circle
        const shapeEl = document.createElementNS(svgNS, "circle");
        shapeEl.setAttribute("cx", pos.x.toString());
        shapeEl.setAttribute("cy", pos.y.toString());
        shapeEl.setAttribute("r", size.toString()); // 'size' is used as radius for 'dot' or 'circle'

        const fillColor = (nodeOptions.color && nodeOptions.color.background) || nodeOptions.color || "#97C2FC"; // Default vis.js node color
        const borderColor = (nodeOptions.color && nodeOptions.color.border) || "#2B7CE9"; // Default vis.js border color
        const borderWidth = nodeOptions.borderWidth || 1;

        shapeEl.setAttribute("fill", fillColor);
        shapeEl.setAttribute("stroke", borderColor);
        shapeEl.setAttribute("stroke-width", borderWidth.toString());
        nodesGroup.appendChild(shapeEl);

        // Draw Label
        if (nodeOptions.label && nodeOptions.font) {
            const textEl = document.createElementNS(svgNS, "text");
            textEl.setAttribute("x", pos.x.toString());
            textEl.setAttribute("y", pos.y.toString()); // Will be adjusted by dominant-baseline
            textEl.setAttribute("text-anchor", "middle");
            textEl.setAttribute("dominant-baseline", "central"); // Good for single line vertical centering
            textEl.setAttribute("font-family", nodeOptions.font.face || "arial");
            textEl.setAttribute("font-size", (nodeOptions.font.size || 14) + "px");
            textEl.setAttribute("fill", nodeOptions.font.color || "#343434");
            textEl.style.pointerEvents = "none"; // Labels should not block interaction

            const labelLines = String(nodeOptions.label).split(/\\n|\n|<br\s*\/?>/i); // Split by \n, \\n, or <br>
            if (labelLines.length > 1) {
                const fontSize = nodeOptions.font.size || 14;
                const lineHeight = (nodeOptions.font.vadjust || 0) + fontSize * 1.2; // Approximate line height
                const totalLabelHeight = lineHeight * labelLines.length;
                let startY = pos.y - totalLabelHeight / 2 + fontSize / 2 + (nodeOptions.font.vadjust || 0); // Center block of text

                labelLines.forEach((line, index) => {
                    const tspan = document.createElementNS(svgNS, "tspan");
                    tspan.setAttribute("x", pos.x.toString());
                    tspan.setAttribute("dy", (index === 0 ? startY - pos.y : lineHeight) + "px"); // dy is relative for subsequent lines
                    tspan.textContent = line;
                    textEl.appendChild(tspan);
                });
            } else {
                textEl.textContent = nodeOptions.label;
            }
            nodesGroup.appendChild(textEl);
        }
    });
    svg.appendChild(nodesGroup);

    console.log("SVG generation complete.");
    return new XMLSerializer().serializeToString(svg);
}

// --- PNG Export Function ---
async function exportToPNG(selection = null, qualityScaleFactor = 1.5) {
    const exportType = selection ? `selection (Scale: ${qualityScaleFactor})` : `full network (Scale: ${qualityScaleFactor})`;
    console.log(`PNG export started for ${exportType}...`);

    if (!window.network || !window.network.body) {
        console.error("Network not ready for PNG export.");
        alert("Error: Network not ready for PNG export.");
        return;
    }
    showLoadingOverlay(`Generating PNG for ${selection ? "selection" : "full network"}...`);

    try {
        const svgCropArea = selection ? {
            x: selection.x, y: selection.y,
            width: selection.width, height: selection.height
        } : null;

        const svgString = await generateNetworkSVG(svgCropArea);
        if (!svgString) throw new Error("SVG string generation failed.");

        const svgMatch = svgString.match(/<svg[^>]*width="([^"]+)"[^>]*height="([^"]+)"/);
        const viewBoxMatch = svgString.match(/<svg[^>]*viewBox="([^"]+)"/);

        let svgExportWidth, svgExportHeight;

        if (svgMatch && svgMatch[1] && svgMatch[2]) {
            svgExportWidth = parseFloat(svgMatch[1]);
            svgExportHeight = parseFloat(svgMatch[2]);
        } else if (viewBoxMatch && viewBoxMatch[1]) {
            const vbParts = viewBoxMatch[1].split(" ").map(Number);
            svgExportWidth = vbParts[2];
            svgExportHeight = vbParts[3];
        } else {
            throw new Error("Could not determine SVG dimensions for PNG export.");
        }


        if (svgExportWidth <= 0 || svgExportHeight <= 0) {
            throw new Error(`Invalid SVG dimensions for PNG export: ${svgExportWidth}x${svgExportHeight}`);
        }

        const dpr = window.devicePixelRatio || 1;
        const scale = dpr * qualityScaleFactor;
        const canvas = document.createElement("canvas");
        canvas.width = Math.max(1, Math.round(svgExportWidth * scale)); // Ensure canvas dimensions are at least 1x1
        canvas.height = Math.max(1, Math.round(svgExportHeight * scale));
        const ctx = canvas.getContext("2d");

        if (!ctx) throw new Error("Could not get 2D context from canvas.");

        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";

        // Get background color from the network container or canvas itself
        let bgColor = "#ffffff"; // Default background
        const networkContainer = document.getElementById("mynetwork");
        if (networkContainer) {
            const visCanvas = networkContainer.querySelector("canvas");
            if (visCanvas) {
                bgColor = window.getComputedStyle(visCanvas).backgroundColor;
            } else {
                bgColor = window.getComputedStyle(networkContainer).backgroundColor;
            }
        }
        // If bgColor is transparent or not set, default to white
        if (!bgColor || bgColor === "rgba(0, 0, 0, 0)" || bgColor === "transparent") {
            bgColor = "#ffffff";
        }


        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const img = new Image();
        // Use data URL for SVG source to ensure all styles and definitions are included
        const svgDataUrl = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svgString);

        await new Promise((resolve, reject) => {
            img.onload = () => {
                console.log("SVG loaded into image, drawing to PNG canvas...");
                try {
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    console.log("PNG Canvas drawing complete.");
                    resolve();
                } catch (drawError) {
                    console.error("Error drawing SVG to canvas for PNG:", drawError);
                    reject(new Error("Failed to draw SVG onto canvas. " + drawError.message));
                }
            };
            img.onerror = (errEvent) => {
                console.error("Error loading SVG into image for PNG export. Event:", errEvent, "SVG Data URL used:", svgDataUrl.substring(0, 100) + "...");
                reject(new Error("Failed to load SVG into image for PNG rendering. Check console for SVG data."));
            };
            img.src = svgDataUrl;
        });

        const link = document.createElement("a");
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        const fileNameSuffix = selection ? `_selection_${timestamp}` : `_full_${timestamp}`;
        link.download = `${baseFileName}${fileNameSuffix}.png`;
        link.href = canvas.toDataURL("image/png");
        link.click();

        console.log(`PNG export successful for ${exportType}.`);
    } catch (error) {
        console.error(`PNG export failed for ${exportType}:`, error);
        alert(`Error saving PNG (${exportType}): ${error.message}`);
    } finally {
        hideLoadingOverlay();
    }
}

// --- SVG Export Function (handles selection or full) ---
async function exportToSVG(selection = null) {
    const exportType = selection ? "selection" : "full network";
    console.log(`SVG export started for ${exportType}...`);
    if (!window.network || !window.network.body) {
        console.error("Network not ready for SVG export.");
        alert("Error: Network not ready for SVG export.");
        return;
    }
    showLoadingOverlay(`Generating SVG for ${selection ? "selection" : "full network"}...`);

    try {
        const svgCropArea = selection ? {
            x: selection.x, y: selection.y,
            width: selection.width, height: selection.height
        } : null;
        const svgString = await generateNetworkSVG(svgCropArea);
        if (!svgString) throw new Error("SVG string generation failed.");

        const blob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        const fileNameSuffix = selection ? `_selection_${timestamp}` : `_full_${timestamp}`;
        link.download = `${baseFileName}${fileNameSuffix}.svg`;
        link.click();

        setTimeout(() => URL.revokeObjectURL(link.href), 100); // Cleanup blob URL

        console.log(`SVG export successful for ${exportType}.`);
    } catch (error) {
        console.error(`SVG export failed for ${exportType}:`, error);
        alert(`Error saving SVG (${exportType}): ${error.message}`);
    } finally {
        hideLoadingOverlay();
    }
}

// --- Functions to trigger FULL network exports from UI (e.g. buttons) ---
function saveFullNetworkPNG(qualityScaleFactor = 1.5) {
    // Potentially get scale factor from a UI element if desired
    // const scaleInput = document.getElementById('pngScaleFactor');
    // const scale = scaleInput ? parseFloat(scaleInput.value) : 1.5;
    exportToPNG(null, qualityScaleFactor);
}

function saveFullNetworkSVG() {
    exportToSVG(null);
}
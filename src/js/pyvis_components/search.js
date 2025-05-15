// src/js/pyvis_components/search.js

function initializeSearch() {
    // Ensure DOM elements are referenced (they might be set in init.js or panels.js)
    searchInput = searchInput || document.getElementById("searchInput");
    searchResultCount = searchResultCount || document.getElementById("searchResultCount");
    searchStatus = searchStatus || document.getElementById("searchStatus");
    prevSearchResultBtn = prevSearchResultBtn || document.getElementById("prevSearchResult");
    nextSearchResultBtn = nextSearchResultBtn || document.getElementById("nextSearchResult");

    if (!searchInput) {
        console.warn("Search input not found for initialization.");
        return;
    }

    // Set up event listeners for search input only once
    if (!searchInput.dataset.initialized) {
        searchInput.addEventListener("keyup", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                if (e.shiftKey) {
                    navigateSearchResult(-1); // Shift+Enter = Previous
                } else {
                    navigateSearchResult(1); // Enter = Next
                }
                return;
            }

            if (e.key === "Escape") {
                closeSearchPanel();
                return;
            }

            // For other keys, update search
            const query = searchInput.value.trim();
            if (query !== currentSearchQuery) {
                performSearch(query);
            }
        });
        searchInput.dataset.initialized = "true"; // Mark as initialized
    }

    // Initialize Fuse.js if not already done
    initializeSearchEngine();
}

function initializeSearchEngine() {
    if (window.network && window.network.body && !searchFuseInstance) {
        const nodes = window.network.body.data.nodes.get() || [];
        if (!nodes.length) {
            if (searchStatus) searchStatus.textContent = "No nodes available for search.";
            return;
        }

        if (typeof Fuse === "undefined") {
            console.warn("Fuse.js library not loaded. Search will not be available.");
            if (searchStatus) searchStatus.textContent = "Search library not loaded.";
            // Attempt to load Fuse.js if it was missed
            const fusejsScript = document.createElement("script");
            fusejsScript.src = "https://cdn.jsdelivr.net/npm/fuse.js@7.1.0";
            fusejsScript.onload = () => {
                console.log("Fuse.js library loaded dynamically by search module.");
                createFuseInstance(nodes);
                if (searchInput && searchInput.value.trim()) { // If there was a query, re-run search
                    performSearch(searchInput.value.trim());
                }
            };
            fusejsScript.onerror = (err) => {
                console.error("Failed to load Fuse.js dynamically:", err);
                if (searchStatus) searchStatus.textContent = "Search engine failed to load.";
            };
            document.head.appendChild(fusejsScript);
            return; // Exit, will be re-attempted on script load
        }
        createFuseInstance(nodes);
    }
}

function createFuseInstance(nodes) {
    const searchableNodes = nodes.map((node) => {
        const fullDetails = extractInfoFromTooltip(node.title || "");
        return {
            id: node.id,
            label: node.label || node.id.toString(), // Ensure label is a string
            ...fullDetails,
        };
    });

    searchFuseInstance = new Fuse(searchableNodes, {
        keys: ["label", "fullName", "type", "database"],
        includeScore: true,
        threshold: 0.4, // Default fuzzy
        ignoreLocation: true,
        useExtendedSearch: true, // Allows for more complex queries if needed later
    });

    if (searchStatus) searchStatus.textContent = "Search engine ready.";
    console.log("Fuse.js instance created with " + searchableNodes.length + " nodes.");
}

function extractInfoFromTooltip(tooltipHtml) {
    const info = {
        fullName: "",
        type: "unknown",
        database: "",
        connections: 0,
    };

    if (!tooltipHtml || typeof tooltipHtml !== 'string') return info;

    try {
        const lines = tooltipHtml.split(/\\n|<br\s*\/?>/i); // Split by \n or <br>

        if (lines.length > 0) {
            info.fullName = lines[0].trim();
        }

        const typeMatch = tooltipHtml.match(/Type:\s*([^<\n\\]+)/i);
        if (typeMatch && typeMatch[1]) {
            info.type = typeMatch[1].trim();
        }

        const dbMatch = tooltipHtml.match(/Database:\s*([^<\n\\]+)/i);
        if (dbMatch && dbMatch[1]) {
            info.database = dbMatch[1].trim();
            if (info.database.toLowerCase() === "(default)") {
                info.database = "default";
            }
        }

        const conMatch = tooltipHtml.match(/Connections:\s*(\d+)/i);
        if (conMatch && conMatch[1]) {
            info.connections = parseInt(conMatch[1].trim(), 10);
        }
    } catch (e) {
        console.warn("Error parsing tooltip data for search:", e, "Input HTML:", tooltipHtml);
    }
    return info;
}

function performSearch(query) {
    currentSearchQuery = query;
    currentSearchResults = [];
    currentSearchResultIndex = -1;

    resetSearchHighlights(); // Clear previous highlights
    updateSearchResultUI();

    if (!query) {
        if (searchStatus) searchStatus.textContent = "Enter a search term.";
        return;
    }

    if (!window.network || !window.network.body) {
        if (searchStatus) searchStatus.textContent = "Network not ready for search.";
        return;
    }

    if (!searchFuseInstance) {
        initializeSearchEngine(); // Attempt to initialize if not ready
        if (!searchFuseInstance) {
            if (searchStatus) searchStatus.textContent = "Search engine initializing...";
            // Optionally, queue the search or try again after a short delay
            setTimeout(() => performSearch(query), 500);
            return;
        }
    }

    const isCaseSensitive = document.getElementById("searchCaseSensitive")?.checked || false;
    const isFuzzy = document.getElementById("searchFuzzy")?.checked ?? true; // Default to fuzzy

    const fuseOptions = {
        threshold: isFuzzy ? 0.4 : 0.0, // 0.0 for exact match
        ignoreCase: !isCaseSensitive, // Fuse's ignoreCase is true by default
    };

    const results = searchFuseInstance.search(query, fuseOptions);
    currentSearchResults = results.map((result) => result.item.id);

    if (currentSearchResults.length > 0) {
        currentSearchResultIndex = 0;
        highlightSearchResults();
        focusOnCurrentResult();
    } else {
        if (searchStatus) searchStatus.textContent = `No matches found for "${query}"`;
    }
    updateSearchResultUI();
}

function updateSearchResultUI() {
    if (searchResultCount) {
        if (!currentSearchQuery || currentSearchResults.length === 0) {
            searchResultCount.textContent = currentSearchQuery ? "0 results" : "";
        } else {
            searchResultCount.textContent = `${currentSearchResultIndex + 1} of ${currentSearchResults.length
                } results`;
        }
    }

    if (prevSearchResultBtn) {
        prevSearchResultBtn.disabled =
            currentSearchResults.length === 0 || currentSearchResultIndex <= 0;
    }
    if (nextSearchResultBtn) {
        nextSearchResultBtn.disabled =
            currentSearchResults.length === 0 ||
            currentSearchResultIndex >= currentSearchResults.length - 1;
    }
}

function navigateSearchResult(direction) {
    if (currentSearchResults.length === 0) return;

    let newIndex = currentSearchResultIndex + direction;

    if (newIndex < 0) {
        newIndex = currentSearchResults.length - 1; // Wrap to last
    } else if (newIndex >= currentSearchResults.length) {
        newIndex = 0; // Wrap to first
    }

    currentSearchResultIndex = newIndex;

    highlightSearchResults(); // Re-highlight to update current selection style
    updateSearchResultUI();
    focusOnCurrentResult();
}

function focusOnCurrentResult() {
    if (currentSearchResults.length === 0 || currentSearchResultIndex < 0 || !window.network) return;

    const nodeId = currentSearchResults[currentSearchResultIndex];
    if (!nodeId) return;

    const options = {
        scale: window.network.getScale() > 1.5 ? window.network.getScale() : 1.5, // Zoom in, but not too much if already zoomed
        offset: { x: 0, y: 0 },
        animation: {
            duration: 500,
            easingFunction: "easeInOutQuad",
        },
    };

    try {
        window.network.focus(nodeId, options);
        window.network.selectNodes([nodeId], { highlightEdges: false });
    } catch (e) {
        console.warn("Error focusing on node:", nodeId, e);
    }
}

function highlightSearchResults() {
    if (!window.network || !window.network.body) return;

    resetSearchHighlights(); // Start fresh

    if (currentSearchResults.length === 0) {
        return;
    }

    const shouldHighlightAll = document.getElementById("searchHighlightAll")?.checked || false;
    const shouldDimOthers = document.getElementById("searchDimOthers")?.checked || false;

    const allNodeIdsInNetwork = Object.keys(window.network.body.nodes); // More robust way to get all node IDs

        if (shouldDimOthers) {
            const nodesToUpdate = allNodeIdsInNetwork.map(id => {
                if (!currentSearchResults.includes(id)) {
                    return { id: id, opacity: 0.25 };
                }
                return null; // Will be filtered out
            }).filter(n => n);
            if (nodesToUpdate.length > 0) {
                // Apply opacity changes without triggering stabilization
                nodesToUpdate.forEach(update => {
                    const nodeObj = window.network.body.nodes[update.id];
                    if (nodeObj) {
                        nodeObj.setOptions({ opacity: update.opacity });
                    }
                });
                window.network.redraw();
            }
        }

    let nodesToHighlight = [];
    if (shouldHighlightAll) {
        nodesToHighlight = currentSearchResults.map(nodeId => {
            const isCurrent = nodeId === currentSearchResults[currentSearchResultIndex];
            return {
                id: nodeId,
                borderWidth: isCurrent ? 4 : 3, // Make current slightly thicker
                borderColor: isCurrent ? "#e91e63" : "#ff5722", // Pink for current, Orange for others
                opacity: 1.0, // Ensure highlighted are fully opaque
            };
        });
    } else if (currentSearchResultIndex !== -1) {
        // Only highlight the current result
        const nodeId = currentSearchResults[currentSearchResultIndex];
        if (nodeId) {
            nodesToHighlight.push({
                id: nodeId,
                borderWidth: 4,
                borderColor: "#e91e63", // Pink
                opacity: 1.0,
            });
        }
    }
    if (nodesToHighlight.length > 0) {
        // Apply highlight changes without triggering stabilization
        nodesToHighlight.forEach(update => {
            const nodeObj = window.network.body.nodes[update.id];
            if (nodeObj) {
                nodeObj.setOptions({
                    borderWidth: update.borderWidth,
                    borderColor: update.borderColor,
                    opacity: update.opacity
                });
            }
        });
        window.network.redraw();
    }
    // No need to call network.redraw() explicitly if using dataset.update()
}

function resetSearchHighlights() {
    if (!window.network || !window.network.body || !window.network.body.data.nodes) return;

    const allNodeIdsInNetwork = Object.keys(window.network.body.nodes);
    if (allNodeIdsInNetwork.length === 0) return;

    // Get default options to reset to. This is a bit tricky as individual nodes might have their own defaults.
    // For simplicity, we reset to the global defaults or clear specific overrides.
    const nodesToResetObjects = allNodeIdsInNetwork
        .map(nodeId => window.network.body.nodes[nodeId])
        .filter(node => node && (node.options.borderColor === "#e91e63" || node.options.borderColor === "#ff5722" || node.options.opacity < 1.0));
    
    if (nodesToResetObjects.length > 0) {
        nodesToResetObjects.forEach(node => {
            node.setOptions({
                borderWidth: undefined,
                borderColor: undefined,
                opacity: undefined,
            });
        });
        window.network.redraw();
    }

    if (searchStatus && currentSearchQuery) searchStatus.textContent = `Found ${currentSearchResults.length} results for "${currentSearchQuery}"`;
    else if (searchStatus) searchStatus.textContent = "";
}

function clearSearch() {
    if (searchInput) {
        searchInput.value = "";
    }
    currentSearchQuery = "";
    const hadResults = currentSearchResults.length > 0;
    currentSearchResults = [];
    currentSearchResultIndex = -1;

    if (hadResults) { // Only reset highlights if there were any
        resetSearchHighlights();
    }

    updateSearchResultUI();
    if (searchStatus) searchStatus.textContent = "";

    if (window.network) {
        window.network.unselectAll();
    }
}

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
        // Clear any existing timeout
        let searchTimeout;
        
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

            // For other keys, debounce the search
            const query = searchInput.value.trim();
            if (query !== currentSearchQuery) {
                // Clear previous timeout
                if (searchTimeout) {
                    clearTimeout(searchTimeout);
                }
                
                // Set new timeout for debounced search
                searchTimeout = setTimeout(() => {
                    performSearch(query);
                }, 300); // 300ms debounce delay
            }
        });
        
        // Also add input event for immediate feedback on certain keys
        searchInput.addEventListener("input", function (e) {
            const query = searchInput.value.trim();
            
            // Clear search immediately if input is empty
            if (!query && currentSearchQuery) {
                clearTimeout(searchTimeout);
                performSearch("");
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
        const baseLabel = node.label || node.id.toString();
        
        return {
            id: node.id,
            label: baseLabel,
            normalizedLabel: normalizeSearchText(baseLabel),
            searchVariants: createSearchVariants(baseLabel),
            ...fullDetails,
            normalizedFullName: normalizeSearchText(fullDetails.fullName || ""),
            normalizedType: normalizeSearchText(fullDetails.type || ""),
            normalizedDatabase: normalizeSearchText(fullDetails.database || ""),
        };
    });

    searchFuseInstance = new Fuse(searchableNodes, {
        keys: [
            { name: "label", weight: 1.0 },
            { name: "normalizedLabel", weight: 0.9 },
            { name: "searchVariants", weight: 0.8 },
            { name: "fullName", weight: 0.9 },
            { name: "normalizedFullName", weight: 0.8 },
            { name: "type", weight: 0.6 },
            { name: "normalizedType", weight: 0.5 },
            { name: "database", weight: 0.5 },
            { name: "normalizedDatabase", weight: 0.4 },
        ],
        includeScore: true,
        threshold: 0.3, // More lenient for better fuzzy matching
        ignoreLocation: true,
        useExtendedSearch: true,
        ignoreFieldNorm: true, // Ignore field length normalization for better scoring
        fieldNormWeight: 0.2, // Reduce field length impact
        minMatchCharLength: 1, // Allow single character matches
        shouldSort: true,
        sortFn: (a, b) => {
            // Custom sorting: prioritize lower scores (better matches)
            // But also consider exact matches and special character matches
            const scoreA = a.score || 0;
            const scoreB = b.score || 0;
            
            // If scores are very close, prefer shorter matches
            if (Math.abs(scoreA - scoreB) < 0.1) {
                const lenA = a.item.label?.length || 0;
                const lenB = b.item.label?.length || 0;
                return lenA - lenB;
            }
            
            return scoreA - scoreB;
        }
    });

    if (searchStatus) searchStatus.textContent = "Search engine ready.";
    console.log("Enhanced Fuse.js instance created with " + searchableNodes.length + " nodes.");
}

// Utility function to normalize search text for better fuzzy matching
function normalizeSearchText(text) {
    if (!text || typeof text !== 'string') return "";
    
    return text
        .toLowerCase()
        .trim()
        // Replace special characters with spaces for normalization
        .replace(/[_\-@\.]/g, ' ')
        // Remove multiple spaces
        .replace(/\s+/g, ' ')
        .trim();
}

// Create search variants for better matching
function createSearchVariants(text) {
    if (!text || typeof text !== 'string') return [];
    
    const variants = [];
    const baseText = text.trim();
    
    // Original text
    variants.push(baseText);
    
    // Lowercase version
    variants.push(baseText.toLowerCase());
    
    // Version with special characters replaced by spaces
    variants.push(baseText.replace(/[_\-@\.]/g, ' '));
    
    // Version with special characters removed
    variants.push(baseText.replace(/[_\-@\.\s]/g, ''));
    
    // Version with underscores and dashes as spaces
    variants.push(baseText.replace(/[_\-]/g, ' '));
    
    // Mixed separator versions for common patterns
    if (baseText.includes('_')) {
        variants.push(baseText.replace(/_/g, '-'));
        variants.push(baseText.replace(/_/g, '.'));
        variants.push(baseText.replace(/_/g, '@'));
    }
    
    if (baseText.includes('-')) {
        variants.push(baseText.replace(/-/g, '_'));
        variants.push(baseText.replace(/-/g, '.'));
        variants.push(baseText.replace(/-/g, '@'));
    }
    
    if (baseText.includes('.')) {
        variants.push(baseText.replace(/\./g, '_'));
        variants.push(baseText.replace(/\./g, '-'));
        variants.push(baseText.replace(/\./g, '@'));
    }
    
    // Remove duplicates and empty strings
    return [...new Set(variants)].filter(v => v && v.length > 0);
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

    // Enhanced search with better fuzzy options
    const searchOptions = {
        threshold: isFuzzy ? 0.3 : 0.0, // More lenient threshold for fuzzy search
        ignoreCase: !isCaseSensitive,
        includeScore: true,
        findAllMatches: true, // Find all matches, not just the first
        minMatchCharLength: 1,
        shouldSort: true,
        location: 0, // Start search from beginning
        distance: 100, // How far from location to search
    };

    // Create multiple search queries for better matching
    const searchQueries = [query];
    
    // Add normalized version of the query
    const normalizedQuery = normalizeSearchText(query);
    if (normalizedQuery !== query.toLowerCase()) {
        searchQueries.push(normalizedQuery);
    }
    
    // Add variants of the query
    const queryVariants = createSearchVariants(query);
    searchQueries.push(...queryVariants.slice(0, 3)); // Limit to top 3 variants to avoid performance issues

    // Perform searches and combine results
    let allResults = [];
    const uniqueIds = new Set();

    for (const searchQuery of searchQueries) {
        if (!searchQuery || searchQuery.length === 0) continue;
        
        const results = searchFuseInstance.search(searchQuery, searchOptions);
        
        // Add results that haven't been seen yet
        results.forEach(result => {
            if (!uniqueIds.has(result.item.id)) {
                uniqueIds.add(result.item.id);
                allResults.push(result);
            }
        });
    }

    // Sort results by score (lower is better) and relevance
    allResults.sort((a, b) => {
        const scoreA = a.score || 0;
        const scoreB = b.score || 0;
        
        // Prefer exact matches
        if (scoreA === 0 && scoreB > 0) return -1;
        if (scoreB === 0 && scoreA > 0) return 1;
        
        // Then by score
        if (Math.abs(scoreA - scoreB) > 0.1) {
            return scoreA - scoreB;
        }
        
        // If scores are close, prefer shorter labels
        const lenA = a.item.label?.length || 0;
        const lenB = b.item.label?.length || 0;
        return lenA - lenB;
    });

    currentSearchResults = allResults.map(result => result.item.id);

    if (currentSearchResults.length > 0) {
        currentSearchResultIndex = 0;
        highlightSearchResults();
        focusOnCurrentResult();
        if (searchStatus) {
            const exactMatches = allResults.filter(r => (r.score || 0) === 0).length;
            const statusText = exactMatches > 0 
                ? `Found ${currentSearchResults.length} results (${exactMatches} exact) for "${query}"`
                : `Found ${currentSearchResults.length} results for "${query}"`;
            searchStatus.textContent = statusText;
        }
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

    try {
        // Get current network state
        const currentScale = window.network.getScale();
        const viewPosition = window.network.getViewPosition();
        
        // Calculate optimal zoom level based on network density and current zoom
        const optimalScale = calculateOptimalZoom(currentScale, nodeId);
        
        // Get node position for perfect centering
        const nodePosition = window.network.getPositions([nodeId])[nodeId];
        if (!nodePosition) {
            console.warn("Node position not found for:", nodeId);
            return;
        }

        // Enhanced focus options for smooth centering
        const focusOptions = {
            scale: optimalScale,
            offset: { x: 0, y: 0 }, // Perfect center
            animation: {
                duration: 600, // Slightly longer for smoother feel
                easingFunction: "easeInOutCubic", // Smoother easing
            },
        };

        // Focus on the node with enhanced centering
        window.network.focus(nodeId, focusOptions);
        
        // Select the node with visual feedback
        window.network.selectNodes([nodeId], { 
            highlightEdges: false,
            unselectAll: true // Clear any previous selections
        });

        // Add a slight delay before final positioning to ensure smooth animation
        setTimeout(() => {
            try {
                // Ensure the node is perfectly centered after animation
                const currentViewPos = window.network.getViewPosition();
                const canvasSize = window.network.body.view.canvas.frame.canvas;
                const centerX = canvasSize.width / 2;
                const centerY = canvasSize.height / 2;
                
                // Fine-tune position if needed (only if significantly off-center)
                const screenPos = window.network.canvasToDOM(nodePosition);
                const offsetX = centerX - screenPos.x;
                const offsetY = centerY - screenPos.y;
                
                if (Math.abs(offsetX) > 10 || Math.abs(offsetY) > 10) {
                    window.network.moveTo({
                        position: {
                            x: currentViewPos.x - offsetX / currentScale,
                            y: currentViewPos.y - offsetY / currentScale
                        },
                        scale: currentScale,
                        animation: {
                            duration: 200,
                            easingFunction: "easeOutQuad"
                        }
                    });
                }
            } catch (e) {
                // Ignore fine-tuning errors, main focus should have worked
                console.debug("Fine-tuning focus position failed:", e);
            }
        }, 650); // After main animation completes

    } catch (e) {
        console.warn("Error focusing on node:", nodeId, e);
        
        // Fallback to basic focus if enhanced version fails
        try {
            window.network.focus(nodeId, {
                scale: 1.5,
                animation: { duration: 500 }
            });
            window.network.selectNodes([nodeId]);
        } catch (fallbackError) {
            console.error("Fallback focus also failed:", fallbackError);
        }
    }
}

// Calculate optimal zoom level for focusing on a node
function calculateOptimalZoom(currentScale, nodeId) {
    try {
        // Get network statistics for intelligent zooming
        const nodes = window.network.body.data.nodes.get();
        const edges = window.network.body.data.edges.get();
        
        if (!nodes || nodes.length === 0) return Math.max(currentScale, 1.5);
        
        // Calculate network density
        const nodeCount = nodes.length;
        const edgeCount = edges ? edges.length : 0;
        const density = nodeCount > 1 ? edgeCount / (nodeCount * (nodeCount - 1)) : 0;
        
        // Get canvas size
        const canvas = window.network.body.view.canvas.frame.canvas;
        const canvasArea = canvas.width * canvas.height;
        
        // Base zoom calculation
        let targetScale = currentScale;
        
        // For dense networks, zoom in more to focus on the specific area
        if (density > 0.1) {
            targetScale = Math.max(2.0, currentScale * 1.2);
        } else if (density > 0.05) {
            targetScale = Math.max(1.8, currentScale * 1.1);
        } else {
            targetScale = Math.max(1.5, currentScale);
        }
        
        // Adjust based on canvas size - smaller screens need more zoom
        if (canvasArea < 500000) { // Small screen
            targetScale *= 1.2;
        } else if (canvasArea > 2000000) { // Large screen
            targetScale *= 0.9;
        }
        
        // Cap the zoom levels for usability
        targetScale = Math.min(Math.max(targetScale, 1.0), 4.0);
        
        return targetScale;
        
    } catch (e) {
        console.warn("Error calculating optimal zoom:", e);
        return Math.max(currentScale, 1.5); // Safe fallback
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

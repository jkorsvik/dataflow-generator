// Pyvis custom JavaScript extracted from pyvis_mod.py
// Placeholders: %%INITIAL_NETWORK_OPTIONS%%, %%BASE_FILE_NAME%%

const initialNetworkOptions = "%%INITIAL_NETWORK_OPTIONS%%";
const baseFileName = "%%BASE_FILE_NAME%%";

// ...rest of the JavaScript logic from the custom_js variable in pyvis_mod.py...
// (You will need to copy the full JavaScript logic here, replacing dynamic values with the placeholders above)

let isPanelExpanded = false;
const panelWidth = 300; // Match CSS
let loadingTimeout = null; // For fallback hide timer

// --- Selection State Variables ---
let isSelecting = false;
let selectionStartX = 0;
let selectionStartY = 0;
let selectionRect = { x: 0, y: 0, width: 0, height: 0 }; // Store selection rect relative to overlay
let selectionCanvasCoords = null; // To store converted canvas coordinates

// --- DOM Elements ---
let selectionOverlay = null;
let selectionRectangle = null;
let exportChoiceModal = null;

// --- Search Variables ---
let searchPanel = null;
let searchInput = null;
let searchResultCount = null;
let searchStatus = null;
let prevSearchResultBtn = null;
let nextSearchResultBtn = null;
let currentSearchQuery = "";
let currentSearchResults = [];
let currentSearchResultIndex = -1;
let searchFuseInstance = null;
let isSearchPanelOpen = false;

// --- Function to hide loading bar ---
function hideLoadingBar() {
  const loadingBar = document.getElementById("loadingBar");
  if (loadingBar) {
    loadingBar.style.display = "none";
    console.log("Loading bar hidden by timer");
  }
}

// Set up a recurring timer to hide the loading bar every 10 seconds
setInterval(hideLoadingBar, 10000);

// Also hide it when it reaches 100%
function setupLoadingBarObserver() {
  // Find the loading bar element
  const loadingBar = document.getElementById("loadingBar");
  if (!loadingBar) {
    console.warn("Loading bar element not found");
    return;
  }

  // Setup mutation observer to watch for text content or style changes
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      // Check if the loading bar text is 100%
      const textElement = loadingBar.querySelector("#text");
      const bar = loadingBar.querySelector("#bar");

      if (
        (textElement && textElement.textContent === "100%") ||
        (bar && bar.style.width === "100%")
      ) {
        hideLoadingBar();
      }
    });
  });

  // Observe both attribute changes and child content
  observer.observe(loadingBar, {
    attributes: true,
    childList: true,
    subtree: true,
    attributeFilter: ["style"],
  });

  console.log("Loading bar observer set up");

  // Hide loading bar immediately to start
  hideLoadingBar();
}

// --- Loading Overlay Functions ---
function showLoadingOverlay() {
  const overlay = document.getElementById("loadingOverlay");
  if (overlay) {
    overlay.style.display = "flex";
  }
  clearTimeout(loadingTimeout);
  loadingTimeout = setTimeout(hideLoadingOverlay, 15000); // Increase safety timeout to 15s
  console.log("Loading overlay shown.");
}
function hideLoadingOverlay() {
  clearTimeout(loadingTimeout);
  const overlay = document.getElementById("loadingOverlay");
  if (overlay) {
    overlay.style.display = "none";
  }
  console.log("Loading overlay hidden.");
}

// --- Panel Toggle ---
function togglePanel() {
  const panel = document.getElementById("controlPanel");
  const networkContainer = document.getElementById("mynetwork");

  if (!panel) {
    console.error("Control panel element not found");
    return;
  }

  isPanelExpanded = !isPanelExpanded;
  panel.classList.toggle("expanded");

  if (networkContainer) {
    networkContainer.style.right = isPanelExpanded ? panelWidth + "px" : "0px";
  }

  // No need to update icon classes as we're now using the hamburger-icon spans
  // that are styled with CSS based on the panel's expanded state
}

// --- Search Panel Toggle ---
function toggleSearchPanel() {
  searchPanel = document.getElementById("searchPanel");
  if (!searchPanel) return;

  isSearchPanelOpen = !isSearchPanelOpen;
  searchPanel.classList.toggle("expanded", isSearchPanelOpen);

  if (isSearchPanelOpen) {
    // Focus the search input
    searchInput = document.getElementById("searchInput");
    if (searchInput) {
      searchInput.focus();
      initializeSearch();
    }
  } else {
    // Clear search when closing
    clearSearch();
  }
}

function closeSearchPanel() {
  searchPanel = document.getElementById("searchPanel");
  if (!searchPanel) return;

  searchPanel.classList.remove("expanded");
  isSearchPanelOpen = false;

  // Clear highlights when closing
  clearSearch();
}

function initializeSearch() {
  if (!searchInput) {
    searchInput = document.getElementById("searchInput");
  }

  if (!searchResultCount) {
    searchResultCount = document.getElementById("searchResultCount");
  }

  if (!searchStatus) {
    searchStatus = document.getElementById("searchStatus");
  }

  if (!prevSearchResultBtn) {
    prevSearchResultBtn = document.getElementById("prevSearchResult");
  }

  if (!nextSearchResultBtn) {
    nextSearchResultBtn = document.getElementById("nextSearchResult");
  }

  // Set up event listeners for search input
  if (searchInput && !searchInput.onkeyup) {
    searchInput.addEventListener("keyup", function (e) {
      // Check for special key events (Enter, Escape)
      if (e.key === "Enter") {
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
  }

  // Initialize Fuse.js if not already done
  initializeSearchEngine();
}

function initializeSearchEngine() {
  // Only initialize if network is ready and we don't already have an instance
  if (network && network.body && !searchFuseInstance) {
    const nodes = network.body.data.nodes.get() || [];
    if (!nodes.length) {
      if (searchStatus)
        searchStatus.textContent = "No nodes available for search.";
      return;
    }

    // Load Fuse.js if not already loaded
    if (typeof Fuse === "undefined") {
      const fusejsScript = document.createElement("script");
      fusejsScript.src = "https://cdn.jsdelivr.net/npm/fuse.js@7.1.0";
      fusejsScript.onload = () => {
        console.log("Fuse.js library loaded");
        createFuseInstance(nodes);
      };
      fusejsScript.onerror = (err) => {
        console.error("Failed to load Fuse.js:", err);
        if (searchStatus)
          searchStatus.textContent = "Search engine failed to load.";
      };
      document.head.appendChild(fusejsScript);
    } else {
      createFuseInstance(nodes);
    }
  }
}

function createFuseInstance(nodes) {
  // Transform nodes for better searching
  const searchableNodes = nodes.map((node) => {
    // Get tooltip data (to extract database, type info)
    const fullDetails = extractInfoFromTooltip(node.title || "");
    return {
      id: node.id,
      label: node.label || node.id,
      ...fullDetails,
    };
  });

  // Create Fuse instance with appropriate options
  searchFuseInstance = new Fuse(searchableNodes, {
    keys: ["label", "fullName", "type", "database"],
    includeScore: true,
    threshold: 0.4,
    ignoreLocation: true,
    useExtendedSearch: true,
  });

  if (searchStatus) searchStatus.textContent = "Search engine ready.";
}

function extractInfoFromTooltip(tooltipHtml) {
  // Parse tooltip content to extract useful info
  // This handles tooltip format from our node generation
  const info = {
    fullName: "",
    type: "unknown",
    database: "",
    connections: 0,
  };

  if (!tooltipHtml) return info;

  try {
    // Split by newlines to extract the different sections
    const lines = tooltipHtml.split("\\n");

    // First line should be full name
    if (lines.length > 0) {
      info.fullName = lines[0].trim();
    }

    // Try to match Type
    const typeMatch = tooltipHtml.match(/Type: ([^\\n]+)/i);
    if (typeMatch && typeMatch[1]) {
      info.type = typeMatch[1].trim();
    }

    // Try to match Database
    const dbMatch = tooltipHtml.match(/Database: ([^\\n]+)/i);
    if (dbMatch && dbMatch[1]) {
      info.database = dbMatch[1].trim();
      // Handle "(default)" placeholder
      if (info.database === "(default)") {
        info.database = "default";
      }
    }

    // Try to match Connections count
    const conMatch = tooltipHtml.match(/Connections: (\\d+)/i);
    if (conMatch && conMatch[1]) {
      info.connections = parseInt(conMatch[1].trim(), 10);
    }
  } catch (e) {
    console.warn("Error parsing tooltip data:", e);
  }

  return info;
}

function performSearch(query) {
  currentSearchQuery = query;

  // Clear previous results
  currentSearchResults = [];
  currentSearchResultIndex = -1;

  // Reset UI initially
  resetSearchHighlights();
  updateSearchResultUI();

  // If query is empty, just clear everything
  if (!query) {
    return;
  }

  if (!network || !network.body) {
    if (searchStatus)
      searchStatus.textContent = "Network not ready for search.";
    return;
  }

  // Initialize search engine if needed
  if (!searchFuseInstance) {
    initializeSearchEngine();
    // If it's still not available, show error message
    if (!searchFuseInstance) {
      if (searchStatus)
        searchStatus.textContent = "Search engine initializing...";
      return;
    }
  }

  // Get search options from UI
  const isCaseSensitive =
    document.getElementById("searchCaseSensitive")?.checked || false;
  const isFuzzy = document.getElementById("searchFuzzy")?.checked || false;

  // Adjust Fuse.js search options based on UI settings
  const searchOptions = {};
  if (!isFuzzy) {
    // For exact matching
    searchOptions.threshold = 0.0;
  } else {
    // For fuzzy matching
    searchOptions.threshold = 0.4;
  }

  if (isCaseSensitive) {
    searchOptions.ignoreCase = false;
  } else {
    searchOptions.ignoreCase = true;
  }

  // Perform search with Fuse
  const searchResults = searchFuseInstance.search(query, searchOptions);
  currentSearchResults = searchResults.map((result) => result.item.id);

  // Update UI with results
  if (currentSearchResults.length > 0) {
    currentSearchResultIndex = 0; // Start with first result
    highlightSearchResults();
    updateSearchResultUI();
    focusOnCurrentResult();
  } else {
    if (searchStatus) searchStatus.textContent = "No matches found for {query}";
  }
}

function updateSearchResultUI() {
  if (searchResultCount) {
    if (currentSearchResults.length === 0) {
      searchResultCount.textContent = "0 results";
    } else {
      searchResultCount.textContent = `${currentSearchResultIndex + 1} of ${
        currentSearchResults.length
      } results`;
    }
  }

  // Update navigation buttons
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

  // Calculate new index, wrap around if needed
  let newIndex = currentSearchResultIndex + direction;

  if (newIndex < 0) {
    newIndex = currentSearchResults.length - 1;
  } else if (newIndex >= currentSearchResults.length) {
    newIndex = 0;
  }

  currentSearchResultIndex = newIndex;

  // Highlight current result in a different color
  highlightSearchResults();
  updateSearchResultUI();
  focusOnCurrentResult();
}

function focusOnCurrentResult() {
  if (currentSearchResults.length === 0 || currentSearchResultIndex < 0) return;

  const nodeId = currentSearchResults[currentSearchResultIndex];

  // Get network options
  const options = {
    scale: 1.2,
    offset: { x: 0, y: 0 },
    animation: {
      duration: 500,
      easingFunction: "easeInOutQuad",
    },
  };

  // Focus/zoom on the node
  network.focus(nodeId, options);

  // Select the node
  network.selectNodes([nodeId]);
}

function highlightSearchResults() {
  if (!network || !network.body) return;

  // Reset all node appearances
  resetSearchHighlights();

  // Get search options
  const shouldHighlightAll =
    document.getElementById("searchHighlightAll")?.checked || false;
  const shouldDimOthers =
    document.getElementById("searchDimOthers")?.checked || false;

  if (currentSearchResults.length === 0) {
    return; // Nothing to highlight
  }

  // Get all nodes for dimming (if needed)
  const nodeIds = network.body.nodeIndices;

  // First handle dimming all non-matching nodes
  if (shouldDimOthers) {
    for (const nodeId of nodeIds) {
      if (!currentSearchResults.includes(nodeId)) {
        const node = network.body.nodes[nodeId];
        node.setOptions({ opacity: 0.25 }); // Make non-matching nodes transparent
      }
    }
  }

  // Highlight matching nodes
  if (shouldHighlightAll) {
    // Highlight all matching results
    for (const nodeId of currentSearchResults) {
      const node = network.body.nodes[nodeId];
      if (node) {
        const isCurrentResult =
          nodeId === currentSearchResults[currentSearchResultIndex];
        const borderWidth = isCurrentResult ? 3 : 2;
        const borderColor = isCurrentResult ? "#e91e63" : "#ff5722"; // Current = pink, others = orange
        node.setOptions({
          borderWidth: borderWidth,
          borderColor: borderColor,
          opacity: 1.0, // Ensure visible even if dimming is on
        });
      }
    }
  } else {
    // Only highlight current result
    const nodeId = currentSearchResults[currentSearchResultIndex];
    const node = network.body.nodes[nodeId];
    if (node) {
      node.setOptions({
        borderWidth: 3,
        borderColor: "#e91e63", // Pink
        opacity: 1.0,
      });
    }
  }

  // Redraw network to show highlights
  network.redraw();
}

function resetSearchHighlights() {
  if (!network || !network.body) return;

  // Reset node appearances to original
  const nodeIds = network.body.nodeIndices;
  for (const nodeId of nodeIds) {
    const node = network.body.nodes[nodeId];
    if (node) {
      node.setOptions({
        borderWidth: undefined, // Reset to default from options
        borderColor: undefined, // Reset to default from options
        opacity: 1.0, // Reset opacity
      });
    }
  }

  // Clear search status
  if (searchStatus) searchStatus.textContent = "";

  // Redraw network
  network.redraw();
}

function clearSearch() {
  // Clear search input
  if (searchInput) {
    searchInput.value = "";
  }

  // Reset search variables
  currentSearchQuery = "";
  currentSearchResults = [];
  currentSearchResultIndex = -1;

  // Reset node appearances
  resetSearchHighlights();

  // Update UI
  updateSearchResultUI();

  // Clear any node selection
  if (network) {
    network.unselectAll();
  }
}

// --- Setup global keyboard shortcuts ---
function setupKeyboardShortcuts() {
  document.addEventListener("keydown", function (e) {
    // Check if we should ignore the event (input fields, etc.)
    if (shouldIgnoreKeyboardEvent(e)) return;

    // Ctrl+F for search
    if ((e.ctrlKey || e.metaKey) && e.key === "f") {
      e.preventDefault(); // Prevent browser's find
      toggleSearchPanel();
    }

    // Escape to close search panel
    if (e.key === "Escape" && isSearchPanelOpen) {
      closeSearchPanel();
    }

    // Navigation in search results
    if (isSearchPanelOpen && currentSearchResults.length > 0) {
      if (e.key === "Enter") {
        e.preventDefault();

        if (e.shiftKey) {
          navigateSearchResult(-1); // Previous
        } else {
          navigateSearchResult(1); // Next
        }
      }
    }
  });
}

function shouldIgnoreKeyboardEvent(e) {
  // Ignore keyboard events when typing in input elements
  const target = e.target;
  const tagName = target.tagName.toLowerCase();

  if (tagName === "input" || tagName === "textarea" || tagName === "select") {
    return true;
  }

  // Ignore events with contentEditable elements
  if (target.isContentEditable) {
    return true;
  }

  return false;
}

// --- Helper to get value from UI element ---
function getElementValue(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return undefined;
  if (el.type === "checkbox") return el.checked;
  if (el.type === "range" || el.type === "number") {
    // Special handling for avoidOverlap: always parse as float
    if (elementId === "physics.hierarchicalRepulsion.avoidOverlap") {
      return parseFloat(el.value);
    }
    return el.valueAsNumber;
  }
  return el.value;
}

// --- Nested Property Helper ---
function setNestedProperty(obj, path, value) {
  const keys = path.split(".");
  let current = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    current = current[keys[i]] = current[keys[i]] || {};
  }
  current[keys[keys.length - 1]] = value;
}

// --- Helper to update value display for sliders ---
function updateValueDisplay(rangeInputId, value) {
  const displayElement = document.getElementById(rangeInputId + "_value");
  if (displayElement) {
    displayElement.textContent = Number.isFinite(parseFloat(value))
      ? parseFloat(value).toFixed(2)
      : value;
  }
}

// --- Apply Settings Button Logic ---
function applyUISettings() {
  if (!network || !network.setOptions) {
    console.error("Network not ready.");
    return;
  }
  console.log("Applying UI settings...");
  showLoadingOverlay();

  const currentOptions = {};
  const controlElements = document.querySelectorAll(".control-panel [id]");
  controlElements.forEach((el) => {
    if (
      el.id &&
      el.id !== "loadingOverlay" &&
      el.id !== "controlPanel" &&
      (el.tagName === "INPUT" || el.tagName === "SELECT")
    ) {
      const optionPath = el.id;
      const value = getElementValue(el.id);
      if (value !== undefined) {
        setNestedProperty(currentOptions, optionPath, value);
      }
    }
  });

  console.log("Applying options:", JSON.stringify(currentOptions, null, 2));
  try {
    setTimeout(() => {
      // Short delay for overlay
      network.setOptions(currentOptions);
      if (
        currentOptions.physics?.enabled ||
        currentOptions.layout?.hierarchical?.enabled
      ) {
        console.log("Stabilizing network after applying changes...");
        network.stabilize(); // Stabilization event will hide overlay
      } else {
        console.log("Redrawing network (no stabilization needed)...");
        network.redraw();
        hideLoadingOverlay(); // Hide manually if not stabilizing
      }
    }, 50);
  } catch (error) {
    console.error(
      "Error applying settings:",
      error,
      "Attempted options:",
      currentOptions
    );
    hideLoadingOverlay();
  }
}

// --- Reset Function ---
function resetToInitialOptions() {
  if (!network || !network.setOptions) {
    console.error("Network not ready.");
    return;
  }
  console.log("Resetting to initial options...");
  showLoadingOverlay();

  // Reset UI elements FIRST
  const controlElements = document.querySelectorAll(".control-panel [id]");
  controlElements.forEach((el) => {
    if (el.id && (el.tagName === "INPUT" || el.tagName === "SELECT")) {
      const optionPath = el.id;
      let initialValue = initialNetworkOptions;
      try {
        optionPath.split(".").forEach((k) => {
          initialValue = initialValue[k];
        });
      } catch (e) {
        initialValue = undefined;
      }
      if (initialValue !== undefined) {
        if (el.type === "checkbox") {
          el.checked = initialValue;
        } else if (el.type === "range") {
          el.value = initialValue;
          updateValueDisplay(el.id, initialValue);
        } else {
          el.value = initialValue;
        }
      }
    }
  });

  // Apply initial options to the network
  setTimeout(() => {
    try {
      network.setOptions(initialNetworkOptions);
      console.log("Stabilizing network after reset...");
      network.stabilize(); // Stabilization event will hide overlay
    } catch (error) {
      console.error("Error resetting options:", error);
      hideLoadingOverlay();
    }
  }, 50);
}

// --- SVG Generation (Mostly unchanged, added basic error checking) ---
async function generateNetworkSVG(cropArea = null) {
  console.log(
    "Generating SVG representation...",
    cropArea ? "for selection" : "for full network"
  );
  if (!network || !network.body || !network.getPositions) {
    console.error("Network object or required components not available.");
    throw new Error("Network not ready for SVG export.");
  }

  const nodeIds = network.body.nodeIndices;
  const edgeIds = network.body.edgeIndices;
  const positions = network.getPositions();

  // Determine bounding box
  let minX = Infinity,
    minY = Infinity,
    maxX = -Infinity,
    maxY = -Infinity;
  let hasContent = false; // Flag to check if there's anything to draw

  nodeIds.forEach((nodeId) => {
    const node = network.body.nodes[nodeId];
    if (!node || node.options.hidden || !positions[nodeId]) return;
    const pos = positions[nodeId];
    const size = (node.options.size || 10) * 2; // diameter
    const borderWidth = (node.options.borderWidth || 1) * 2; // consider border width on both sides
    const extent = size / 2 + borderWidth / 2;

    // If cropping, only consider nodes within the crop area
    if (
      cropArea &&
      (pos.x < cropArea.x ||
        pos.x > cropArea.x + cropArea.width ||
        pos.y < cropArea.y ||
        pos.y > cropArea.y + cropArea.height)
    ) {
      // Basic check, could be refined to check intersection instead of center point only
      return;
    }

    minX = Math.min(minX, pos.x - extent);
    maxX = Math.max(maxX, pos.x + extent);
    minY = Math.min(minY, pos.y - extent);
    maxY = Math.max(maxY, pos.y + extent);
    hasContent = true;
  });

  // If cropping, adjust bounds to the selection area
  if (cropArea) {
    minX = cropArea.x;
    minY = cropArea.y;
    maxX = cropArea.x + cropArea.width;
    maxY = cropArea.y + cropArea.height;
  } else if (!hasContent) {
    // Handle empty network case for full export
    minX = -100;
    minY = -100;
    maxX = 100;
    maxY = 100; // Default non-zero size
  } else {
    // Add padding for full export only if there's content
    const padding = 50;
    minX -= padding;
    minY -= padding;
    maxX += padding;
    maxY += padding;
  }

  const width = maxX - minX;
  const height = maxY - minY;

  if (width <= 0 || height <= 0) {
    console.warn(
      "Calculated network bounds are zero or negative. Using default size."
    );
    minX = -200;
    minY = -200;
    maxX = 200;
    maxY = 200;
    width = 400;
    height = 400;
  }

  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("xmlns", svgNS);
  svg.setAttribute("viewBox", `${minX} ${minY} ${width} ${height}`);
  svg.setAttribute("width", width); // Set physical size for better rendering
  svg.setAttribute("height", height);
  svg.style.backgroundColor = "#ffffff";
  svg.setAttribute("shape-rendering", "geometricPrecision");

  // Define marker for arrowheads (unchanged)
  const defs = document.createElementNS(svgNS, "defs");
  const marker = document.createElementNS(svgNS, "marker");
  marker.setAttribute("id", "arrowhead");
  marker.setAttribute("viewBox", "-5 -5 10 10");
  marker.setAttribute("refX", "6"); // Adjusted slightly
  marker.setAttribute("refY", "0");
  marker.setAttribute("markerWidth", "6");
  marker.setAttribute("markerHeight", "6");
  marker.setAttribute("orient", "auto-start-reverse");
  const arrowPath = document.createElementNS(svgNS, "path");
  arrowPath.setAttribute("d", "M -5 -5 L 5 0 L -5 5 z");
  marker.appendChild(arrowPath);
  defs.appendChild(marker);
  svg.appendChild(defs);

  // Draw Edges
  const edgesGroup = document.createElementNS(svgNS, "g");
  edgesGroup.setAttribute("id", "edges");
  edgeIds.forEach((edgeId) => {
    const edge = network.body.edges[edgeId];
    if (!edge || edge.options.hidden || !edge.fromId || !edge.toId) return; // Skip invalid edges
    const fromNode = network.body.nodes[edge.fromId];
    const toNode = network.body.nodes[edge.toId];
    if (
      !fromNode ||
      !toNode ||
      !positions[edge.fromId] ||
      !positions[edge.toId]
    )
      return;

    const fromPos = positions[edge.fromId];
    const toPos = positions[edge.toId];

    // Basic check if edge is within cropArea (can be improved for curve intersections)
    if (cropArea) {
      const roughlyInside = (p) =>
        p.x >= cropArea.x &&
        p.x <= cropArea.x + cropArea.width &&
        p.y >= cropArea.y &&
        p.y <= cropArea.y + cropArea.height;
      if (!roughlyInside(fromPos) && !roughlyInside(toPos)) {
        // More sophisticated check needed for edges crossing the boundary
        // For simplicity, only drawing edges whose endpoints are roughly inside
        // A better approach involves clipping paths, which is complex.
        // return; // Skipped for simplicity, draw all for now and let viewBox clip
      }
    }

    const edgeOptions = edge.options;
    const path = document.createElementNS(svgNS, "path");
    let pathD = `M ${fromPos.x} ${fromPos.y}`;

    if (
      edgeOptions.smooth &&
      edgeOptions.smooth.enabled &&
      edgeOptions.smooth.type === "cubicBezier"
    ) {
      const dx = toPos.x - fromPos.x;
      const roundnessFactor =
        edgeOptions.smooth.roundness != null
          ? edgeOptions.smooth.roundness
          : 0.5;
      const controlPointOffset = dx * roundnessFactor * 0.5;
      const cp1x = fromPos.x + controlPointOffset;
      const cp1y = fromPos.y;
      const cp2x = toPos.x - controlPointOffset;
      const cp2y = toPos.y;
      pathD += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${toPos.x} ${toPos.y}`;
    } else {
      pathD += ` L ${toPos.x} ${toPos.y}`;
    }

    path.setAttribute("d", pathD);
    const color = (edgeOptions.color && edgeOptions.color.color) || "#cccccc";
    const opacity =
      edgeOptions.color && edgeOptions.color.opacity != null
        ? edgeOptions.color.opacity
        : 0.6;
    const width = edgeOptions.width || 1.5;

    path.setAttribute("stroke", color);
    path.setAttribute("stroke-width", width);
    path.setAttribute("stroke-opacity", opacity);
    path.setAttribute("fill", "none");

    if (
      edgeOptions.arrows &&
      edgeOptions.arrows.to &&
      edgeOptions.arrows.to.enabled
    ) {
      path.setAttribute("marker-end", "url(#arrowhead)");
      const markerPath = marker.querySelector("path");
      if (markerPath) {
        markerPath.setAttribute("fill", color);
      }
    }

    edgesGroup.appendChild(path);
  });
  svg.appendChild(edgesGroup);

  // Draw Nodes
  const nodesGroup = document.createElementNS(svgNS, "g");
  nodesGroup.setAttribute("id", "nodes");
  nodeIds.forEach((nodeId) => {
    const node = network.body.nodes[nodeId];
    if (!node || node.options.hidden || !positions[nodeId]) return;

    const pos = positions[nodeId];

    // Skip node if outside crop area
    if (
      cropArea &&
      (pos.x < cropArea.x ||
        pos.x > cropArea.x + cropArea.width ||
        pos.y < cropArea.y ||
        pos.y > cropArea.y + cropArea.height)
    ) {
      // Again, simple check. Could improve by checking if any part of the node overlaps.
      // return; // Skipped for simplicity, draw all for now and let viewBox clip
    }

    const nodeOptions = node.options;
    const size = nodeOptions.size || 10;
    const radius = size; // Assuming 'dot' shape
    const borderWidth = nodeOptions.borderWidth || 1;
    const color =
      (nodeOptions.color && nodeOptions.color.background) || "#97C2FC";
    const borderColor =
      nodeOptions.borderColor ||
      (nodeOptions.color && nodeOptions.color.border) ||
      color;

    const shape = document.createElementNS(svgNS, "circle");
    shape.setAttribute("cx", pos.x);
    shape.setAttribute("cy", pos.y);
    shape.setAttribute("r", radius);
    shape.setAttribute("fill", color);
    shape.setAttribute("stroke", borderColor);
    shape.setAttribute("stroke-width", borderWidth);
    nodesGroup.appendChild(shape);

    if (nodeOptions.label && nodeOptions.font) {
      const text = document.createElementNS(svgNS, "text");
      text.setAttribute("x", pos.x);
      text.setAttribute("y", pos.y);
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("dominant-baseline", "central");
      text.setAttribute("font-family", nodeOptions.font.face || "arial");
      text.setAttribute("font-size", nodeOptions.font.size || 12);
      text.setAttribute("fill", nodeOptions.font.color || "#343434");
      text.setAttribute("text-rendering", "geometricPrecision");

      const labelLines = String(nodeOptions.label).split("\\n");
      if (labelLines.length > 1) {
        const fontSize = nodeOptions.font.size || 12;
        const approxLineHeightFactor = 1.2; // Adjust as needed
        const totalLabelHeight =
          fontSize * labelLines.length * approxLineHeightFactor;
        const startY = pos.y - totalLabelHeight / 2 + fontSize * 0.6; // Rough vertical centering

        labelLines.forEach((line, index) => {
          const tspan = document.createElementNS(svgNS, "tspan");
          tspan.setAttribute("x", pos.x);
          tspan.setAttribute(
            "dy",
            index === 0 ? startY - pos.y : fontSize * approxLineHeightFactor
          );
          tspan.textContent = line;
          text.appendChild(tspan);
        });
      } else {
        text.textContent = nodeOptions.label;
      }

      nodesGroup.appendChild(text);
    }
  });
  svg.appendChild(nodesGroup);

  console.log("SVG generation complete.");
  return new XMLSerializer().serializeToString(svg);
}

// --- PNG Export Function (handles selection or full) ---
async function exportToPNG(selection = null, qualityScaleFactor = 1.5) {
  const exportType = selection
    ? `selection (Scale: ${qualityScaleFactor})`
    : `full network (Scale: ${qualityScaleFactor})`;
  console.log(`High-quality PNG export started for ${exportType}...`);
  if (!network || !network.body) {
    console.error("Network not ready for PNG export.");
    alert("Error: Network not ready");
    return;
  }

  showLoadingOverlay(
    `Generating PNG for ${selection ? "selection" : "full network"}...`
  );

  try {
    // 1. Generate SVG (pass null for cropArea if it's a full export)
    const svgCropArea = selection
      ? {
          x: selection.x,
          y: selection.y,
          width: selection.width,
          height: selection.height,
        }
      : null;
    const svgString = await generateNetworkSVG(svgCropArea);

    // 2. Get dimensions from SVG viewBox
    const svgMatch = svgString.match(/viewBox="([^"]+)"/);
    const viewBox = svgMatch
      ? svgMatch[1].split(" ").map(Number)
      : [0, 0, 600, 600];
    const svgWidth = viewBox[2];
    const svgHeight = viewBox[3];

    if (svgWidth <= 0 || svgHeight <= 0) {
      throw new Error("Invalid SVG dimensions calculated for PNG export.");
    }

    // 3. Create high-resolution canvas
    const dpr = window.devicePixelRatio || 1;
    const scale = dpr * qualityScaleFactor;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(svgWidth * scale);
    canvas.height = Math.round(svgHeight * scale);
    const ctx = canvas.getContext("2d");

    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";

    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // 4. Render SVG onto the canvas
    const img = new Image();
    const blob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    await new Promise((resolve, reject) => {
      img.onload = () => {
        console.log("SVG loaded, drawing to PNG canvas...");
        try {
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          URL.revokeObjectURL(url);
          console.log("PNG Canvas drawing complete.");
          resolve();
        } catch (drawError) {
          URL.revokeObjectURL(url);
          console.error("Error drawing SVG to canvas:", drawError);
          reject(new Error("Failed to draw SVG onto canvas."));
        }
      };
      img.onerror = (err) => {
        URL.revokeObjectURL(url);
        console.error("Error loading SVG into image for PNG export:", err);
        reject(new Error("Failed to load SVG for PNG rendering."));
      };
      img.src = url;
    });

    // 5. Save the canvas as PNG
    const link = document.createElement("a");
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const fileNameSuffix = selection
      ? "_selection_" + timestamp
      : "_full_" + timestamp;
    link.download = `${baseFileName}${fileNameSuffix}.png`;
    link.href = canvas.toDataURL("image/png"); // Ensure this step happens after drawImage completes
    link.click();

    console.log(`PNG export successful for ${exportType}.`);
    hideLoadingOverlay();
  } catch (error) {
    console.error(`PNG export failed for ${exportType}:`, error);
    alert(`Error saving PNG (${exportType}): ` + error.message);
    hideLoadingOverlay();
  }
}

// --- SVG Export Function (handles selection or full) ---
async function exportToSVG(selection = null) {
  const exportType = selection ? "selection" : "full network";
  console.log(`SVG export started for ${exportType}...`);
  if (!network || !network.body) {
    console.error("Network not ready for SVG export.");
    alert("Error: Network not ready");
    return;
  }
  showLoadingOverlay(
    `Generating SVG for ${selection ? "selection" : "full network"}...`
  );

  try {
    const svgCropArea = selection
      ? {
          x: selection.x,
          y: selection.y,
          width: selection.width,
          height: selection.height,
        }
      : null;
    const svgString = await generateNetworkSVG(svgCropArea);

    const blob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const fileNameSuffix = selection
      ? "_selection_" + timestamp
      : "_full_" + timestamp;
    link.download = `${baseFileName}${fileNameSuffix}.svg`;
    link.click();

    setTimeout(() => URL.revokeObjectURL(link.href), 100); // Cleanup

    console.log(`SVG export successful for ${exportType}.`);
    hideLoadingOverlay();
  } catch (error) {
    console.error(`SVG export failed for ${exportType}:`, error);
    alert(`Error saving SVG (${exportType}): ` + error.message);
    hideLoadingOverlay();
  }
}

// --- Functions to trigger FULL network exports ---
function saveFullNetworkPNG(qualityScaleFactor = 1.5) {
  exportToPNG(null, qualityScaleFactor);
}
function saveFullNetworkSVG() {
  exportToSVG(null);
}

// --- Selection Mode Functions ---
function startSelectionMode() {
  if (!network) {
    alert("Network not ready.");
    return;
  }
  console.log("Starting selection mode...");
  selectionOverlay = document.getElementById("selectionOverlay");
  selectionRectangle = document.getElementById("selectionRectangle");
  exportChoiceModal = document.getElementById("exportChoiceModal");

  if (!selectionOverlay || !selectionRectangle || !exportChoiceModal) {
    console.error("Selection UI elements not found.");
    return;
  }

  selectionOverlay.style.display = "block";
  exportChoiceModal.style.display = "none"; // Hide export choice initially
  selectionRectangle.style.display = "none";
  isSelecting = false;
  selectionCanvasCoords = null; // Reset previous selection

  // Add event listeners for selection
  selectionOverlay.addEventListener("mousedown", handleMouseDown);
  selectionOverlay.addEventListener("mousemove", handleMouseMove);
  selectionOverlay.addEventListener("mouseup", handleMouseUp);
  selectionOverlay.addEventListener("mouseleave", handleMouseLeave); // Cancel if mouse leaves
}

function cancelSelectionMode() {
  console.log("Cancelling selection mode...");
  if (selectionOverlay) {
    selectionOverlay.style.display = "none";
    selectionOverlay.removeEventListener("mousedown", handleMouseDown);
    selectionOverlay.removeEventListener("mousemove", handleMouseMove);
    selectionOverlay.removeEventListener("mouseup", handleMouseUp);
    selectionOverlay.removeEventListener("mouseleave", handleMouseLeave);
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
  if (event.button !== 0) return; // Only left click
  isSelecting = true;
  selectionStartX = event.clientX;
  selectionStartY = event.clientY;
  const rect = selectionOverlay.getBoundingClientRect(); // Get overlay position
  selectionRect.x = event.clientX - rect.left;
  selectionRect.y = event.clientY - rect.top;
  selectionRect.width = 0;
  selectionRect.height = 0;
  selectionRectangle.style.left = selectionRect.x + "px";
  selectionRectangle.style.top = selectionRect.y + "px";
  selectionRectangle.style.width = "0px";
  selectionRectangle.style.height = "0px";
  selectionRectangle.style.display = "block";
  event.preventDefault(); // Prevent text selection, etc.
}

function handleMouseMove(event) {
  if (!isSelecting) return;
  const rect = selectionOverlay.getBoundingClientRect();
  const currentX = event.clientX - rect.left;
  const currentY = event.clientY - rect.top;

  selectionRect.width = currentX - selectionRect.x;
  selectionRect.height = currentY - selectionRect.y;

  // Adjust for dragging in different directions
  let displayX = selectionRect.x;
  let displayY = selectionRect.y;
  let displayWidth = selectionRect.width;
  let displayHeight = selectionRect.height;

  if (selectionRect.width < 0) {
    displayX = currentX;
    displayWidth = -selectionRect.width;
  }
  if (selectionRect.height < 0) {
    displayY = currentY;
    displayHeight = -selectionRect.height;
  }

  selectionRectangle.style.left = displayX + "px";
  selectionRectangle.style.top = displayY + "px";
  selectionRectangle.style.width = displayWidth + "px";
  selectionRectangle.style.height = displayHeight + "px";
}

function handleMouseUp(event) {
  if (!isSelecting) return;
  isSelecting = false;
  selectionRectangle.style.display = "none"; // Hide rectangle after selection
  selectionOverlay.style.display = "none"; // Hide overlay

  // Remove overlay listeners immediately
  selectionOverlay.removeEventListener("mousedown", handleMouseDown);
  selectionOverlay.removeEventListener("mousemove", handleMouseMove);
  selectionOverlay.removeEventListener("mouseup", handleMouseUp);
  selectionOverlay.removeEventListener("mouseleave", handleMouseLeave);

  // Final coordinates relative to the overlay
  const rect = selectionOverlay.getBoundingClientRect();
  const finalX = selectionRect.x + rect.left; // Use original start, not event.clientX
  const finalY = selectionRect.y + rect.top; // Use original start, not event.clientY
  const finalWidth = selectionRect.width;
  const finalHeight = selectionRect.height;

  // Ensure positive width/height
  let startDOMX = finalX;
  let startDOMY = finalY;
  let endDOMX = finalX + finalWidth;
  let endDOMY = finalY + finalHeight;

  if (finalWidth < 0) {
    [startDOMX, endDOMX] = [endDOMX, startDOMX];
  }
  if (finalHeight < 0) {
    [startDOMY, endDOMY] = [endDOMY, startDOMY];
  }

  const absWidth = Math.abs(finalWidth);
  const absHeight = Math.abs(finalHeight);

  // Ignore tiny selections
  if (absWidth < 5 || absHeight < 5) {
    console.log("Selection too small, cancelled.");
    cancelSelectionMode();
    return;
  }

  // Convert DOM coordinates to Canvas coordinates
  const startCanvas = network.DOMtoCanvas({ x: startDOMX, y: startDOMY });
  const endCanvas = network.DOMtoCanvas({ x: endDOMX, y: endDOMY });

  selectionCanvasCoords = {
    x: Math.min(startCanvas.x, endCanvas.x),
    y: Math.min(startCanvas.y, endCanvas.y),
    width: Math.abs(endCanvas.x - startCanvas.x),
    height: Math.abs(endCanvas.y - startCanvas.y),
  };

  console.log("Selection finished. Canvas Coords:", selectionCanvasCoords);

  // Show export choice modal
  if (exportChoiceModal) {
    exportChoiceModal.style.display = "block";
  } else {
    console.error("Export choice modal not found!");
    cancelSelectionMode(); // Fallback: just cancel if modal is missing
  }
}

function handleMouseLeave(event) {
  // If selecting and mouse leaves the area, cancel the selection
  if (isSelecting) {
    console.log("Mouse left overlay during selection, cancelling.");
    cancelSelectionMode();
  }
}

// --- Trigger Export based on Choice ---
function exportSelection(format) {
  exportChoiceModal.style.display = "none"; // Hide modal

  if (!selectionCanvasCoords) {
    console.error("No selection coordinates available for export.");
    alert("Error: No selection was made.");
    cancelSelectionMode();
    return;
  }

  if (format === "png") {
    exportToPNG(selectionCanvasCoords, 1.5); // Export selection as PNG with 1.5x upscale
  } else if (format === "svg") {
    exportToSVG(selectionCanvasCoords); // Export selection as SVG
  } else {
    console.error("Unknown export format:", format);
  }

  // Reset selection state after export attempt
  selectionCanvasCoords = null;
}

// --- Event Listener Setup (Mostly unchanged) ---
function setupEventListeners() {
  console.log("Setting up event listeners for controls...");
  document
    .querySelectorAll('.control-panel input[type="range"]')
    .forEach((input) => {
      input.oninput = () => updateValueDisplay(input.id, input.value);
    });

  // Setup search-related event listeners
  setupKeyboardShortcuts();

  // Setup event listeners for search options
  document
    .querySelectorAll('.search-option input[type="checkbox"]')
    .forEach((checkbox) => {
      checkbox.addEventListener("change", function () {
        // Re-highlight with new settings if we have search results
        if (currentSearchResults.length > 0) {
          highlightSearchResults();
        }
      });
    });
}

// --- Network Ready & Initialization (Check overlay setup) ---
let networkReady = false;
let listenersAttached = false;

function onNetworkReady() {
  if (networkReady && !listenersAttached) {
    setupEventListeners();
    hideLoadingBar(); // Ensure loading bar is hidden
    listenersAttached = true;
    console.log("Network ready, listeners attached.");

    network.on("stabilizationIterationsDone", () => {
      console.log("Stabilization finished.");
      setTimeout(hideLoadingOverlay, 250);
      hideLoadingBar();
    });
    network.on("stabilizationProgress", (params) => {
      /* Optional logging */
    });
    // Hide overlay initially, stabilization might be fast or off
    setTimeout(hideLoadingOverlay, 100); // Hide a bit faster after ready

    // Initialize search functionality
    initializeSearchEngine();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM Content Loaded.");
  // Get references to new UI elements
  selectionOverlay = document.getElementById("selectionOverlay");
  selectionRectangle = document.getElementById("selectionRectangle");
  exportChoiceModal = document.getElementById("exportChoiceModal");
  searchPanel = document.getElementById("searchPanel");
  searchInput = document.getElementById("searchInput");
  searchResultCount = document.getElementById("searchResultCount");
  searchStatus = document.getElementById("searchStatus");

  const networkContainer = document.getElementById("mynetwork");
  if (networkContainer) networkContainer.style.right = "0px";

  if (!document.getElementById("loadingOverlay")) {
    const overlay = document.createElement("div");
    overlay.id = "loadingOverlay";
    overlay.innerHTML =
      '<div class="spinner"></div><div>Loading Network...</div>'; // Use spinner class
    overlay.style.cssText =
      "/* ... loading overlay CSS from style block ... */ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(200, 200, 200, 0.6); z-index: 1002; display: flex; flex-direction: column; justify-content: center; align-items: center; font-size: 1.5em; color: #333; text-align: center;";
    document.body.appendChild(overlay);
  }
  document.getElementById("loadingOverlay").style.display = "flex"; // Show initially

  hideLoadingBar(); // Attempt early hide
  setupLoadingBarObserver(); // Set up observer early

  const checkNetworkInterval = setInterval(() => {
    if (window.network && typeof window.network.on === "function") {
      clearInterval(checkNetworkInterval);
      networkReady = true;
      console.log("Network object found.");
      onNetworkReady();
    }
  }, 100);

  setTimeout(() => {
    clearInterval(checkNetworkInterval);
    if (!networkReady) {
      console.warn("Network object failed to initialize within timeout.");
      hideLoadingOverlay();
    }
  }, 15000);
});

window.addEventListener("load", () => {
  console.log("Window Load event fired.");
  hideLoadingBar();
  if (
    !networkReady &&
    window.network &&
    typeof window.network.on === "function"
  ) {
    networkReady = true;
    console.log("Network object found on window.load.");
    onNetworkReady();
  }
  setTimeout(hideLoadingOverlay, 500); // Ensure overlay is hidden after load

  // Add Fuse.js library
  if (typeof Fuse === "undefined") {
    try {
      const fusejsScript = document.createElement("script");
      fusejsScript.src = "https://cdn.jsdelivr.net/npm/fuse.js@7.1.0";
      fusejsScript.onload = () =>
        console.log("Fuse.js library loaded successfully");
      fusejsScript.onerror = (err) =>
        console.error("Failed to load Fuse.js:", err);
      document.head.appendChild(fusejsScript);
    } catch (e) {
      console.error("Error attempting to add Fuse.js:", e);
    }
  }
});

// --- Window Resize Handler (Unchanged) ---
window.addEventListener("resize", () => {
  clearTimeout(window.resizeTimeout);
  window.resizeTimeout = setTimeout(() => {
    console.log("Window resized.");
    const networkContainer = document.getElementById("mynetwork");
    if (networkContainer) {
      networkContainer.style.right = isPanelExpanded
        ? panelWidth + "px"
        : "0px";
    }
    if (network?.redraw) {
      network.redraw();
    }
    if (network?.fit) {
      network.fit({ animation: false });
    }
  }, 250);
});

// --- Custom Persistent Tooltip Logic ---
let persistentTooltip = null;
let persistentTooltipNodeId = null;
function showPersistentTooltip(nodeId, html, event) {
  hidePersistentTooltip();
  persistentTooltip = document.createElement("div");
  persistentTooltip.className = "vis-tooltip";
  persistentTooltip.innerHTML =
    `<button style='float:right; margin-left:10px;' onclick='hidePersistentTooltip()'>&#10005;</button>` +
    html;
  persistentTooltip.style.position = "fixed";
  persistentTooltip.style.zIndex = 2000;
  persistentTooltip.style.pointerEvents = "auto";
  persistentTooltip.style.maxWidth = "450px";
  persistentTooltip.style.maxHeight = "60vh";
  persistentTooltip.style.overflowY = "auto";
  // Position near mouse, but keep in viewport
  let x = event.clientX + 16;
  let y = event.clientY + 16;
  if (x + 450 > window.innerWidth) x = window.innerWidth - 470;
  if (y + 300 > window.innerHeight) y = window.innerHeight - 320;
  persistentTooltip.style.left = x + "px";
  persistentTooltip.style.top = y + "px";
  document.body.appendChild(persistentTooltip);
  persistentTooltipNodeId = nodeId;
  // Prevent click from propagating to network
  persistentTooltip.addEventListener("mousedown", (e) => e.stopPropagation());
  persistentTooltip.addEventListener("mouseup", (e) => e.stopPropagation());
}
function hidePersistentTooltip() {
  if (persistentTooltip) {
    persistentTooltip.remove();
    persistentTooltip = null;
    persistentTooltipNodeId = null;
  }
}
// Hide tooltip if clicking outside
document.addEventListener("mousedown", function (e) {
  if (persistentTooltip && !persistentTooltip.contains(e.target)) {
    hidePersistentTooltip();
  }
});
// --- Patch vis.js events after network is ready ---
function patchVisTooltip() {
  if (!window.network) return;
  window.network.on("click", function (params) {
    hidePersistentTooltip();
    if (params.nodes && params.nodes.length > 0) {
      const nodeId = params.nodes[0];
      const node = window.network.body.data.nodes.get(nodeId);
      if (node && node.title) {
        // Use last pointer event for position
        let evt = window.network.lastPointerEvent || window.event;
        if (!evt && params.event && params.event.srcEvent)
          evt = params.event.srcEvent;
        if (!evt)
          evt = {
            clientX: window.innerWidth / 2,
            clientY: window.innerHeight / 2,
          };
        showPersistentTooltip(nodeId, node.title, evt);
      }
    }
  });
  // Save pointer event for click positioning
  window.network.on("hoverNode", function (params) {
    if (params.event && params.event.srcEvent) {
      window.network.lastPointerEvent = params.event.srcEvent;
    }
  });
}
document.addEventListener("DOMContentLoaded", function () {
  setTimeout(patchVisTooltip, 500);
});
